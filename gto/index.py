import os
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import ClassVar, Dict, Generator, List, Optional, Tuple, Union
from typing.io import IO

import git
from pydantic import BaseModel, parse_obj_as
from ruamel.yaml import safe_dump, safe_load

from .config import CONFIG
from .exceptions import GitopsException, ObjectNotFound


class Artifact(BaseModel):
    name: str
    path: str
    type: str


State = Dict[str, Artifact]


def not_frozen(f):
    @wraps(f)
    def inner(self: "BaseIndex", *args, **kwargs):
        if self.frozen:
            raise ValueError(f"Cannot {f.__name__}: {self.__class__} is frozen")
        return f(self, *args, **kwargs)
    return inner


class Index(BaseModel, ABC):
    state: State = {}  # TODO should not be populated until load() is called
    frozen: ClassVar[bool]

    def __contains__(self, item):
        return item in self.state
    @classmethod
    def read(cls, path_or_file: Union[str, IO]):
        index = Index()
        index.read_state(path_or_file)
        return index

    @staticmethod
    def read_state(path_or_file: Union[str, IO]):
        if isinstance(path_or_file, str):
            with open(path_or_file, "r") as f:
                return parse_obj_as(State, safe_load(f))
        return parse_obj_as(State, safe_load(path_or_file))

    def write_state(self, path_or_file: Union[str, IO]):
        if isinstance(path_or_file, str):
            with open(path_or_file, "w", encoding="utf8") as f:
                f.write(safe_dump(self.dict()["state"], default_flow_style=False))

    @not_frozen
    def add(self, name, type, path):
        if name in self:
            raise GitopsException(f"Artifact {name} already exists")
        self.state[name] = Artifact(name=name, type=type, path=path)

    @not_frozen
    def remove(self, name):
        if name not in self:
            raise GitopsException(f"Artifact {name} does not exist")
        del self.state[name]








class BaseIndexManager(BaseModel):
    current: Optional[Index]

    @abstractmethod
    def get_index(self) -> Index:
        raise NotImplementedError

    @abstractmethod
    def update(self):
        raise NotImplementedError

    @abstractmethod
    def get_history(self) -> Dict[str, Index]:
        raise NotImplementedError

    def add(self, name, type, path):
        index = self.get_index()
        index.add(name, type, path)
        self.update()

    def remove(self, name):
        index = self.get_index()
        index.remove(name)
        self.update()


class FileIndexManager(BaseIndexManager):
    path: str = ""

    @property
    def index_path(self):
        return str(Path(self.path) / CONFIG.INDEX)

    def get_index(self) -> Index:
        if os.path.exists(self.index_path):
            self.current = Index.read(self.index_path)
        return self.current or Index()

    def update(self):
        if self.current is not None:
            self.current.write_state(self.index_path)

    def get_history(self) -> Dict[str, Index]:
        raise NotImplementedError("Not a git repo: history is not available")

    # maybe we don't need this at all
    # are there some additional methods/things to do
    # when there is no repo (compared to the case when we have a repo)?


ObjectCommits = Dict[str, List[str]]


class RepoIndexManager(BaseIndexManager):
    repo: git.Repo


    @property
    def index_path(self):
        # TODO: config should be loaded from repo too
        return os.path.join(self.repo.git_dir, CONFIG.INDEX)

    class Config:
        arbitrary_types_allowed = True

    def get_index(self) -> Index:
        self.current = Index.read(self.index_path)
        return self.current

    def update(self):
        if self.current is not None:
            self.current.write_state(self.index_path)

    def get_commit_index(self, ref: str):
        index = Index.read((self.repo.commit(ref).tree / CONFIG.INDEX).data_stream)
        return index

    def get_history(self) -> Dict[str, Index]:
        commits = {
            commit
            for branch in self.repo.heads
            for commit in traverse_commit(branch.commit)
        }
        repo_index = {}
        for commit in commits:
            if CONFIG.INDEX in commit.tree:
                repo_index[commit.hexsha] = self.get_commit_index(commit.hexsha)
        return repo_index

    def object_centric_representation(self) -> ObjectCommits:
        representation = defaultdict(list)
        for commit, index in self.get_history().items():
            for obj in index.state:
                representation[obj].append(commit)
        return representation

    def check_existence(self, name, commit):
        return name in self.get_commit_index(commit)

    def assert_existence(self, name, commit):
        if not self.check_existence(name, commit):
            raise ObjectNotFound(name)


def traverse_commit(
    commit: git.Commit,
) -> Generator[Tuple[git.Commit], None, None]:
    yield commit
    for parent in commit.parents:
        yield from traverse_commit(parent)


# try:
#     # list of items
#     return RepoIndexState(index=index)
# except ValidationError:
#     try:
#         # dict with aliases as keys
#         return RepoIndexState(
#             index={
#                 hexsha: [
#                     Object(name=name, path=details["path"], type=details["type"])
#                     for name, details in index_at_commit.items()  # type: ignore
#                 ]
#                 for hexsha, index_at_commit in index.items()
#             }
#         )
#     except (ValidationError, TypeError):
#         # dict with types as keys
#         return RepoIndexState(
#             index={
#                 hexsha: [
#                     Object(name=el["name"], path=el["path"], type=type_)
#                     for type_, elements in index_at_commit.items()  # type: ignore
#                     for el in elements
#                 ]
#                 for hexsha, index_at_commit in index.items()
#             }
#         )
