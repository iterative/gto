from collections import defaultdict
from typing import Dict, Generator, List, Tuple

import git
from pydantic import BaseModel, ValidationError
from ruamel.yaml import safe_load

from gto.exceptions import ObjectNotFound

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
    index = {
        commit.hexsha: index
        for branch in repo.heads
        for commit, index in traverse_commit(branch.commit)
    }
    try:
        # list of items
        return RepoIndexState(index=index)
    except ValidationError:
        try:
            # dict with aliases as keys
            return RepoIndexState(
                index={
                    hexsha: [
                        Object(name=name, path=details["path"], type=details["type"])
                        for name, details in index_at_commit.items()  # type: ignore
                    ]
                    for hexsha, index_at_commit in index.items()
                }
            )
        except (ValidationError, TypeError):
            # dict with types as keys
            return RepoIndexState(
                index={
                    hexsha: [
                        Object(name=el["name"], path=el["path"], type=type_)
                        for type_, elements in index_at_commit.items()  # type: ignore
                        for el in elements
                    ]
                    for hexsha, index_at_commit in index.items()
                }
            )
