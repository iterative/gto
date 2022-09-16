from gto.git_utils import is_url_to_remote_repo
from tests.git_utils.data import get_example_http_remote_repo


def test_if_remote_url_then_true():
    assert is_url_to_remote_repo(repo=get_example_http_remote_repo()) is True


def test_if_local_url_then_true():
    assert is_url_to_remote_repo(repo="/local/path") is False
