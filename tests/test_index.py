import pytest

from gto import CONFIG
from gto.index import Artifact, RepoIndexManager, find_nested_path


def init_index(path):
    return RepoIndexManager.from_repo(path)


@pytest.fixture
def git_index_repo(empty_git_repo):
    return init_index(empty_git_repo.working_dir), empty_git_repo


def test_git_index_add(git_index_repo):
    index, repo = git_index_repo
    index.add("a", "a", "a")

    new_index = init_index(repo.git_dir)
    assert isinstance(new_index, RepoIndexManager)
    index_value = new_index.get_index()
    assert index_value.state["a"] == Artifact(name="a", path="a", type="a")

    repo.index.add(CONFIG.INDEX)
    commit = repo.index.commit("add index")

    assert new_index.get_history()[commit.hexsha].state == index_value.state


def test_git_index_remove(git_index_repo):
    index, repo = git_index_repo
    index.add("a", "a", "a")

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
    assert find_nested_path(path, paths) is not None


@pytest.mark.parametrize(
    "path, paths",
    [("models/m1.txt", ["models/m2.txt"]), ("models/a/m1.txt", ["models/m1.txt"])],
)
def test_check_path_not_found(path, paths):
    assert find_nested_path(path, paths) is None
