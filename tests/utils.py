from typing import Any, Dict, Set

from pydantic import BaseModel


def _check_dict(obj: BaseModel, values: Dict[str, Any], skip_keys: Set[str]):
    obj_values = obj.dict(exclude=skip_keys)
    assert obj_values == values
