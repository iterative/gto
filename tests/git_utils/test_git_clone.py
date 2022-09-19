from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from gto.git_utils import git_clone
from tests.git_utils.data import (
    get_example_http_remote_repo,
    get_example_http_remote_repo_without_dot_git_suffix,
)
from tests.skip_presets import skip_for_windows_py_lt_3_9


@skip_for_windows_py_lt_3_9
@pytest.mark.parametrize(
    "repo",
    (
        get_example_http_remote_repo(),
        get_example_http_remote_repo_without_dot_git_suffix(),
    ),
)
def test_clone_remote_git_repo_in_specified_folder(repo: str):
    with TemporaryDirectory() as tmp_repo_dir:
        git_clone(repo=repo, dir=tmp_repo_dir)
        assert_dir_contain_git_repo(dir=tmp_repo_dir)


def assert_dir_contain_git_repo(dir: str) -> None:
    assert (Path(dir) / ".git").is_dir()
    assert (Path(dir) / ".git/HEAD").is_file()
