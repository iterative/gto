from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from gto.git_utils import git_clone
from tests.git_utils.data.remote_repositories import get_all_examples


@pytest.mark.parametrize("repo", get_all_examples())
def test_clone_remote_git_repo_in_specified_folder(repo: str):
    with TemporaryDirectory() as tmp_repo_dir:
        git_clone(repo=repo, dir=tmp_repo_dir)
        assert_dir_contain_git_repo(dir=tmp_repo_dir)


def assert_dir_contain_git_repo(dir: str) -> None:
    assert (Path(dir) / ".git").is_dir()
    assert (Path(dir) / ".git/HEAD").is_file()
