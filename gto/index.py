import os
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import IO, Dict, Generator, List, Optional, Union

import git
from pydantic import BaseModel, parse_obj_as
from ruamel.yaml import safe_dump, safe_load

from .config import CONFIG
from .exceptions import GTOException, ObjectNotFound


class Artifact(BaseModel):
    name: str
    path: str
    type: str


State = Dict[str, Artifact]


def not_frozen(func):
    @wraps(func)
    def inner(self: "Index", *args, **kwargs):
        if self.frozen:
            raise ValueError(f"Cannot {func.__name__}: {self.__class__} is frozen")
        return func(self, *args, **kwargs)

    return inner


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
                return parse_obj_as(State, safe_load(file))
        return parse_obj_as(State, safe_load(path_or_file))

    def write_state(self, path_or_file: Union[str, IO]):
        if isinstance(path_or_file, str):
            with open(path_or_file, "w", encoding="utf8") as file:
                file.write(safe_dump(self.dict()["state"], default_flow_style=False))

    @not_frozen
    def add(self, name, type, path):
        if name in self:
            raise GTOException(f"Artifact {name} already exists")
        self.state[name] = Artifact(name=name, type=type, path=path)

    @not_frozen
    def remove(self, name):
        if name not in self:
            raise GTOException(f"Artifact {name} does not exist")
        del self.state[name]


class BaseIndexManager(BaseModel, ABC):
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

    def index_path(self):
        return str(Path(self.path) / CONFIG.INDEX)

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


ObjectCommits = Dict[str, List[str]]


class RepoIndexManager(FileIndexManager):
    repo: git.Repo

    @classmethod
    def from_repo(cls, repo: Union[str, git.Repo]):
        if isinstance(repo, str):
            repo = git.Repo(repo)
        return cls(repo=repo)

    def index_path(self):
        # TODO: config should be loaded from repo too
        return os.path.join(os.path.dirname(self.repo.git_dir), CONFIG.INDEX)

    class Config:
        arbitrary_types_allowed = True

    def get_commit_index(self, ref: str) -> Index:
        return Index.read(
            (self.repo.commit(ref).tree / CONFIG.INDEX).data_stream, frozen=True
        )

    def get_history(self) -> Dict[str, Index]:
        commits = {
            commit
            for branch in self.repo.heads
            for commit in traverse_commit(branch.commit)
        }
        return {
            commit.hexsha: self.get_commit_index(commit.hexsha)
            for commit in commits
            if CONFIG.INDEX in commit.tree
        }

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


def traverse_commit(commit: git.Commit) -> Generator[git.Commit, None, None]:
    yield commit
    for parent in commit.parents:
        yield from traverse_commit(parent)
