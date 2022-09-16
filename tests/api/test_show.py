from gto.api import show
from tests.api import data


def test_show_on_remote_git_repo():
    result = show(repo=data.get_sample_remote_repo_url())
    assert result == data.get_sample_remote_repo_expected_registry()
