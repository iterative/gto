from tempfile import TemporaryDirectory
from typing import Union
from unittest.mock import patch

import pytest
from git import Repo

from gto.git_utils import git_clone, git_clone_if_repo_is_remote
from tests.git_utils.data import get_example_http_remote_repo
from tests.skip_presets import (
    only_for_windows_py_lt_3_8,
    skip_for_windows_py_lt_3_9,
)


def test_if_repo_is_a_meaningless_string_then_leave_it_unchanged():
    assert_f_called_with_repo_return_repo(repo="meaningless_string")


def test_if_repo_is_a_local_git_repo_then_leave_it_unchanged(tmp_local_git_repo):
    assert_f_called_with_repo_return_repo(repo=tmp_local_git_repo)


def test_if_repo_gitpython_object_then_leave_it_unchanged(tmp_local_git_repo):
    assert_f_called_with_repo_return_repo(repo=Repo(path=tmp_local_git_repo))


@skip_for_windows_py_lt_3_9
def test_if_repo_is_remote_url_then_clone_and_set_repo_to_its_local_path():
    with patch("gto.git_utils.git_clone") as mocked_git_clone:
        mocked_git_clone.side_effect = git_clone
        local_repo = decorated_func(repo=get_example_http_remote_repo(), spam=0, jam=3)
        mocked_git_clone.assert_called_once_with(
            repo=get_example_http_remote_repo(), dir=local_repo
        )


@only_for_windows_py_lt_3_8
def test_if_repo_is_remote_url_and_windows_os_error_then_hint_win_with_py_lt_3_9_may_be_the_cause():
    with pytest.raises(OSError) as e:
        decorated_func(repo=get_example_http_remote_repo(), spam=0, jam=3)
    assert e.type in (NotADirectoryError, PermissionError)
    assert "windows" in str(e)
    assert "python" in str(e)
    assert "< 3.9" in str(e)


@git_clone_if_repo_is_remote
def decorated_func(
    spam: int, repo: Union[Repo, str], jam: int
):  # pylint: disable=unused-argument
    return repo


def assert_f_called_with_repo_return_repo(repo: Union[str, Repo]) -> None:
    assert decorated_func(0, repo, 3) is repo
    assert decorated_func(0, repo, jam=3) is repo
    assert decorated_func(0, jam=3, repo=repo) is repo
    assert decorated_func(spam=0, jam=3, repo=repo) is repo


@pytest.fixture
def tmp_local_git_repo() -> str:
    tmp_repo_dir = TemporaryDirectory()  # pylint: disable=consider-using-with
    Repo.init(path=tmp_repo_dir.name)
    yield tmp_repo_dir.name
    tmp_repo_dir.cleanup()