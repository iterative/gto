import pytest

from gto.api import show
from tests.api import data
from tests.skip_presets import (
    only_for_windows_py_lt_3_9,
    skip_for_windows_py_lt_3_9,
)


@skip_for_windows_py_lt_3_9
def test_if_show_on_remote_git_repo_then_return_expected_registry():
    result = show(repo=data.get_sample_remote_repo_url())
    assert result == data.get_sample_remote_repo_expected_registry()


@only_for_windows_py_lt_3_9
def test_if_repo_is_remote_url_and_windows_os_error_then_hint_win_with_py_lt_3_9_may_be_the_cause():
    with pytest.raises(Exception) as e:
        show(repo=data.get_sample_remote_repo_url())
    assert e.type in (NotADirectoryError, PermissionError)
    assert "windows" in str(e)
    assert "python" in str(e)
    assert "< 3.9" in str(e)
