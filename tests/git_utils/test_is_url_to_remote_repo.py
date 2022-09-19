import pytest

from gto.git_utils import is_url_to_remote_repo
from tests.git_utils.data import (
    get_example_http_remote_repo,
    get_example_http_remote_repo_without_dot_git_suffix,
)


@pytest.mark.parametrize(
    "repo",
    (
        get_example_http_remote_repo(),
        get_example_http_remote_repo_without_dot_git_suffix(),
    ),
)
def test_if_remote_url_then_true(repo: str):
    assert is_url_to_remote_repo(repo=repo) is True


def test_if_local_url_then_true():
    assert is_url_to_remote_repo(repo="/local/path") is False
