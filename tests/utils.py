from typing import Any, Dict, Sequence, Set, Union

from funcy import omit
from pydantic import BaseModel


def _assert_equals(a, b):
    # separate function is helpful for debug
    # cause you see dicts without skip_keys
    assert a == b, f"\n{a} \n!=\n {b}"


def _check_obj(
    obj: BaseModel, values: Dict[str, Any], skip_keys: Union[Set[str], Sequence[str]]
):
    obj_values = obj.dict(exclude=set(skip_keys))
    _assert_equals(obj_values, values)
    # assert obj_values == values


def _check_dict(
    obj: Dict[str, Any],
    values: Dict[str, Any],
    skip_keys: Union[Set[str], Sequence[str]],
):
    obj_values = omit(obj, skip_keys)
    values = omit(values, skip_keys)
    _assert_equals(obj_values, values)
    # assert obj_values == values
