import git

from .config import CONFIG
from .tag import TagBasedRegistry


def init_registry(repo=".", base=CONFIG.BASE):
    repo = git.Repo(repo)
    if base != "tag":
        raise ValueError("Other implementations except of tag-based aren't supported")
    base_map = {"tag": TagBasedRegistry}
    return base_map[base](repo=repo)
