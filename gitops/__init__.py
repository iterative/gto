import git

from .config import CONFIG
from .tag import TagBasedRegistry

BASE_MAP = {"tag": TagBasedRegistry}


def init_registry(repo=".", base=CONFIG.BASE):
    repo = git.Repo(repo)
    if base not in BASE_MAP:
        raise ValueError("Other implementations except of tag-based aren't supported")
    return BASE_MAP[base](repo=repo)
