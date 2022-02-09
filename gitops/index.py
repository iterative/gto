from collections import defaultdict
from typing import Dict, Generator, List, Tuple

import git
from pydantic import BaseModel
from ruamel.yaml import load

from gitops.exceptions import ObjectNotFound

from .config import CONFIG


class Object(BaseModel):
    name: str
    path: str
    category: str


Index = List[Object]
# RepoIndexState = Dict[git.Commit, Index]


class RepoIndexState(BaseModel):
    index: Dict[git.Commit, Index]

    class Config:
        arbitrary_types_allowed = True

    def check_existence(self, category, object, commit):
        return any(
            obj.category == category and obj.name == object
            for obj in self.index[commit]
        )

    def assert_existence(self, category, object, commit):
        if not self.check_existence(category, object, commit):
            raise ObjectNotFound(category, object)

    def object_centric_representation(self) -> Dict[Tuple[str, str], List[git.Commit]]:
        representation = defaultdict(list)
        for commit, index in self.index.items():
            for obj in index:
                representation[(obj.category, obj.name)].append(commit)
        return representation


def traverse_commit(
    commit: git.Commit,
) -> Generator[Tuple[git.Commit, Index], None, None]:
    if CONFIG.INDEX in commit.tree:
        yield commit, load((commit.tree / CONFIG.INDEX).data_stream.read())
    for parent in commit.parents:
        yield from traverse_commit(parent)


def read_index(repo: git.Repo) -> RepoIndexState:
    return RepoIndexState(
        index={
            commit: index
            for branch in repo.heads
            for commit, index in traverse_commit(branch.commit)
        }
    )
