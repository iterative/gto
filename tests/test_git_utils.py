from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pytest
from git import Repo

from gto.git_utils import convert_to_git_repo, git_clone
from tests.data.remote_repositories import get_example_http_remote_repo, get_example_ssh_remote_repo


def test_convert_to_git_repo__return_input_itself_if_provided_with_a_git_repo():
    repo = MagicMock()
    repo.__class__ = Repo

    assert convert_to_git_repo(repo=repo) is repo


def test_convert_to_git_repo__return_repo_object_from_string_with_path_to_local_git_repo(create_tmp_local_git_repo):
    assert isinstance(convert_to_git_repo(repo=create_tmp_local_git_repo), Repo)


@pytest.mark.parametrize("repo", [get_example_http_remote_repo(), get_example_ssh_remote_repo()])
def test_convert_to_git_repo__clone_remote_git_repo_and_convert_from_url(repo):
    assert isinstance(convert_to_git_repo(repo=repo), Repo)

    from gto.git_utils import tmp_repo_dir
    tmp_repo_dir.cleanup()


@pytest.mark.parametrize("repo", [get_example_http_remote_repo(), get_example_ssh_remote_repo()])
def test_git_clone__clone_remote_git_repo_in_specified_folder(repo: str):
    with TemporaryDirectory() as tmp_repo_dir:
        git_clone(repo=get_example_http_remote_repo(), dir=tmp_repo_dir)
        assert_dir_contain_git_repo(dir=tmp_repo_dir)


@pytest.fixture
def create_tmp_local_git_repo() -> Repo:
    tmp_repo_dir = TemporaryDirectory()
    Repo.init(path=tmp_repo_dir.name)
    yield tmp_repo_dir.name
    tmp_repo_dir.cleanup()


def assert_dir_contain_git_repo(dir: str) -> None:
    assert (Path(dir) / ".git").is_dir()
    assert (Path(dir) / ".git/HEAD").is_file()
