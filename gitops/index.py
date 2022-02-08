from typing import List

from pydantic import BaseModel
from ruamel.yaml import load

from .config import CONFIG


class Object(BaseModel):
    name: str
    path: str
    category: str


class Index(BaseModel):
    objects: List[Object]


class CommitIndex(BaseModel):
    hexsha: str
    index: Index


class RepoIndex(BaseModel):
    commits: List[CommitIndex]


def read_index():

    with open(CONFIG.INDEX, encoding="utf8") as index_file:
        index = load(index_file)
    return index
