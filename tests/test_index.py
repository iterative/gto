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
    return RepoIndexManager.from_repo(path)


@pytest.fixture
def git_index_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo  # pylint: disable=unused-variable
    return init_index(repo.working_dir), repo


def test_git_index_add_virtual(git_index_repo):
    index, repo = git_index_repo
    index.add(
        "a",
        type="a",
        path="a",
        must_exist=False,
        labels=[],
        description="",
        update=False,
    )

    new_index = init_index(repo.git_dir)
    assert isinstance(new_index, RepoIndexManager)
    index_value = new_index.get_index()
    assert index_value.state["a"] == Artifact(path="a", type="a", virtual=True)

    repo.index.add(CONFIG.INDEX)
    commit = repo.index.commit("add index")

    assert new_index.get_history()[commit.hexsha].state == index_value.state


def test_git_index_remove_virtual(git_index_repo):
    index, repo = git_index_repo
    index.add("a", "a", "a", must_exist=False, labels=[], description="", update=True)

    new_index = init_index(repo.git_dir)
    assert isinstance(new_index, RepoIndexManager)

    new_index.remove("a")
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
