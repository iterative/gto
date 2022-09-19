import os
from copy import deepcopy
from typing import Any, Dict, Sequence, Set, Union

from funcy import omit
from pydantic import BaseModel


def show_difference(left: Dict, right: Dict):
    left_ = deepcopy(left)
    right_ = deepcopy(right)
    for key in list(left_.keys()):
        if left_.get(key) == right_.get(key):
            left_.pop(key)
            right_.pop(key)
    return f"\n{left_} \n!=\n {right_}"


def assert_equals(left, right):
    # separate function is helpful for debug
    # cause you see dicts without skip_keys
    assert left == right, show_difference(left, right)


def check_obj(
    obj: Union[BaseModel, Dict[str, Any]],
    values: Dict[str, Any],
    skip_keys: Union[Set[str], Sequence[str]],
):
    if isinstance(obj, BaseModel):
        obj_values = obj.dict(exclude=set(skip_keys))
    else:
        obj_values = omit(obj, skip_keys)
    values = omit(values, skip_keys)
    assert_equals(obj_values, values)


def is_os_windows_and_py_lt_3_9() -> bool:
    return (
        os.environ.get("GITHUB_MATRIX_OS") == "windows-latest"
        and os.environ.get("GITHUB_MATRIX_PYTHON", "2") < "3.9"
    )


def is_os_windows_and_py_lt_3_8() -> bool:
    return (
        os.environ.get("GITHUB_MATRIX_OS") == "windows-latest"
        and os.environ.get("GITHUB_MATRIX_PYTHON", "2") < "3.8"
    )
