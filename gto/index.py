import logging
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import IO, Any, Dict, FrozenSet, Generator, List, Optional, Union

import git
from git import Repo
from pydantic import BaseModel, ValidationError, parse_obj_as, validator
from ruamel.yaml import YAMLError

from gto.base import BaseManager, BaseRegistryState
from gto.base import Commit as EnrichmentEvent
from gto.commit_message_generator import (
    generate_annotate_commit_message,
    generate_remove_commit_message,
)
from gto.config import (
    CONFIG_FILE_NAME,
    RegistryConfig,
    assert_name_is_valid,
    read_registry_config,
    yaml,
)
from gto.constants import Action
from gto.exceptions import (
    ArtifactExists,
    ArtifactNotFound,
    NoFile,
    PathIsUsed,
    WrongArgs,
    WrongArtifactsYaml,
)
from gto.ext import EnrichmentInfo, EnrichmentReader
from gto.git_utils import RemoteRepoMixin, read_repo
from gto.ui import echo
from gto.utils import resolve_ref

logger = logging.getLogger("gto")


class Artifact(BaseModel):
    type: Optional[str] = None
    path: Optional[str] = None
    virtual: bool = True
    labels: List[str] = []  # TODO: allow key:value labels
    description: str = ""
    custom: Any = None


State = Dict[str, Artifact]


def not_frozen(func):
    @wraps(func)
    def inner(self: "Index", *args, **kwargs):
        if self.frozen:
            raise ValueError(f"Cannot {func.__name__}: {self.__class__} is frozen")
        return func(self, *args, **kwargs)

    return inner


def find_repeated_path(
    path: Union[str, Path], paths: List[Union[str, Path]]
) -> Optional[Path]:
    """Return the path from "paths" that conflicts with "path":
    is equal to it or is a subpath (in both directions).
    """
    path = Path(path).resolve()
    for p in paths:
        if p:
            p = Path(p).resolve()
            if p == path or p in path.parents or path in p.parents:
                return p
    return None


def check_if_path_exists(path: str, repo: git.Repo = None, ref: str = None):
    """Check if path was committed to repo
    or it just exists in case the repo is not provided.
    """
    if repo is None:
        return Path(path).exists()
    try:
        _ = (repo.commit(ref).tree / path).data_stream
        return True
    except KeyError:
        return False


def traverse_commit(commit: git.Commit) -> Generator[git.Commit, None, None]:
    yield commit
    for parent in commit.parents:
        yield from traverse_commit(parent)


class Index(BaseModel):
    state: State = {}  # TODO should not be populated until load() is called
    frozen: bool = False

    @validator("state")
    def state_is_valid(cls, v):  # pylint: disable=no-self-argument, no-self-use
        for name, artifact in v.items():
            assert_name_is_valid(name)
            if artifact.type:
                assert_name_is_valid(artifact.type)
            for label in artifact.labels:
                assert_name_is_valid(label)
        return v

    def __contains__(self, item):
        return item in self.state

    @classmethod
    def read(cls, path_or_file: Union[str, IO], frozen: bool = False):
        index = cls(frozen=frozen)
        index.state = index.read_state(path_or_file)
        return index

    @staticmethod
    def read_state(path_or_file: Union[str, IO]):
        def read_yaml(stream: IO):
            try:
                return yaml.load(stream)
            except YAMLError as e:
                raise WrongArtifactsYaml() from e

        # read contents of the yaml
        if isinstance(path_or_file, str):
            try:
                with open(path_or_file, "r", encoding="utf8") as file:
                    contents = read_yaml(file)
            except FileNotFoundError as e:
                raise NoFile("artifacts.yaml") from e
        else:
            contents = read_yaml(path_or_file)
        # check yaml contents is a valid State
        try:
            state = parse_obj_as(State, contents)
        except ValidationError as e:
            raise WrongArtifactsYaml() from e
        # validate that specific names conform to the naming convention
        for key in state:
            assert_name_is_valid(key)
        return state

    def write_state(self, path_or_file: Union[str, IO]):
        if isinstance(path_or_file, str):
            with open(path_or_file, "w", encoding="utf8") as file:
                state = self.dict(exclude_defaults=True).get("state", {})
                yaml.dump(state, file)

    @not_frozen
    def add(
        self,
        name,
        type,
        path,
        must_exist,
        allow_same_path,
        labels,
        description,
        custom,
        update,
    ) -> Artifact:
        if name in self and not update:
            raise ArtifactExists(name)
        if (
            path
            and not allow_same_path
            and find_repeated_path(
                path, [a.path for n, a in self.state.items() if n != name]
            )
            is not None
        ):
            raise PathIsUsed(type=type, name=name, path=path)
        if update and name in self.state:
            self.state[name].type = type or self.state[name].type
            self.state[name].path = path or self.state[name].path
            if must_exist:
                self.state[name].virtual = False
            elif path:
                self.state[name].virtual = True
            self.state[name].labels = sorted(set(self.state[name].labels).union(labels))
            self.state[name].description = description or self.state[name].description
            self.state[name].custom = custom or self.state[name].custom
        else:
            self.state[name] = Artifact(
                type=type,
                path=path,
                virtual=not must_exist,
                labels=labels,
                description=description,
                custom=custom,
            )
        self.state_is_valid(self.state)
        return self.state[name]

    @not_frozen
    def remove(self, name):
        if name not in self:
            raise ArtifactNotFound(name)
        del self.state[name]


class BaseIndexManager(BaseModel, ABC):
    current: Optional[Index]
    config: RegistryConfig

    @abstractmethod
    def get_index(self) -> Index:
        raise NotImplementedError

    @abstractmethod
    def update(self):
        raise NotImplementedError

    @abstractmethod
    def get_history(self) -> Dict[str, Index]:
        raise NotImplementedError

    def add(
        self,
        name,
        type,
        path,
        must_exist,
        allow_same_path,
        labels,
        description,
        custom,
        update,
        stdout=False,
    ):
        for arg in [name] + list(labels or []):
            assert_name_is_valid(arg)
        if type:
            self.config.assert_type(type)
        if must_exist:
            if not path:
                raise WrongArgs("`path` is required when `must_exist` is set to True")
            if not check_if_path_exists(
                path, self.repo if hasattr(self, "repo") else None
            ):
                raise NoFile(path)
        index = self.get_index()
        index.add(
            name,
            type=type,
            path=path,
            must_exist=must_exist,
            allow_same_path=allow_same_path,
            labels=labels or [],
            description=description,
            custom=custom,
            update=update,
        )
        self.update()
        if stdout:
            echo("Updated `artifacts.yaml`")

    def remove(self, name, stdout=False):
        index = self.get_index()
        index.remove(name)
        self.update()
        if stdout:
            echo("Updated `artifacts.yaml`")


class FileIndexManager(BaseIndexManager):
    path: str = ""

    @classmethod
    def from_path(cls, path: str, config: RegistryConfig = None):
        if config is None:
            config = read_registry_config(os.path.join(path, CONFIG_FILE_NAME))
        return cls(path=path, config=config)

    def index_path(self):
        return str(Path(self.path) / self.config.INDEX)

    def get_index(self) -> Index:
        if os.path.exists(self.index_path()):
            self.current = Index.read(self.index_path())
        if not self.current:
            self.current = Index()
        return self.current

    def update(self):
        if self.current is not None:
            self.current.write_state(self.index_path())

    def get_history(self) -> Dict[str, Index]:
        raise NotImplementedError("Not a git repo: history is not available")

    def get_commit_index(self, **kwargs) -> Index:
        raise NotImplementedError("Not a git repo: using revision is not available")

    def artifact_centric_representation(self):
        raise NotImplementedError("Not a git repo")


ArtifactCommits = Dict[str, Artifact]
ArtifactsCommits = Dict[str, ArtifactCommits]


class RepoIndexManager(FileIndexManager, RemoteRepoMixin):
    repo: git.Repo

    def __init__(self, repo, config):
        super().__init__(repo=repo, config=config)

    @classmethod
    def from_local_repo(cls, repo: Union[str, git.Repo], config: RegistryConfig = None):
        repo = read_repo(repo, search_parent_directories=True)
        if config is None:
            config = read_registry_config(
                os.path.join(repo.working_dir, CONFIG_FILE_NAME)
            )
        return cls(repo=repo, config=config)

    def add(
        self,
        name,
        type,
        path,
        must_exist,
        allow_same_path,
        labels,
        description,
        custom,
        update,
        stdout=False,
        commit=False,
        commit_message=None,
        push=False,
    ):
        return self._call_commit_push(
            super().add,
            commit=commit,
            commit_message=commit_message
            or generate_annotate_commit_message(name=name, type=type, path=path),
            push=push,
            stdout=stdout,
            name=name,
            type=type,
            path=path,
            must_exist=must_exist,
            allow_same_path=allow_same_path,
            labels=labels,
            description=description,
            custom=custom,
            update=update,
        )

    def remove(
        self,
        name,
        stdout=False,
        commit=False,
        commit_message=None,
        push=False,
    ):
        return self._call_commit_push(
            super().remove,
            commit=commit,
            commit_message=commit_message or generate_remove_commit_message(name=name),
            push=push,
            stdout=stdout,
            name=name,
        )

    def index_path(self):
        # TODO: config should be loaded from repo too
        return os.path.join(os.path.dirname(self.repo.git_dir), self.config.INDEX)

    class Config:
        arbitrary_types_allowed = True

    def get_commit_index(  # type: ignore # pylint: disable=arguments-differ
        self,
        ref: Union[str, git.Reference, None],
        allow_to_not_exist: bool = True,
        ignore_corrupted: bool = False,
    ) -> Optional[Index]:
        if not ref or isinstance(ref, str):
            ref = resolve_ref(self.repo, ref)
        if self.config.INDEX in ref.tree:
            try:
                return Index.read(
                    (ref.tree / self.config.INDEX).data_stream,
                    frozen=True,
                )
            except WrongArtifactsYaml as e:
                logger.warning("Corrupted artifacts.yaml file in commit %s", ref)
                if ignore_corrupted:
                    return None
                raise e
        if allow_to_not_exist:
            return None
        raise ValueError(f"No Index exists at {ref}")

    def get_history(self) -> Dict[str, Index]:
        commits = {
            commit
            for branch in self.repo.heads
            for commit in traverse_commit(branch.commit)
        }
        return {
            commit.hexsha: self.get_commit_index(commit)  # type: ignore
            for commit in commits
            if self.config.INDEX in commit.tree
        }

    def artifact_centric_representation(self) -> ArtifactsCommits:
        representation = defaultdict(dict)  # type: ArtifactsCommits
        for commit, index in self.get_history().items():
            for art in index.state:
                representation[art][commit] = index.state[art]
        return representation

    def check_existence(self, name, commit):
        return name in self.get_commit_index(commit)

    def assert_existence(self, name, commit):
        if not self.check_existence(name, commit):
            raise ArtifactNotFound(name)


class EnrichmentManager(BaseManager, RemoteRepoMixin):
    actions: FrozenSet[Action] = frozenset()

    @classmethod
    def from_local_repo(cls, repo: Union[str, Repo], config: RegistryConfig = None):
        if isinstance(repo, str):
            repo = git.Repo(repo, search_parent_directories=True)
        if config is None:
            config = read_registry_config(
                os.path.join(repo.working_dir, CONFIG_FILE_NAME)
            )
        return cls(repo=repo, config=config)

    def describe(self, name: str, rev: str = None) -> List[EnrichmentInfo]:
        enrichments = self.config.enrichments
        res = []
        gto_enrichment = enrichments.pop("gto")
        gto_info = gto_enrichment.describe(self.repo, name, rev)
        if gto_info:
            res.append(gto_info)
            path = gto_info.get_path()  # type: ignore
            for enrichment in enrichments.values():
                enrichment_data = enrichment.describe(self.repo, path, rev)
                if enrichment_data is not None:
                    res.append(enrichment_data)
        return res

    def get_commits(self, all_branches=False, all_commits=False):
        if not self.repo.refs:
            return {}
        if all_commits:
            return {
                commit
                for branch in self.repo.heads
                for commit in traverse_commit(branch.commit)
            }
        if all_branches:
            return {branch.commit for branch in self.repo.heads}
        return {self.repo.commit()}

    def update_state(
        self,
        state: BaseRegistryState,
        all_branches=False,
        all_commits=False,
    ) -> BaseRegistryState:
        # processing registered artifacts and versions first
        for artifact in state.get_artifacts().values():
            for version in artifact.versions:
                commit = self.repo.commit(version.commit_hexsha)
                enrichments = self.describe(
                    artifact.artifact,
                    # faster to make git.Reference here
                    rev=commit,
                )
                version.add_event(
                    EnrichmentEvent(
                        artifact=artifact.artifact,
                        version=version.version,
                        created_at=datetime.fromtimestamp(commit.committed_date),
                        author=commit.author.name,
                        author_email=commit.author.email,
                        commit_hexsha=commit.hexsha,
                        message=commit.message,
                        committer=commit.committer.name,
                        committer_email=commit.committer.email,
                        enrichments=enrichments,
                    )
                )
                state.update_artifact(artifact)
        for commit in self.get_commits(
            all_branches=all_branches, all_commits=all_commits
        ):
            for art_name in GTOEnrichment().discover(self.repo, commit):
                enrichments = self.describe(art_name, rev=commit)
                artifact = state.find_artifact(art_name, create_new=True)
                version = artifact.find_version(
                    commit_hexsha=commit.hexsha, create_new=True
                )
                version.add_event(
                    EnrichmentEvent(
                        artifact=artifact.artifact,
                        version=version.version,
                        created_at=datetime.fromtimestamp(commit.committed_date),
                        author=commit.author.name,
                        author_email=commit.author.email,
                        commit_hexsha=commit.hexsha,
                        message=commit.message,
                        committer=commit.committer.name,
                        committer_email=commit.committer.email,
                        enrichments=enrichments,
                    )
                )
                state.update_artifact(artifact)
        return state


class GTOInfo(EnrichmentInfo):
    source = "gto"
    artifact: Artifact

    def get_object(self) -> BaseModel:
        return self.artifact

    def get_human_readable(self) -> str:
        return self.artifact.json()

    def get_path(self):
        return self.artifact.path


class GTOEnrichment(EnrichmentReader):
    source = "gto"

    def discover(  # pylint: disable=no-self-use
        self, repo, rev: Optional[Union[git.Reference, str]]
    ) -> Dict[str, GTOInfo]:
        with RepoIndexManager.from_repo(repo) as index:
            index = index.get_commit_index(rev)
        if index:
            return {
                name: GTOInfo(artifact=artifact)
                for name, artifact in index.state.items()
            }
        return {}

    def describe(  # pylint: disable=no-self-use
        self, repo, obj: str, rev: Optional[Union[git.Reference, str]]
    ) -> Optional[GTOInfo]:
        with RepoIndexManager.from_repo(repo) as index:
            index = index.get_commit_index(rev)
        if index and obj in index.state:
            return GTOInfo(artifact=index.state[obj])
        return None
