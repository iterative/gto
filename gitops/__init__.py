import git

from gitops.base import BaseRegistry
from gitops.branch import BranchEnvManager

from .config import CONFIG
from .constants import BRANCH, TAG
from .tag import TagEnvManager, TagVersionManager

VERSION_MAPPING = {TAG: TagVersionManager}
ENV_MAPPING = {TAG: TagEnvManager, BRANCH: BranchEnvManager}


def init_registry(repo=".", config=CONFIG):
    repo = git.Repo(repo)

    print(config)
    return BaseRegistry(
        repo=repo,
        version_manager=VERSION_MAPPING[config.VERSION_BASE](repo=repo),
        env_manager=ENV_MAPPING[config.ENV_BASE](repo=repo),
    )
