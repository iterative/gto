import os
from collections import defaultdict
from typing import Dict, Generator, List, Optional, Tuple

import git
from pydantic import BaseModel, ValidationError
from ruamel.yaml import safe_dump, safe_load

from .config import CONFIG
from .exceptions import ObjectNotFound


class Object(BaseModel):
    name: str
    path: str
    type: str


Index = List[Object]


class RepoIndexState(BaseModel):
    index: Dict[str, Index]

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


class RepoIndex(BaseModel):  # maybe this should be one class? Why we need State?
    repo: git.Repo
    state: Optional[RepoIndexState]

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_state()

    def update_state(self):
        self.state = read_index(self.repo)

    def load(self) -> Index:
        if os.path.exists(CONFIG.INDEX):
            with open(CONFIG.INDEX) as f:
                index = safe_load(f.read())
            if index is None:
                index = []
            return index
        return []

    def dump(self, index: Index) -> None:
        with open(CONFIG.INDEX, "w") as f:
            f.write(safe_dump(index))

    def add(self, name, type, path):
        checkouted_index = self.load()
        checkouted_index.append(Object(name=name, type=type, path=path))
        print(checkouted_index)
        self.dump(checkouted_index)


def traverse_commit(
    commit: git.Commit,
) -> Generator[Tuple[git.Commit, Index], None, None]:
    if CONFIG.INDEX in commit.tree:
        yield commit, safe_load((commit.tree / CONFIG.INDEX).data_stream.read())
    for parent in commit.parents:
        yield from traverse_commit(parent)


def read_index(repo: git.Repo) -> RepoIndexState:
    # need to check what we return here for the checkouted commit,
    # do we return unstaged changes
    # for tags-based you don't need unstaged changes
    # for file-based you need unstaged changes
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
