from collections import defaultdict
from typing import Dict, Generator, List, Tuple

import git
from pydantic import BaseModel
from ruamel.yaml import safe_load

from gitops.exceptions import ObjectNotFound

from .config import CONFIG


class Object(BaseModel):
    name: str
    path: str
    type: str


Index = List[Object]
# RepoIndexState = Dict[git.Commit, Index]


class RepoIndexState(BaseModel):
    index: Dict[str, Index]

    class Config:
        arbitrary_types_allowed = True

    def check_existence(self, name, commit):
        return any(obj.name == name for obj in self.index[commit])

    def assert_existence(self, name, commit):
        if not self.check_existence(name, commit):
            raise ObjectNotFound(name)

    def object_centric_representation(self) -> Dict[str, List[str]]:
        representation = defaultdict(list)
        for commit, index in self.index.items():
            for obj in index:
                representation[obj.name].append(commit)
        return representation


def traverse_commit(
    commit: git.Commit,
) -> Generator[Tuple[git.Commit, Index], None, None]:
    if CONFIG.INDEX in commit.tree:
        yield commit, safe_load((commit.tree / CONFIG.INDEX).data_stream.read())
    for parent in commit.parents:
        yield from traverse_commit(parent)


def read_index(repo: git.Repo) -> RepoIndexState:
    return RepoIndexState(
        index={
            commit.hexsha: index
            for branch in repo.heads
            for commit, index in traverse_commit(branch.commit)
        }
    )
