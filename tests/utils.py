from typing import Any, Dict, Sequence, Set, Union

from pydantic import BaseModel

# def _equals(a, b):
#     # separate function is helpful for debug
#     # cause you see dicts without skip_keys
#     assert a == b


def _check_obj(
    obj: BaseModel, values: Dict[str, Any], skip_keys: Union[Set[str], Sequence[str]]
):
    obj_values = obj.dict(exclude=set(skip_keys))
    assert obj_values == values


def _check_dict(
    obj: Dict[str, Any],
    values: Dict[str, Any],
    skip_keys: Union[Set[str], Sequence[str]],
):
    obj_values = {k: v for k, v in obj.items() if k not in skip_keys}
    values = {k: v for k, v in values.items() if k not in skip_keys}
    assert obj_values == values
