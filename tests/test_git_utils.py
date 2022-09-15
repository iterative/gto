from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union
from unittest.mock import patch

import pytest
from git import Repo

from gto.git_utils import git_clone, git_clone_if_repo_is_remote
from tests.data.remote_repositories import get_all_examples


def test_git_clone_if_repo_is_remote__if_repo_is_a_meaningless_string_then_leave_it_unchanged():
    repo = "meaningless_string"
    assert_f_called_with_repo_return_repo(repo=repo)


def test_git_clone_if_repo_is_remote__if_repo_is_a_local_git_repo_then_leave_it_unchanged(tmp_local_git_repo):
    repo = tmp_local_git_repo
    assert_f_called_with_repo_return_repo(repo=repo)


def test_git_clone_if_repo_is_remote__if_repo_gitpython_object_then_leave_it_unchanged(tmp_local_git_repo):
    repo = Repo(path=tmp_local_git_repo)
    assert_f_called_with_repo_return_repo(repo=repo)


@pytest.mark.parametrize("remote_repo", get_all_examples())
def test_git_clone_if_repo_is_remote__if_repo_is_remote_url_then_clone_and_set_repo_to_its_local_path(remote_repo: str):
    with patch("gto.git_utils.git_clone") as mocked_git_clone:
        mocked_git_clone.side_effect = git_clone
        local_repo = f(repo=remote_repo, spam=0, jam=3)
        mocked_git_clone.assert_called_once_with(repo=remote_repo, dir=local_repo)


@pytest.mark.parametrize("repo", get_all_examples())
def test_git_clone__clone_remote_git_repo_in_specified_folder(repo: str):
    with TemporaryDirectory() as tmp_repo_dir:
        git_clone(repo=repo, dir=tmp_repo_dir)
        assert_dir_contain_git_repo(dir=tmp_repo_dir)


@git_clone_if_repo_is_remote
def f(spam: int, repo: Union[Repo, str], jam: int):
    return repo


def assert_f_called_with_repo_return_repo(repo: Union[str, Repo]) -> None:
    assert f(0, repo, 3) is repo
    assert f(0, repo, jam=3) is repo
    assert f(0, jam=3, repo=repo) is repo
    assert f(spam=0, jam=3, repo=repo) is repo


@pytest.fixture
def tmp_local_git_repo() -> str:
    tmp_repo_dir = TemporaryDirectory()
    Repo.init(path=tmp_repo_dir.name)
    yield tmp_repo_dir.name
    tmp_repo_dir.cleanup()


def assert_dir_contain_git_repo(dir: str) -> None:
    assert (Path(dir) / ".git").is_dir()
    assert (Path(dir) / ".git/HEAD").is_file()
