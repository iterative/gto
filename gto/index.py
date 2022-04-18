import os
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import IO, Dict, FrozenSet, Generator, List, Optional, Union

import git
from pydantic import BaseModel, parse_obj_as

from gto.base import BaseManager, BaseRegistryState, BaseVersion
from gto.config import CONFIG_FILE_NAME, RegistryConfig, yaml
from gto.constants import Action
from gto.exceptions import (
    ArtifactExists,
    ArtifactNotFound,
    NoFile,
    NoRepo,
    PathIsUsed,
    WrongArgs,
)
from gto.ext import Enrichment, EnrichmentInfo
from gto.utils import resolve_ref


class Artifact(BaseModel):
    type: Optional[str] = None
    path: Optional[str] = None
    virtual: bool = True
    labels: List[str] = []  # TODO: allow key:value labels
    description: str = ""


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

    def __contains__(self, item):
        return item in self.state

    @classmethod
    def read(cls, path_or_file: Union[str, IO], frozen: bool = False):
        index = cls(frozen=frozen)
        index.state = index.read_state(path_or_file)
        return index

    @staticmethod
    def read_state(path_or_file: Union[str, IO]):
        if isinstance(path_or_file, str):
            with open(path_or_file, "r", encoding="utf8") as file:
                return parse_obj_as(State, yaml.load(file))
        return parse_obj_as(State, yaml.load(path_or_file))

    def write_state(self, path_or_file: Union[str, IO]):
        if isinstance(path_or_file, str):
            with open(path_or_file, "w", encoding="utf8") as file:
                state = self.dict(exclude_defaults=True).get("state", {})
                yaml.dump(state, file)

    @not_frozen
    def add(
        self, name, type, path, must_exist, labels, description, update
    ) -> Artifact:
        if name in self and not update:
            raise ArtifactExists(name)
        if (
            must_exist
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
            self.state[name].labels = labels or self.state[name].labels
            self.state[name].description = description or self.state[name].description
        else:
            self.state[name] = Artifact(
                type=type,
                path=path,
                virtual=not must_exist,
                labels=labels,
                description=description,
            )
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

    def add(self, name, type, path, must_exist, labels, description, update):
        if labels is None:
            labels = []
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
            labels=labels,
            description=description,
            update=update,
        )
        self.update()

    def remove(self, name):
        index = self.get_index()
        index.remove(name)
        self.update()


class FileIndexManager(BaseIndexManager):
    path: str = ""

    @classmethod
    def from_path(cls, path: str, config: RegistryConfig = None):
        if config is None:
            config = RegistryConfig(
                CONFIG_FILE_NAME=os.path.join(path, CONFIG_FILE_NAME)
            )
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


ArtifactCommits = Dict[str, Artifact]
ArtifactsCommits = Dict[str, ArtifactCommits]


class RepoIndexManager(FileIndexManager):
    repo: git.Repo

    @classmethod
    def from_repo(cls, repo: Union[str, git.Repo], config: RegistryConfig = None):
        if isinstance(repo, str):
            try:
                repo = git.Repo(repo, search_parent_directories=True)
            except git.InvalidGitRepositoryError as e:
                raise NoRepo(repo) from e
        if config is None:
            config = RegistryConfig(
                CONFIG_FILE_NAME=os.path.join(repo.working_dir, CONFIG_FILE_NAME)
            )
        return cls(repo=repo, config=config)

    def index_path(self):
        # TODO: config should be loaded from repo too
        return os.path.join(os.path.dirname(self.repo.git_dir), self.config.INDEX)

    class Config:
        arbitrary_types_allowed = True

    def get_commit_index(
        self, ref: Union[str, git.Reference, None], allow_to_not_exist: bool = True
    ) -> Optional[Index]:
        if not ref or isinstance(ref, str):
            ref = resolve_ref(self.repo, ref)
        if self.config.INDEX in ref.tree:
            return Index.read(
                (ref.tree / self.config.INDEX).data_stream,
                frozen=True,
            )
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
            commit.hexsha: self.get_commit_index(commit.hexsha)  # type: ignore
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


class EnrichmentManager(BaseManager):
    actions: FrozenSet[Action] = frozenset()

    @classmethod
    def from_repo(cls, repo, config: RegistryConfig = None):
        if isinstance(repo, str):
            repo = git.Repo(repo, search_parent_directories=True)
        if config is None:
            config = RegistryConfig(
                CONFIG_FILE_NAME=os.path.join(repo.working_dir, CONFIG_FILE_NAME)
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
        # discover: bool = False,
        all_branches=False,
        all_commits=False,
    ) -> BaseRegistryState:
        # processing registered artifacts and versions first
        for artifact in state.get_artifacts().values():
            for version in artifact.versions:
                enrichments = self.describe(artifact.name, rev=version.commit_hexsha)
                artifact.update_enrichments(
                    version=version.name, enrichments=enrichments
                )
                state.update_artifact(artifact)
        # do discovery if requested
        # if discover:
        for commit in self.get_commits(
            all_branches=all_branches, all_commits=all_commits
        ):
            for art_name in GTOEnrichment().discover(self.repo, commit):
                enrichments = self.describe(art_name, rev=commit)
                artifact = state.find_artifact(art_name, create_new=True)
                version = artifact.find_version(commit_hexsha=commit.hexsha)
                # TODO: duplicated in tag.py
                if version:
                    version = version.name
                else:
                    artifact.add_version(
                        BaseVersion(
                            artifact=art_name,
                            name=commit.hexsha,
                            creation_date=datetime.fromtimestamp(commit.committed_date),
                            author=commit.author.name,
                            commit_hexsha=commit.hexsha,
                            discovered=True,
                        )
                    )
                    version = commit.hexsha
                artifact.update_enrichments(version=version, enrichments=enrichments)
                state.update_artifact(artifact)
        return state

    def check_ref(self, ref: str, state: BaseRegistryState):
        # TODO: implement
        raise NotImplementedError()


def init_index_manager(path):
    try:
        return RepoIndexManager.from_repo(path)
    except NoRepo:
        return FileIndexManager.from_path(path)


class GTOInfo(EnrichmentInfo):
    source = "gto"
    artifact: Artifact

    def get_object(self) -> BaseModel:
        return self.artifact

    def get_human_readable(self) -> str:
        return self.artifact.json()

    def get_path(self):
        return self.artifact.path


class GTOEnrichment(Enrichment):
    source = "gto"

    def discover(  # pylint: disable=no-self-use
        self, repo, rev: Optional[str]
    ) -> Dict[str, GTOInfo]:
        index = RepoIndexManager.from_repo(repo).get_commit_index(rev)
        if index:
            return {
                name: GTOInfo(artifact=artifact)
                for name, artifact in index.state.items()
            }
        return {}

    def describe(  # pylint: disable=no-self-use
        self, repo, obj: str, rev: Optional[str]
    ) -> Optional[GTOInfo]:
        index = RepoIndexManager.from_repo(repo).get_commit_index(rev)
        if index and obj in index.state:
            return GTOInfo(artifact=index.state[obj])
        return None
