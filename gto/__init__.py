import git

import gto.log  # noqa
from gto.base import GitRegistry
from gto.config import CONFIG
from gto.index import FileIndexManager, RepoIndexManager


def init_registry(repo=".", config=CONFIG):
    repo = git.Repo(repo)

    return GitRegistry(
        repo=repo,
        version_manager=CONFIG.VERSION_MANAGERS_MAPPING[config.VERSION_BASE](repo=repo),
        env_manager=CONFIG.ENV_MANAGERS_MAPPING[config.ENV_BASE](repo=repo),
    )


def init_index(path: str = ""):
    try:
        return RepoIndexManager(repo=git.Repo(path))
    except Exception:  # TODO repo not found exception
        return FileIndexManager(path=path)
