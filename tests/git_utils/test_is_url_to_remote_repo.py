import pytest

from gto.git_utils import is_url_of_remote_repo
from tests.git_utils import data


@pytest.mark.parametrize(
    "repo",
    (
        data.SAMPLE_HTTP_REMOTE_REPO,
        data.SAMPLE_HTTP_REMOTE_REPO_WITHOUT_DOT_GIT_SUFFIX,
    ),
)
def test_if_remote_url_then_true(repo: str):
    assert is_url_of_remote_repo(repo=repo) is True


@pytest.mark.parametrize(
    "repo",
    (
        "/local/path",
        "/local/path",
        ".",
    ),
)
def test_if_local_url_then_true(repo: str):
    assert is_url_of_remote_repo(repo=repo) is False
