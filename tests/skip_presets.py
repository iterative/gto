import os

import pytest

skip_for_windows_py_lt_3_9 = pytest.mark.skipif(
    os.environ.get("GITHUB_MATRIX_OS") == "windows-latest"
    and os.environ.get("GITHUB_MATRIX_PYTHON", "2") < "3.9",
    reason="functionality requires python features not working on windows with python<3.9",
)
