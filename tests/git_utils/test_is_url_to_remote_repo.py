import pytest

from gto.git_utils import is_url_to_remote_repo
from tests.git_utils.data.remote_repositories import get_all_examples


@pytest.mark.parametrize(
    "url, expected_result",
    zip(
        get_all_examples() + ["/local/path"], [True] * len(get_all_examples()) + [False]
    ),
)
def test_identify_valid_url_to_remote_git_repos(url: str, expected_result: bool):
    assert is_url_to_remote_repo(repo=url) == expected_result
