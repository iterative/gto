from tempfile import TemporaryDirectory
from typing import Union

from git import Repo, InvalidGitRepositoryError, NoSuchPathError

from gto.exceptions import NoRepo

# TODO: get rid of tmp_repo_dir
tmp_repo_dir = TemporaryDirectory()


# TODO: make a new type out of Union[str, Repo]
def convert_to_git_repo(repo: Union[Repo, str]) -> Repo:
    if isinstance(repo, str):
        try:
            repo = Repo(repo, search_parent_directories=True)
        except (InvalidGitRepositoryError, NoSuchPathError):
            try:
                git_clone(repo=repo, dir=tmp_repo_dir.name)
                repo = Repo(tmp_repo_dir.name, search_parent_directories=True)
            except (InvalidGitRepositoryError, NoSuchPathError):
                raise NoRepo(repo)
    return repo


def git_clone(repo: str, dir: str) -> None:
    Repo.clone_from(url=repo, to_path=dir)
