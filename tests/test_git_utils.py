from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Tuple
from unittest.mock import MagicMock, patch

import pytest
from git import Repo

import tests.resources
from gto.exceptions import GTOException
from gto.git_utils import (
    git_add_and_commit_all_changes,
    git_clone,
    git_push,
    git_push_tag,
    is_url_of_remote_repo,
    stashed_changes,
)
from tests.skip_presets import skip_for_windows_py_lt_3_9


@pytest.mark.parametrize(
    "repo_path",
    (
        "/local/path",
        "/local/path",
        ".",
    ),
)
def test_is_url_of_remote_repo_if_local_url_then_true(repo_path: str):
    assert is_url_of_remote_repo(repo_path=repo_path) is False


@pytest.mark.parametrize(
    "repo_path",
    (
        tests.resources.SAMPLE_HTTP_REMOTE_REPO,
        tests.resources.SAMPLE_HTTP_REMOTE_REPO_WITHOUT_DOT_GIT_SUFFIX,
    ),
)
def test_is_url_of_remote_repo_if_remote_url_then_true(repo_path: str):
    assert is_url_of_remote_repo(repo_path=repo_path) is True


@skip_for_windows_py_lt_3_9
@pytest.mark.parametrize(
    "repo_path",
    (
        tests.resources.SAMPLE_HTTP_REMOTE_REPO,
        tests.resources.SAMPLE_HTTP_REMOTE_REPO_WITHOUT_DOT_GIT_SUFFIX,
    ),
)
def test_git_clone_if_valid_remote_then_clone(repo_path: str):
    with TemporaryDirectory() as tmp_repo_dir:
        git_clone(repo=repo_path, dir=tmp_repo_dir)
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

    git_push_tag(repo=path, tag_name=tag_name, remote_name=remote_name)

    MockedRepo.assert_called_once_with(path, search_parent_directories=False)
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

    git_push_tag(repo=path, tag_name=tag_name, delete=True, remote_name=remote_name)

    MockedRepo.assert_called_once_with(path, search_parent_directories=False)
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
    mocked_remote.push.return_value.error = MagicMock()
    tag_name = "test_tag"

    with pytest.raises(GTOException) as error:
        git_push_tag(repo=path, tag_name=tag_name, remote_name=remote_name)

    assert f"git push {remote_name} {tag_name}" in error.value.msg
    assert (
        "Make sure your local repository is in sync with the remote" in error.value.msg
    )


@skip_for_windows_py_lt_3_9
def test_git_add_and_commit_all_changes_if_files_not_changed_then_no_new_commit(
    tmp_local_git_repo_with_first_test_commit,
):
    git_add_and_commit_all_changes(
        repo=tmp_local_git_repo_with_first_test_commit[0],
        message=SECOND_TEST_COMMIT_MESSAGE,
    )
    assert_repo_as_expected_after_first_test_commit(
        repo_path=tmp_local_git_repo_with_first_test_commit[0]
    )


@skip_for_windows_py_lt_3_9
def test_git_add_and_commit_all_changes_if_tracked_file_is_changed_then_new_commit(
    tmp_local_git_repo_with_first_test_commit,
):
    with open(tmp_local_git_repo_with_first_test_commit[1], "a", encoding="utf") as f:
        f.write(SECOND_TEST_FILE_MODIFICATION)

    git_add_and_commit_all_changes(
        repo=tmp_local_git_repo_with_first_test_commit[0],
        message=SECOND_TEST_COMMIT_MESSAGE,
    )

    assert_repo_as_expected_after_second_test_commit(
        repo_path=tmp_local_git_repo_with_first_test_commit[0],
        second_commit_on_untracked_file=False,
    )


@skip_for_windows_py_lt_3_9
def test_git_commit_specific_files_if_untracked_file_is_changed_then_new_commit(
    tmp_local_git_repo_with_first_test_commit,
):
    untracked_file = (
        Path(tmp_local_git_repo_with_first_test_commit[0]) / TEST_COMMIT_UNTRACKED_FILE
    )
    with open(untracked_file, "w", encoding="utf") as f:
        f.write(SECOND_TEST_FILE_MODIFICATION)

    git_add_and_commit_all_changes(
        repo=tmp_local_git_repo_with_first_test_commit[0],
        message=SECOND_TEST_COMMIT_MESSAGE,
    )

    assert_repo_as_expected_after_second_test_commit(
        repo_path=tmp_local_git_repo_with_first_test_commit[0],
        second_commit_on_untracked_file=True,
    )


def test_stashed_changes_if_repo_has_no_ref_then_raise_exception(
    tmp_local_empty_git_repo,
):
    with pytest.raises(RuntimeError):
        with stashed_changes(repo=tmp_local_empty_git_repo):
            pass


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_tracked_file_was_changed_then_inside_with_statement_is_rolled_back(
    tmp_local_git_repo_with_first_test_commit,
):
    tracked_file, _ = change_tracked_file(
        repo_path=tmp_local_git_repo_with_first_test_commit[0]
    )

    with stashed_changes(repo=tmp_local_git_repo_with_first_test_commit[0]):
        with open(tracked_file, "r", encoding="utf") as f:
            assert f.read() == FIRST_TEST_FILE_MODIFICATION


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_tracked_file_was_changed_then_outside_with_statement_is_as_before(
    tmp_local_git_repo_with_first_test_commit,
):
    tracked_file, new_file_content = change_tracked_file(
        repo_path=tmp_local_git_repo_with_first_test_commit[0]
    )

    with stashed_changes(repo=tmp_local_git_repo_with_first_test_commit[0]):
        pass

    with open(tracked_file, "r", encoding="utf") as f:
        assert f.read() == new_file_content


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_tracked_file_was_changed_then_return_its_path(
    tmp_local_git_repo_with_first_test_commit,
):
    repo_path = tmp_local_git_repo_with_first_test_commit[0]
    tracked_file, _ = change_tracked_file(repo_path=repo_path)

    with stashed_changes(repo=repo_path) as (
        tracked,
        untracked,
    ):
        assert tracked == [tracked_file.relative_to(repo_path).as_posix()]
        assert len(untracked) == 0


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_untracked_file_was_changed_but_include_untracked_is_false_then_do_not_roll_back(
    tmp_local_git_repo_with_first_test_commit,
):
    untracked_file, _ = change_untracked_file(
        repo_path=tmp_local_git_repo_with_first_test_commit[0]
    )

    with stashed_changes(
        repo=tmp_local_git_repo_with_first_test_commit[0], include_untracked=False
    ):
        assert untracked_file.is_file()


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_untracked_file_was_changed_then_inside_with_statement_is_rolled_back(
    tmp_local_git_repo_with_first_test_commit,
):
    untracked_file, _ = change_untracked_file(
        repo_path=tmp_local_git_repo_with_first_test_commit[0]
    )

    with stashed_changes(
        repo=tmp_local_git_repo_with_first_test_commit[0], include_untracked=True
    ):
        assert not untracked_file.is_file()


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_untracked_file_was_changed_then_outside_with_statement_is_as_before(
    tmp_local_git_repo_with_first_test_commit,
):
    untracked_file, new_file_content = change_untracked_file(
        repo_path=tmp_local_git_repo_with_first_test_commit[0]
    )

    with stashed_changes(
        repo=tmp_local_git_repo_with_first_test_commit[0], include_untracked=True
    ):
        pass

    with open(untracked_file, "r", encoding="utf") as f:
        assert f.read() == new_file_content


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_untracked_file_was_changed_then_return_its_path(
    tmp_local_git_repo_with_first_test_commit,
):
    repo_path = tmp_local_git_repo_with_first_test_commit[0]
    untracked_file, _ = change_untracked_file(repo_path=repo_path)

    with stashed_changes(repo=repo_path, include_untracked=True) as (
        tracked,
        untracked,
    ):
        assert len(tracked) == 0
        assert untracked == [untracked_file.relative_to(repo_path).as_posix()]


@skip_for_windows_py_lt_3_9
def test_git_push_if_called_then_corresponding_gitpython_functions_are_called(
    tmp_local_empty_git_repo,
):
    with patch("gto.git_utils.git.Repo") as MockedRepo:
        git_push(repo=tmp_local_empty_git_repo)

    MockedRepo.assert_called_once_with(
        tmp_local_empty_git_repo, search_parent_directories=False
    )
    MockedRepo.return_value.git.push.assert_called_once_with()


@pytest.fixture
def tmp_local_empty_git_repo() -> str:
    tmp_repo_dir = TemporaryDirectory()  # pylint: disable=consider-using-with
    Repo.init(path=tmp_repo_dir.name)
    yield tmp_repo_dir.name
    tmp_repo_dir.cleanup()


@pytest.fixture
def tmp_local_git_repo_with_first_test_commit(tmp_local_empty_git_repo) -> str:
    new_file_path = Path(tmp_local_empty_git_repo) / TEST_COMMIT_FILE
    repo = Repo(path=tmp_local_empty_git_repo)
    with open(new_file_path, "w", encoding="utf") as test_file:
        test_file.write(FIRST_TEST_FILE_MODIFICATION)
    with open(
        Path(tmp_local_empty_git_repo) / "README.md", "w", encoding="utf"
    ) as readme:
        readme.write("Read me")
    repo.index.add(items=[test_file.name, readme.name])
    repo.index.commit(message=FIRST_TEST_COMMIT_MESSAGE)
    yield tmp_local_empty_git_repo, new_file_path.as_posix()


def change_tracked_file(repo_path: str) -> Tuple[Path, str]:
    tracked_file = Path(repo_path) / TEST_COMMIT_FILE
    new_file_content = "Same changes"
    with open(tracked_file, "w", encoding="utf") as f:
        f.write(new_file_content)
    return tracked_file, new_file_content


def change_untracked_file(
    repo_path: str,
) -> Tuple[Path, str]:
    untracked_file = Path(repo_path) / TEST_COMMIT_UNTRACKED_FILE
    new_file_content = "Same changes to an untracked file"
    with open(untracked_file, "w", encoding="utf") as f:
        f.write(new_file_content)
    return untracked_file, new_file_content


def assert_dir_contain_git_repo(dir: str) -> None:
    assert (Path(dir) / ".git").is_dir()
    assert (Path(dir) / ".git/HEAD").is_file()


@pytest.fixture
def with_mocked_repo_with_remote() -> tuple:
    mocked_remote = MagicMock()
    mocked_push_info = MagicMock()
    mocked_push_info.error = None
    mocked_remote.push.return_value = mocked_push_info
    mocked_repo = MagicMock()
    path = "git_repo_path"
    remote_name = "git_remote_name"

    with patch("gto.git_utils.git.Repo") as MockedRepo:
        MockedRepo.return_value = mocked_repo
        mocked_repo.remote.return_value = mocked_remote
        yield path, remote_name, MockedRepo, mocked_repo, mocked_remote


def assert_repo_without_commit(repo_path: str) -> None:
    with pytest.raises(ValueError) as e:
        Repo(path=repo_path).iter_commits()
    assert "Reference at 'refs/heads/master' does not exist" in str(e)


def assert_repo_as_expected_after_first_test_commit(repo_path: str) -> None:
    assert (
        list(Repo(path=repo_path).iter_commits())[0].message
        == FIRST_TEST_COMMIT_MESSAGE
    )
    assert_test_commit_file_content(
        repo_path=repo_path,
        file_name=TEST_COMMIT_FILE,
        expected_content=FIRST_TEST_FILE_MODIFICATION,
    )


def assert_repo_as_expected_after_second_test_commit(
    repo_path: str, second_commit_on_untracked_file: bool
) -> None:
    assert [c.message for c in Repo(path=repo_path).iter_commits()] == [
        SECOND_TEST_COMMIT_MESSAGE,
        FIRST_TEST_COMMIT_MESSAGE,
    ]
    if second_commit_on_untracked_file:
        assert_test_commit_file_content(
            repo_path=repo_path,
            file_name=TEST_COMMIT_FILE,
            expected_content=FIRST_TEST_FILE_MODIFICATION,
        )
        assert_test_commit_file_content(
            repo_path=repo_path,
            file_name=TEST_COMMIT_UNTRACKED_FILE,
            expected_content=SECOND_TEST_FILE_MODIFICATION,
        )
    else:
        assert_test_commit_file_content(
            repo_path=repo_path,
            file_name=TEST_COMMIT_FILE,
            expected_content=FIRST_TEST_FILE_MODIFICATION
            + SECOND_TEST_FILE_MODIFICATION,
        )


def assert_test_commit_file_content(
    repo_path: str, file_name: str, expected_content: str
) -> None:
    with TemporaryDirectory() as td:
        Repo.clone_from(url=repo_path, to_path=td)
        with open(Path(td) / file_name, "r", encoding="utf") as f:
            assert f.read() == expected_content


TEST_COMMIT_FILE = "foo.txt"
TEST_COMMIT_UNTRACKED_FILE = "untracked_foo.txt"
FIRST_TEST_FILE_MODIFICATION = "First file modification"
SECOND_TEST_FILE_MODIFICATION = "Second file modification"
FIRST_TEST_COMMIT_MESSAGE = "first test commit"
SECOND_TEST_COMMIT_MESSAGE = "second test commit"
