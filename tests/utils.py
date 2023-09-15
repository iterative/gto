import json
from copy import deepcopy
from typing import Any, Dict, Sequence, Set, Union

from funcy import omit

from gto._pydantic import BaseModel


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
    skip_keys: Union[Set[str], Sequence[str]] = (),
):
    if isinstance(obj, BaseModel):
        obj_values = obj.dict(exclude=set(skip_keys))
    else:
        obj_values = omit(obj, skip_keys)
    values = omit(values, skip_keys)
    assert_equals(obj_values, values)


def convert_objects_to_str_in_json_serializable_object(
    o: Union[list, dict]
) -> Union[list, dict]:
    return json.loads(json.dumps(o, default=str))
