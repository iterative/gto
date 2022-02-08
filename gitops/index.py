from typing import Dict, Generator, List, Tuple

import git
from pydantic import BaseModel
from ruamel.yaml import load

from .config import CONFIG


class Object(BaseModel):
    name: str
    path: str
    category: str


class Index(BaseModel):
    objects: List[Object]


class RepoIndex(BaseModel):
    commits: Dict[str, Index]


def traverse_commit(
    commit: git.Commit,
) -> Generator[Tuple[git.Commit, Dict], None, None]:
    if CONFIG.INDEX in commit.tree:
        yield commit, load((commit.tree / CONFIG.INDEX).data_stream.read())
    for parent in commit.parents:
        yield from traverse_commit(parent)


def read_index(repo: git.Repo) -> Dict[git.Commit, Dict]:
    return {
        commit: index
        for branch in repo.heads
        for commit, index in traverse_commit(branch.commit)
    }
