from typing import Callable, Tuple

import git
import pytest

from gto import CONFIG
from gto.index import (
    Artifact,
    RepoIndexManager,
    check_if_path_exists,
    find_repeated_path,
)


def init_index(path):
    # not correct, I believe, but tests pass
    with RepoIndexManager.from_repo(path) as index:
        return index


@pytest.fixture
def git_index_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo  # pylint: disable=unused-variable
    return init_index(repo.working_dir), repo


def test_git_index_add_virtual(git_index_repo):
    index, repo = git_index_repo
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

    new_index = init_index(repo.git_dir)
    assert isinstance(new_index, RepoIndexManager)
    index_value = new_index.get_index()
    assert index_value.state["nn"] == Artifact(path="pp", type="tt", virtual=True)

    repo.index.add(CONFIG.INDEX)
    commit = repo.index.commit("add index")

    assert new_index.get_history()[commit.hexsha].state == index_value.state


def test_git_index_remove_virtual(git_index_repo):
    index, repo = git_index_repo
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

    new_index = init_index(repo.git_dir)
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
def test_check_path_found(path, paths):
    assert find_repeated_path(path, paths) is not None


@pytest.mark.parametrize(
    "path, paths",
    [("models/m1.txt", ["models/m2.txt"]), ("models/a/m1.txt", ["models/m1.txt"])],
)
def test_check_path_not_found(path, paths):
    assert find_repeated_path(path, paths) is None


def test_check_existence_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo

    write_file("m1.txt", "some content")
    repo.index.add(["m1.txt"])
    repo.index.commit("commit config file")
    write_file("a/b", "some content")
    repo.index.add(["a/b"])
    repo.index.remove(["m1.txt"])
    repo.index.commit("commit a/b")

    assert check_if_path_exists("m1.txt", repo, "HEAD^1")
    assert not check_if_path_exists("m1.txt", repo, "HEAD")
    assert not check_if_path_exists("a/b", repo, "HEAD^1")
    assert check_if_path_exists("a/b", repo, "HEAD")


def test_check_existence_no_repo(tmp_path):
    with open(tmp_path / "m1.txt", "w", encoding="utf8") as f:
        f.write("some content")
    assert check_if_path_exists(tmp_path / "m1.txt")
    assert not check_if_path_exists(tmp_path / "not/exists")
