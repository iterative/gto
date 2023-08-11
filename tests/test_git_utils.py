from unittest.mock import MagicMock

import pytest
from pytest_test_utils import TmpDir
from scmrepo.exceptions import SCMError
from scmrepo.git import Git, SyncStatus

from gto.exceptions import GTOException
from gto.git_utils import git_add_and_commit_all_changes, git_push_tag


@pytest.fixture(name="mocked_scm")
def _mocked_scm() -> MagicMock:
    return MagicMock(
        root_dir="git_repo_path",
        validate_git_remote=MagicMock(return_value=True),
    )


def test_git_push_tag(mocked_scm):
    tag_name = "test_tag"
    mocked_scm.push_refspecs = MagicMock(
        return_value={f"refs/tag/{tag_name}": SyncStatus.SUCCESS}
    )
    git_push_tag(mocked_scm, tag_name=tag_name)
    mocked_scm.push_refspecs.assert_called_once_with(
        "origin", "refs/tags/test_tag:refs/tags/test_tag"
    )


def test_git_push_tag_with_delete(mocked_scm):
    tag_name = "test_tag"
    mocked_scm.push_refspecs = MagicMock(
        return_value={f"refs/tag/{tag_name}": SyncStatus.SUCCESS}
    )
    git_push_tag(mocked_scm, tag_name=tag_name, delete=True)
    mocked_scm.push_refspecs.assert_called_once_with("origin", ":refs/tags/test_tag")


def test_git_push_tag_error(mocked_scm):
    mocked_scm.push_refspecs = MagicMock(side_effect=SCMError())
    tag_name = "test_tag"
    with pytest.raises(GTOException) as error:
        git_push_tag(mocked_scm, tag_name=tag_name)

    assert f"git push origin {tag_name}" in error.value.msg
    assert (
        "Make sure your local repository is in sync with the remote" in error.value.msg
    )


@pytest.mark.usefixtures("repo_with_commit")
def test_git_add_and_commit_all_changes_if_files_not_changed_then_no_new_commit(
    scm: Git,
):
    rev = scm.get_rev()
    git_add_and_commit_all_changes(
        scm=scm,
        message="test message",
    )
    assert scm.get_rev() == rev


@pytest.mark.usefixtures("repo_with_commit")
def test_git_add_and_commit_all_changes_if_tracked_file_is_changed_then_new_commit(
    tmp_dir: TmpDir,
    scm: Git,
):
    rev = scm.get_rev()
    tmp_dir.gen("some-tracked-file", "test data")
    git_add_and_commit_all_changes(
        scm,
        message="test message",
    )
    assert scm.get_rev() != rev
    fs = scm.get_fs("HEAD")
    with fs.open("some-tracked-file", "r", encoding="utf-8") as f:
        assert f.read() == "test data"


@pytest.mark.usefixtures("repo_with_commit")
def test_git_commit_specific_files_if_untracked_file_is_changed_then_new_commit(
    tmp_dir: TmpDir,
    scm: Git,
):
    rev = scm.get_rev()
    tmp_dir.gen("untracked-file", "test data")
    git_add_and_commit_all_changes(
        scm,
        message="test message",
    )
    assert scm.get_rev() != rev
    fs = scm.get_fs("HEAD")
    with fs.open("untracked-file", "r", encoding="utf-8") as f:
        assert f.read() == "test data"
