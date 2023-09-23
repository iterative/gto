from typing import Sequence

import pytest
from pytest_mock import MockFixture
from pytest_test_utils import TmpDir
from scmrepo.git import Git

from gto import CONFIG
from gto.index import (
    Artifact,
    RepoIndexManager,
    check_if_path_exists,
    find_repeated_path,
)


@pytest.fixture(name="index")
def _index(empty_git_repo: str) -> RepoIndexManager:
    with RepoIndexManager.from_url(empty_git_repo) as index:
        yield index


def test_git_index_add_virtual(tmp_dir: TmpDir, scm: Git, index: RepoIndexManager):
    index.add(
        "nn",
        type="tt",
        path="pp",
        must_exist=False,
        allow_same_path=False,
        labels=[],
        description="",
        custom=None,
        update=False,
        commit=False,
        commit_message=None,
    )

    with RepoIndexManager.from_url(tmp_dir) as new_index:
        assert isinstance(new_index, RepoIndexManager)
        index_value = new_index.get_index()
        assert index_value.state["nn"] == Artifact(path="pp", type="tt", virtual=True)

        scm.add(CONFIG.INDEX)
        scm.commit("add index")
        rev = scm.get_rev()

        assert new_index.get_history()[rev].state == index_value.state


def test_git_index_remove_virtual(tmp_dir: TmpDir, index: RepoIndexManager):
    index.add(
        "aa",
        "aa",
        "aa",
        must_exist=False,
        allow_same_path=False,
        labels=[],
        description="",
        custom=None,
        update=True,
        commit=False,
        commit_message=None,
    )

    with RepoIndexManager.from_url(tmp_dir) as new_index:
        assert isinstance(new_index, RepoIndexManager)

        new_index.remove("aa")
        index_value = new_index.get_index()
        assert index_value.state == {}


@pytest.mark.parametrize(
    "path, paths",
    [
        ("models/m1.txt", ["models/m1.txt"]),
        ("models/m1.txt", ["models"]),
        ("models", ["models/m1.txt"]),
        ("models", ["models/"]),
        ("models/m1.txt/", ["models/m1.txt"]),
    ],
)
def test_check_path_found(path: str, paths: Sequence[str]):
    assert find_repeated_path(path, paths) is not None


@pytest.mark.parametrize(
    "path, paths",
    [("models/m1.txt", ["models/m2.txt"]), ("models/a/m1.txt", ["models/m1.txt"])],
)
def test_check_path_not_found(path: str, paths: Sequence[str]):
    assert find_repeated_path(path, paths) is None


def test_check_existence_repo(tmp_dir: TmpDir, scm: Git):
    tmp_dir.gen("m1.txt", "some content")
    scm.add(["m1.txt"])
    scm.commit("commit config file")
    tmp_dir.gen({"a": {"b": "some content"}})
    scm.add([str(tmp_dir / "a" / "b")])
    (tmp_dir / "m1.txt").unlink()
    scm.add(["m1.txt"])
    scm.commit("commit a/b")

    assert check_if_path_exists("m1.txt", scm, "HEAD^1")
    assert not check_if_path_exists("m1.txt", scm, "HEAD")
    assert not check_if_path_exists("a/b", scm, "HEAD^1")
    assert check_if_path_exists("a/b", scm, "HEAD")


def test_check_existence_no_repo(tmp_dir: TmpDir):
    tmp_dir.gen("m1.txt", "some content")
    assert check_if_path_exists(tmp_dir / "m1.txt")
    assert not check_if_path_exists(tmp_dir / "not" / "exists")


def test_from_url_sets_cloned_property(tmp_dir: TmpDir, scm: Git, mocker: MockFixture):
    with RepoIndexManager.from_url(tmp_dir) as idx:
        assert idx.cloned is False

    with RepoIndexManager.from_url(scm) as idx:
        assert idx.cloned is False

    cloned_git_repo_mock = mocker.patch("gto.git_utils.cloned_git_repo")
    cloned_git_repo_mock.return_value.__enter__.return_value = scm

    with RepoIndexManager.from_url("https://github.com/iterative/gto") as idx:
        assert idx.cloned is True
