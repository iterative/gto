import git

from gitops.base import BaseRegistry
from gitops.branch import BranchEnvManager

from .config import CONFIG
from .tag import TagEnvManager, TagVersionManager

VERSION_MAPPING = {"tag": TagVersionManager}
ENV_MAPPING = {"tag": TagEnvManager, "branch": BranchEnvManager}


def init_registry(repo=".", config=CONFIG):
    repo = git.Repo(repo)

    if config.VERSION_BASE not in VERSION_MAPPING or config.ENV_BASE not in ENV_MAPPING:
        raise ValueError("Other implementations except of tag-based aren't supported")
    return BaseRegistry(
        repo=repo,
        version_manager=VERSION_MAPPING[config.VERSION_BASE](repo=repo),
        env_manager=ENV_MAPPING[config.ENV_BASE](repo=repo),
    )
