import git

from .base import BaseRegistry
from .config import CONFIG

print(CONFIG)


def init_registry(repo=".", config=CONFIG):
    repo = git.Repo(repo)

    return BaseRegistry(
        repo=repo,
        version_manager=CONFIG.VERSION_MANAGERS_MAPPING[config.VERSION_BASE](repo=repo),
        env_manager=CONFIG.ENV_MANAGERS_MAPPING[config.ENV_BASE](repo=repo),
    )
