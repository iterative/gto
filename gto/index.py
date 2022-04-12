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
)
from gto.ext import Enrichment, EnrichmentInfo


class Artifact(BaseModel):
    type: str
    name: str
    path: str
    virtual: bool = False
    tags: List[str] = []  # TODO: allow key:value labels
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
                yaml.dump(self.dict()["state"], file)

    @not_frozen
    def add(self, type, name, path, virtual, tags, description, update) -> Artifact:
        if name in self and not update:
            raise ArtifactExists(name)
        if find_repeated_path(path, [a.path for a in self.state.values()]) is not None:
            raise PathIsUsed(type=type, name=name, path=path)
        if update and name in self.state:
            self.state[name].type = type or self.state[name].type
            self.state[name].name = name or self.state[name].name
            self.state[name].path = path or self.state[name].path
            self.state[name].virtual = virtual or self.state[name].virtual
            self.state[name].tags = tags or self.state[name].tags
            self.state[name].description = description or self.state[name].description
        else:
            self.state[name] = Artifact(
                type=type,
                name=name,
                path=path,
                virtual=virtual,
                tags=tags,
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

    def add(self, type, name, path, virtual, tags, description, update):
        if tags is None:
            tags = []
        self.config.assert_type(type)
        if not virtual and not check_if_path_exists(
            path, self.repo if hasattr(self, "repo") else None
        ):
            raise NoFile(path)
        index = self.get_index()
        index.add(
            type, name, path, virtual, tags=tags, description=description, update=update
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
        self, ref: str, allow_to_not_exist: bool = True
    ) -> Optional[Index]:
        if self.config.INDEX in self.repo.commit(ref).tree:
            return Index.read(
                (self.repo.commit(ref).tree / self.config.INDEX).data_stream,
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

        # TODO: add as arg?
        config = RegistryConfig(
            CONFIG_FILE_NAME=os.path.join(self.repo.working_dir, CONFIG_FILE_NAME)
        )
        enrichments = config.enrichments
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
        discover: bool = False,
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
        if discover:
            for commit in self.get_commits(
                all_branches=all_branches, all_commits=all_commits
            ):
                for enrichment in GTOEnrichment().discover(self.repo, commit):
                    enrichments = self.describe(enrichment.artifact.name, rev=commit)
                    artifact = state.find_artifact(
                        enrichment.artifact.name, create_new=True
                    )
                    version = artifact.find_version(commit_hexsha=commit.hexsha)
                    # TODO: duplicated in tag.py
                    if version:
                        version = version.name
                    else:
                        artifact.add_version(
                            BaseVersion(
                                artifact=enrichment.artifact.name,
                                name=commit.hexsha,
                                creation_date=datetime.fromtimestamp(
                                    commit.committed_date
                                ),
                                author=commit.author.name,
                                commit_hexsha=commit.hexsha,
                                discovered=True,
                            )
                        )
                        version = commit.hexsha
                    artifact.update_enrichments(
                        version=version, enrichments=enrichments
                    )
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
        description = f"""GTO artifact: {self.artifact}"""
        return description

    def get_path(self):
        return self.artifact.path


class GTOEnrichment(Enrichment):
    source = "gto"

    def discover(  # pylint: disable=no-self-use
        self, repo, rev: Optional[str]
    ) -> List[GTOInfo]:
        index = RepoIndexManager.from_repo(repo).get_commit_index(rev)
        if index:
            return [GTOInfo(artifact=artifact) for artifact in index.state.values()]
        return []

    def describe(  # pylint: disable=no-self-use
        self, repo, obj: str, rev: Optional[str]
    ) -> Optional[GTOInfo]:
        index = RepoIndexManager.from_repo(repo).get_commit_index(rev)
        if obj in index.state:
            return GTOInfo(artifact=index.state[obj])
        return None
