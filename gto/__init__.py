import git

from gto.base import GitRegistry
from gto.config import CONFIG
from gto.index import NoRepoIndexManager

print(CONFIG)


def init_registry(repo=".", config=CONFIG):
    repo = git.Repo(repo)

    return GitRegistry(
        repo=repo,
        version_manager=CONFIG.VERSION_MANAGERS_MAPPING[config.VERSION_BASE](repo=repo),
        env_manager=CONFIG.ENV_MANAGERS_MAPPING[config.ENV_BASE](repo=repo),
    )


def init_index():
    return NoRepoIndexManager()
