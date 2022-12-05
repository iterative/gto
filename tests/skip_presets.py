import pytest

from tests.utils import (
    is_os_windows,
    is_os_windows_and_py_lt_3_8,
    is_os_windows_and_py_lt_3_9,
)

skip_for_windows_py_lt_3_9 = pytest.mark.skipif(
    is_os_windows_and_py_lt_3_9(),
    reason="functionality requires python features not working on windows with python<3.9",
)

only_for_windows_py_lt_3_8 = pytest.mark.skipif(
    not is_os_windows_and_py_lt_3_8(),
    reason="test makes sense only for windows with python<3.9",
)

skip_for_windows = pytest.mark.skipif(
    is_os_windows(),
    reason="doesn't work on windows",
)
