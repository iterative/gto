from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Tuple, Union
from unittest.mock import MagicMock, call, patch

import pytest
from git import Repo

import tests.resources
from gto.exceptions import GTOException
from gto.git_utils import (
    clone_on_remote_repo,
    commit_produced_changes_on_commit,
    git_add_and_commit_all_changes,
    git_clone,
    git_push,
    git_push_tag,
    is_url_of_remote_repo,
    push_on_push,
    set_push_on_remote_repo,
    stashed_changes,
)
from tests.skip_presets import (
    only_for_windows_py_lt_3_8,
    skip_for_windows_py_lt_3_9,
)


def test_clone_on_remote_repo_if_repo_is_a_meaningless_string_then_leave_it_unchanged():
    assert_f_called_with_repo_return_repo_itself(repo="meaningless_string")


def test_clone_on_remote_repo_if_repo_is_a_local_git_repo_then_leave_it_unchanged(
    tmp_local_empty_git_repo,
):
    assert_f_called_with_repo_return_repo_itself(repo=tmp_local_empty_git_repo)


def test_clone_on_remote_repo_if_repo_gitpython_object_then_leave_it_unchanged(
    tmp_local_empty_git_repo,
):
    assert_f_called_with_repo_return_repo_itself(
        repo=Repo(path=tmp_local_empty_git_repo)
    )


@skip_for_windows_py_lt_3_9
def test_clone_on_remote_repo_if_repo_is_remote_url_then_clone_and_set_repo_to_its_local_path():
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
    mocked_remote.push.return_value.error = MagicMock()
    tag_name = "test_tag"

    with pytest.raises(GTOException) as error:
        git_push_tag(repo_path=path, tag_name=tag_name, remote_name=remote_name)

    assert f"git push {remote_name} {tag_name}" in error.value.msg
    assert (
        "Make sure your local repository is in sync with the remote" in error.value.msg
    )


def test_set_auto_push_on_remote_repo_if_not_remote_then_auto_push_is_not_changed(
    tmp_local_empty_git_repo,
):
    assert decorated_write_func(spam=37, repo=tmp_local_empty_git_repo, push=True)[0]
    assert not decorated_write_func(spam=37, repo=tmp_local_empty_git_repo, push=False)[
        0
    ]


@skip_for_windows_py_lt_3_9
def test_set_auto_push_on_remote_repo_if_remote_then_auto_push_is_set_to_true():
    assert decorated_write_func(
        spam=37, repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, push=True
    )[0]
    assert decorated_write_func(
        spam=37, repo=tests.resources.SAMPLE_HTTP_REMOTE_REPO, push=False
    )[0]


@skip_for_windows_py_lt_3_9
def test_git_add_and_commit_all_changes_if_files_not_changed_then_no_new_commit(
    tmp_local_git_repo_with_first_test_commit,
):
    git_add_and_commit_all_changes(
        repo_path=tmp_local_git_repo_with_first_test_commit[0],
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
        repo_path=tmp_local_git_repo_with_first_test_commit[0],
        message=SECOND_TEST_COMMIT_MESSAGE,
    )

    assert_repo_as_expected_after_second_test_commit(
        repo_path=tmp_local_git_repo_with_first_test_commit[0],
        second_commit_on_untracked_file=False,
    )


def test_git_commit_specific_files_if_untracked_file_is_changed_then_new_commit(
    tmp_local_git_repo_with_first_test_commit,
):
    untracked_file = (
        Path(tmp_local_git_repo_with_first_test_commit[0]) / TEST_COMMIT_UNTRACKED_FILE
    )
    with open(untracked_file, "w", encoding="utf") as f:
        f.write(SECOND_TEST_FILE_MODIFICATION)

    git_add_and_commit_all_changes(
        repo_path=tmp_local_git_repo_with_first_test_commit[0],
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
        with stashed_changes(repo_path=tmp_local_empty_git_repo):
            pass


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_tracked_file_was_changed_then_inside_with_statement_is_rolled_back(
    tmp_local_git_repo_with_first_test_commit,
):
    tracked_file, _ = change_tracked_file(
        repo_path=tmp_local_git_repo_with_first_test_commit[0]
    )

    with stashed_changes(repo_path=tmp_local_git_repo_with_first_test_commit[0]):
        with open(tracked_file, "r", encoding="utf") as f:
            assert f.read() == FIRST_TEST_FILE_MODIFICATION


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_tracked_file_was_changed_then_outside_with_statement_is_as_before(
    tmp_local_git_repo_with_first_test_commit,
):
    tracked_file, new_file_content = change_tracked_file(
        repo_path=tmp_local_git_repo_with_first_test_commit[0]
    )

    with stashed_changes(repo_path=tmp_local_git_repo_with_first_test_commit[0]):
        pass

    with open(tracked_file, "r", encoding="utf") as f:
        assert f.read() == new_file_content


@skip_for_windows_py_lt_3_9
def test_stashed_changes_if_tracked_file_was_changed_then_return_its_path(
    tmp_local_git_repo_with_first_test_commit,
):
    repo_path = tmp_local_git_repo_with_first_test_commit[0]
    tracked_file, _ = change_tracked_file(repo_path=repo_path)

    with stashed_changes(repo_path=repo_path) as (
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
        repo_path=tmp_local_git_repo_with_first_test_commit[0], include_untracked=False
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
        repo_path=tmp_local_git_repo_with_first_test_commit[0], include_untracked=True
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
        repo_path=tmp_local_git_repo_with_first_test_commit[0], include_untracked=True
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

    with stashed_changes(repo_path=repo_path, include_untracked=True) as (
        tracked,
        untracked,
    ):
        assert len(tracked) == 0
        assert untracked == [untracked_file.relative_to(repo_path).as_posix()]


def test_commit_produced_changes_on_auto_commit_if_no_auto_commit_argument_then_don_t_stash_or_commit(
    mocked_f_decorated_with_commit_produced_changes_on_auto_commit,
):
    (
        f,
        f_spy,
        mocked_stashed_changes,
        mocked_git_add_and_commit_all_changes,
        _,
        _,
    ) = mocked_f_decorated_with_commit_produced_changes_on_auto_commit

    result = f()

    mocked_stashed_changes.assert_not_called()
    mocked_git_add_and_commit_all_changes.assert_not_called()
    f_spy.assert_called_once_with()
    assert result == f_spy.return_value


def test_commit_produced_changes_on_auto_commit_if_auto_commit_is_false_then_don_t_stash_or_commit(
    mocked_f_decorated_with_commit_produced_changes_on_auto_commit,
):
    (
        f,
        f_spy,
        mocked_stashed_changes,
        mocked_git_add_and_commit_all_changes,
        _,
        _,
    ) = mocked_f_decorated_with_commit_produced_changes_on_auto_commit

    result = f(commit=False)

    mocked_stashed_changes.assert_not_called()
    mocked_git_add_and_commit_all_changes.assert_not_called()
    f_spy.assert_called_once_with(commit=False)
    assert result == f_spy.return_value


def test_commit_produced_changes_on_auto_commit_if_auto_commit_but_no_repo_then_exception_and_don_t_stash_or_commit(
    mocked_f_decorated_with_commit_produced_changes_on_auto_commit,
):
    (
        f,
        f_spy,
        mocked_stashed_changes,
        mocked_git_add_and_commit_all_changes,
        _,
        _,
    ) = mocked_f_decorated_with_commit_produced_changes_on_auto_commit

    with pytest.raises(ValueError):
        f(commit=True)

    mocked_stashed_changes.assert_not_called()
    mocked_git_add_and_commit_all_changes.assert_not_called()
    f_spy.assert_not_called()


def test_commit_produced_changes_on_auto_commit_if_auto_commit_is_true_then_stash_and_commit_in_repo(
    mocked_f_decorated_with_commit_produced_changes_on_auto_commit,
):
    (
        f,
        f_spy,
        _,
        _,
        mock_manager,
        generate_test_commit_message,
    ) = mocked_f_decorated_with_commit_produced_changes_on_auto_commit
    repo_path = "a/repo/path"

    result = f(repo=repo_path, commit=True)

    expected_calls = [
        call.stashed_changes(repo_path=repo_path, include_untracked=True),
        call.stashed_changes().__enter__(),
        call.spy(repo=repo_path, commit=True),
        call.git_add_and_commit_all_changes(
            repo_path=repo_path, message=generate_test_commit_message(commit=True)
        ),
        call.stashed_changes().__exit__(None, None, None),
    ]

    assert mock_manager.mock_calls == expected_calls
    assert result == f_spy.return_value


@skip_for_windows_py_lt_3_9
def test_commit_produced_changes_on_auto_commit_if_f_changes_tracked_file_already_dangling_then_raise_exception_and_roll_back(
    tmp_local_git_repo_with_first_test_commit,
):
    repo, tracked_file = tmp_local_git_repo_with_first_test_commit

    with open(tracked_file, "a", encoding="utf") as f:
        f.write(f" - {SECOND_TEST_FILE_MODIFICATION}")

    @commit_produced_changes_on_commit()
    def f_to_test(repo: str, commit: bool):  # pylint: disable=unused-argument
        with open(tracked_file, "a", encoding="utf") as f:
            f.write(" - change made by f")

    with pytest.raises(GTOException):
        f_to_test(repo=repo, commit=True)

    with open(tracked_file, "r", encoding="utf") as f:
        assert (
            f.read()
            == f"{FIRST_TEST_FILE_MODIFICATION} - {SECOND_TEST_FILE_MODIFICATION}"
        )


@skip_for_windows_py_lt_3_9
def test_commit_produced_changes_on_auto_commit_if_f_changes_untracked_file_already_dangling_then_raise_exception_and_roll_back(
    tmp_local_git_repo_with_first_test_commit,
):
    repo, _ = tmp_local_git_repo_with_first_test_commit
    untracked_file = (Path(repo) / TEST_COMMIT_UNTRACKED_FILE).as_posix()

    with open(untracked_file, "w", encoding="utf") as f:
        f.write(f"{FIRST_TEST_FILE_MODIFICATION}")

    @commit_produced_changes_on_commit()
    def f_to_test(repo: str, commit: bool):  # pylint: disable=unused-argument
        with open(untracked_file, "a", encoding="utf") as f:
            f.write(" - change made by f")

    with pytest.raises(GTOException):
        f_to_test(repo=repo, commit=True)

    with open(untracked_file, "r", encoding="utf") as f:
        assert f.read() == f"{FIRST_TEST_FILE_MODIFICATION}"


@skip_for_windows_py_lt_3_9
def test_git_push_if_called_then_corresponding_gitpython_functions_are_called(
    tmp_local_empty_git_repo,
):
    with patch("gto.git_utils.git.Repo") as MockedRepo:
        git_push(repo_path=tmp_local_empty_git_repo)

    MockedRepo.assert_called_once_with(path=tmp_local_empty_git_repo)
    MockedRepo.return_value.git.push.assert_called_once_with()


def test_push_on_auto_push_if_auto_push_and_repo_not_provided_then_raise_exception(
    mocked_f_decorated_with_push_on_auto_push,
):
    f, _, _, _, _ = mocked_f_decorated_with_push_on_auto_push

    with pytest.raises(ValueError):
        f(push=True)


def test_push_on_auto_push_if_auto_push_then_set_auto_commit_to_true(
    mocked_f_decorated_with_push_on_auto_push,
):
    f, f_spy, repo_path, _, _ = mocked_f_decorated_with_push_on_auto_push

    result = f(repo=repo_path, commit=False, push=True)

    f_spy.assert_called_once_with(repo=repo_path, commit=True, push=True)
    assert result == f_spy.return_value


def test_push_on_auto_push_if_auto_push_false_then_git_push_is_not_called(
    mocked_f_decorated_with_push_on_auto_push,
):
    f, f_spy, _, _, mock_manager = mocked_f_decorated_with_push_on_auto_push

    result = f(push=False)

    expected_calls = [
        call.spy(push=False),
    ]
    assert mock_manager.mock_calls == expected_calls
    assert result == f_spy.return_value


def test_push_on_auto_push_if_auto_push_true_then_git_push_is_called_after_f(
    mocked_f_decorated_with_push_on_auto_push,
):
    f, f_spy, repo_path, _, mock_manager = mocked_f_decorated_with_push_on_auto_push

    result = f(repo=repo_path, push=True)

    expected_calls = [
        call.spy(repo=repo_path, commit=True, push=True),
        call.git_push(
            repo_path=repo_path,
        ),
    ]
    assert mock_manager.mock_calls == expected_calls
    assert result == f_spy.return_value


def test_push_on_auto_push_if_git_pull_fails_then_raise_gto_exception(
    mocked_f_decorated_with_push_on_auto_push,
):
    (
        f,
        _,
        repo_path,
        mocked_git_push,
        _,
    ) = mocked_f_decorated_with_push_on_auto_push
    git_push_error_message = "This was the mistake..."
    mocked_git_push.side_effect = Exception(git_push_error_message)

    with pytest.raises(GTOException) as e:
        f(repo=repo_path, push=True)

    assert "It was not possible to run `git push`" in e.value.msg
    assert git_push_error_message in e.value.msg


@set_push_on_remote_repo
def decorated_write_func(
    spam: int, repo: Union[Repo, str], push: bool
):  # pylint: disable=unused-argument
    return push, repo


@clone_on_remote_repo
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


@pytest.fixture
def mocked_f_decorated_with_commit_produced_changes_on_auto_commit() -> Tuple[
    Callable, MagicMock, MagicMock, MagicMock, MagicMock, Callable
]:
    f_spy = MagicMock()
    f_spy.return_value = MagicMock()

    def generate_test_commit_message(commit: bool) -> str:
        return f"commit message with argument {commit}"

    @commit_produced_changes_on_commit(message_generator=generate_test_commit_message)
    def f(*args, **kwargs):
        return f_spy(*args, **kwargs)

    with patch("gto.git_utils.stashed_changes") as mocked_stashed_changes:
        mocked_stashed_changes.return_value.__enter__.return_value = [], []
        with patch(
            "gto.git_utils._get_repo_changed_tracked_and_untracked_files"
        ) as mocked_get_repo_changed_tracked_and_untracked_files:
            mocked_get_repo_changed_tracked_and_untracked_files.return_value = [
                TEST_COMMIT_FILE
            ], []
            with patch(
                "gto.git_utils.git_add_and_commit_all_changes"
            ) as mocked_git_add_and_commit_all_changes:
                mock_manager = MagicMock()
                mock_manager.attach_mock(mocked_stashed_changes, "stashed_changes")
                mock_manager.attach_mock(f_spy, "spy")
                mock_manager.attach_mock(
                    mocked_git_add_and_commit_all_changes,
                    "git_add_and_commit_all_changes",
                )

                yield f, f_spy, mocked_stashed_changes, mocked_git_add_and_commit_all_changes, mock_manager, generate_test_commit_message


@pytest.fixture
def mocked_f_decorated_with_push_on_auto_push() -> Tuple[
    Callable, MagicMock, str, MagicMock, MagicMock
]:
    repo_path = "my/repo"
    f_spy = MagicMock()

    @push_on_push
    def f(*args, **kwargs):
        return f_spy(*args, **kwargs)

    with patch("gto.git_utils.git_push") as mocked_git_push:
        mock_manager = MagicMock()
        mock_manager.attach_mock(f_spy, "spy")
        mock_manager.attach_mock(mocked_git_push, "git_push")

        yield f, f_spy, repo_path, mocked_git_push, mock_manager


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
