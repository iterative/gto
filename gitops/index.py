import os
from collections import defaultdict
from typing import Dict, Generator, List, Optional, Tuple

import git
from pydantic import BaseModel
from ruamel.yaml import safe_dump, safe_load

from .config import CONFIG
from .exceptions import ObjectNotFound


class Object(BaseModel):
    name: str
    path: str
    type: str


class BaseIndex(BaseModel):
    state: List[Object]

    def check_existense(self, name):
        return name in self.state

    def load(self):
        raise NotImplementedError


class FileIndex(BaseIndex):
    def add(self, name, type, path):
        self.state.append(Object(name=name, type=type, path=path))

    def load(self):
        state = []
        if os.path.exists(CONFIG.INDEX):
            with open(CONFIG.INDEX, encoding="utf8") as indexfile:
                state = safe_load(indexfile.read())
        self.state = state or []

    def dump(self) -> None:
        with open(CONFIG.INDEX, "w", encoding="utf8") as indexfile:
            indexfile.write(safe_dump(self.state))


class CommitIndex(BaseIndex):
    repo: git.Repo
    ref: Optional[str]

    def load(self):
        self.state = safe_load(
            (self.repo.commit(self.ref).tree / CONFIG.INDEX).data_stream.read()
        )


class BaseIndexManager(BaseModel):
    @staticmethod
    def get_file_index():
        index = FileIndex()
        index.load()
        return index

    def add(self, name, type, path):
        index = self.get_file_index()
        index.add(name, type, path)
        index.dump()


class NoRepoIndexManager(BaseIndexManager):
    pass


ObjectCommits = Dict[str, List[str]]


class RepoIndexManager(BaseIndexManager):
    repo: git.Repo

    class Config:
        arbitrary_types_allowed = True

    def get_commit_index(self, ref=None):
        index = CommitIndex(repo=self.repo, ref=ref)
        index.load()
        return index

    def read_index(self):
        commits = {
            commit.hexsha
            for branch in self.repo.heads
            for commit in traverse_commit(branch.commit)
        }
        repo_index = {}
        for commit in commits:
            if CONFIG.INDEX in commit.tree:
                index = CommitIndex(ref=commit.hexsha)
                index.load()
                repo_index[commit.hexsha] = index
        return repo_index

    def object_centric_representation(self) -> ObjectCommits:
        representation = defaultdict(list)
        for commit, index in self.read_index().items():
            for obj in index.state:
                representation[obj.name].append(commit)
        return representation

    def check_existence(self, name, commit):
        return self.get_commit_index(commit).check_existense(name)

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
