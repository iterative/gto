import git

from .config import CONFIG
from .tag import TagBasedRegistry

BASE_MAPPING = {"tag": TagBasedRegistry}


def init_registry(repo=".", base=CONFIG.BASE):
    repo = git.Repo(repo)
    if base not in BASE_MAPPING:
        raise ValueError("Other implementations except of tag-based aren't supported")
    return BASE_MAPPING[base](repo=repo)
