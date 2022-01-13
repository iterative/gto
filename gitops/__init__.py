import git

from .config import CONFIG
from .tag import TagBasedRegistry


def init_registry(repo: git.Repo = git.Repo("."), base=CONFIG.BASE):
    if base != "tag":
        raise ValueError("Other implementations except of tag-based aren't supported")
    base_map = {"tag": TagBasedRegistry}
    return base_map[base]()
