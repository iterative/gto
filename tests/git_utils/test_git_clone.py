from pathlib import Path
from tempfile import TemporaryDirectory

from gto.git_utils import git_clone
from tests.git_utils.data import get_example_http_remote_repo
from tests.skip_presets import skip_for_windows_py_lt_3_9


@skip_for_windows_py_lt_3_9
def test_clone_remote_git_repo_in_specified_folder():
    with TemporaryDirectory() as tmp_repo_dir:
        git_clone(repo=get_example_http_remote_repo(), dir=tmp_repo_dir)
        assert_dir_contain_git_repo(dir=tmp_repo_dir)


def assert_dir_contain_git_repo(dir: str) -> None:
    assert (Path(dir) / ".git").is_dir()
    assert (Path(dir) / ".git/HEAD").is_file()
