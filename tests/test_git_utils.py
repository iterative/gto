from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union
from unittest.mock import MagicMock, patch

import pytest
from git import Repo

import tests.resources
from gto.exceptions import GTOException
from gto.git_utils import (
    auto_push_on_remote_repo,
    git_clone,
    git_clone_remote_repo,
    git_push_tag,
    is_url_of_remote_repo,
)
from tests.skip_presets import (
    only_for_windows_py_lt_3_8,
    skip_for_windows_py_lt_3_9,
)


def test_git_clone_remote_repo_if_repo_is_a_meaningless_string_then_leave_it_unchanged():
    assert_f_called_with_repo_return_repo_itself(repo="meaningless_string")


def test_git_clone_remote_repo_if_repo_is_a_local_git_repo_then_leave_it_unchanged(
    tmp_local_git_repo: str,
):
    assert_f_called_with_repo_return_repo_itself(repo=tmp_local_git_repo)


def test_git_clone_remote_repo_if_repo_gitpython_object_then_leave_it_unchanged(
    tmp_local_git_repo: str,
):
    assert_f_called_with_repo_return_repo_itself(repo=Repo(path=tmp_local_git_repo))


@skip_for_windows_py_lt_3_9
def test_git_clone_remote_repo_if_repo_is_remote_url_then_clone_and_set_repo_to_its_local_path():
    with patch("gto.git_utils.git_clone") as mocked_git_clone:
        mocked_git_clone.side_effect = git_clone
        local_repo = decorated_read_func(
            repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, spam=0, jam=3
        )
        mocked_git_clone.assert_called_once_with(
            repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, dir=local_repo
        )


@only_for_windows_py_lt_3_8
def test_if_repo_is_remote_url_and_windows_os_error_then_hint_win_with_py_lt_3_9_may_be_the_cause():
    with pytest.raises(OSError) as e:
        decorated_read_func(repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, spam=0, jam=3)
    assert e.type in (NotADirectoryError, PermissionError)
    assert "windows" in str(e)
    assert "python" in str(e)
    assert "< 3.9" in str(e)


@pytest.mark.parametrize(
    "repo",
    (
        "/local/path",
        "/local/path",
        ".",
    ),
)
def test_is_url_of_remote_repo_if_local_url_then_true(repo: str):
    assert is_url_of_remote_repo(repo=repo) is False


@pytest.mark.parametrize(
    "repo",
    (
        tests.resources.SAMPLE_HTTP_REMOTE_REPO,
        tests.resources.SAMPLE_HTTP_REMOTE_REPO_WITHOUT_DOT_GIT_SUFFIX,
    ),
)
def test_is_url_of_remote_repo_if_remote_url_then_true(repo: str):
    assert is_url_of_remote_repo(repo=repo) is True


@skip_for_windows_py_lt_3_9
@pytest.mark.parametrize(
    "repo",
    (
        tests.resources.SAMPLE_HTTP_REMOTE_REPO,
        tests.resources.SAMPLE_HTTP_REMOTE_REPO_WITHOUT_DOT_GIT_SUFFIX,
    ),
)
def test_git_clone_if_valid_remote_then_clone(repo: str):
    with TemporaryDirectory() as tmp_repo_dir:
        git_clone(repo=repo, dir=tmp_repo_dir)
        assert_dir_contain_git_repo(dir=tmp_repo_dir)


def test_git_push_tag_if_called_then_gitpython_corresponding_methods_are_correctly_invoked(
    with_mocked_repo_with_remote: tuple,
):
    (
        path,
        remote_name,
        MockedRepo,
        mocked_repo,
        mocked_remote,
    ) = with_mocked_repo_with_remote
    tag_name = "test_tag"

    git_push_tag(repo_path=path, tag_name=tag_name, remote_name=remote_name)

    MockedRepo.assert_called_once_with(path=path)
    mocked_repo.remote.assert_called_once_with(name=remote_name)
    mocked_remote.push.assert_called_once_with([tag_name])


def test_git_push_tag_if_called_with_delete_then_gitpython_corresponding_methods_are_correctly_invoked(
    with_mocked_repo_with_remote: tuple,
):
    (
        path,
        remote_name,
        MockedRepo,
        mocked_repo,
        mocked_remote,
    ) = with_mocked_repo_with_remote
    tag_name = "test_tag"

    git_push_tag(
        repo_path=path, tag_name=tag_name, delete=True, remote_name=remote_name
    )

    MockedRepo.assert_called_once_with(path=path)
    mocked_repo.remote.assert_called_once_with(name=remote_name)
    mocked_remote.push.assert_called_once_with(["--delete", tag_name])


def test_git_push_tag_if_error_then_exit_with_code_1(
    with_mocked_repo_with_remote: tuple,
):
    (
        path,
        remote_name,
        _,
        _,
        mocked_remote,
    ) = with_mocked_repo_with_remote
    mocked_remote.push.return_value = MagicMock()
    tag_name = "test_tag"

    with pytest.raises(GTOException) as error:
        git_push_tag(repo_path=path, tag_name=tag_name, remote_name=remote_name)

    assert f"git push {remote_name} {tag_name}" in error.value.msg
    assert (
        "Make sure your local repository is in sync with the remote" in error.value.msg
    )


def test_auto_push_on_remote_repo_if_not_remote_then_auto_push_is_not_changed(
    tmp_local_git_repo: str,
):
    assert decorated_write_func(spam=37, repo=tmp_local_git_repo, auto_push=True)[0]
    assert not decorated_write_func(spam=37, repo=tmp_local_git_repo, auto_push=False)[
        0
    ]


def test_auto_push_on_remote_repo_if_remote_then_auto_push_is_set_to_true():
    assert decorated_write_func(
        spam=37, repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, auto_push=True
    )[0]
    assert decorated_write_func(
        spam=37, repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, auto_push=False
    )[0]


def test_auto_push_on_remote_repo_if_not_remote_then_repo_is_not_cloned(
    tmp_local_git_repo,
):
    assert (
        decorated_write_func(spam=37, repo=tmp_local_git_repo, auto_push=True)[1]
        == tmp_local_git_repo
    )
    assert (
        decorated_write_func(spam=37, repo=tmp_local_git_repo, auto_push=False)[1]
        == tmp_local_git_repo
    )


def test_auto_push_on_remote_repo_if_remote_then_repo_is_cloned(tmp_local_git_repo):
    with patch("gto.git_utils.git_clone") as mocked_git_clone:
        mocked_git_clone.side_effect = git_clone
        local_repo = decorated_write_func(
            repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, spam=0, auto_push=False
        )[1]
        mocked_git_clone.assert_called_once_with(
            repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, dir=local_repo
        )


@auto_push_on_remote_repo
def decorated_write_func(
    spam: int, repo: Union[Repo, str], auto_push: bool
):  # pylint: disable=unused-argument
    return auto_push, repo


@git_clone_remote_repo
def decorated_read_func(
    spam: int, repo: Union[Repo, str], jam: int
):  # pylint: disable=unused-argument
    return repo


def assert_f_called_with_repo_return_repo_itself(repo: Union[str, Repo]) -> None:
    assert decorated_read_func(0, repo, 3) is repo
    assert decorated_read_func(0, repo, jam=3) is repo
    assert decorated_read_func(0, jam=3, repo=repo) is repo
    assert decorated_read_func(spam=0, jam=3, repo=repo) is repo


@pytest.fixture
def tmp_local_git_repo() -> str:
    tmp_repo_dir = TemporaryDirectory()  # pylint: disable=consider-using-with
    Repo.init(path=tmp_repo_dir.name)
    yield tmp_repo_dir.name
    tmp_repo_dir.cleanup()


def assert_dir_contain_git_repo(dir: str) -> None:
    assert (Path(dir) / ".git").is_dir()
    assert (Path(dir) / ".git/HEAD").is_file()


@pytest.fixture
def with_mocked_repo_with_remote() -> tuple:
    mocked_remote = MagicMock()
    mocked_remote.push.return_value = None
    mocked_repo = MagicMock()
    path = "git_repo_path"
    remote_name = "git_remote_name"

    with patch("gto.git_utils.Repo") as MockedRepo:
        MockedRepo.return_value = mocked_repo
        mocked_repo.remote.return_value = mocked_remote
        yield path, remote_name, MockedRepo, mocked_repo, mocked_remote
