from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime


def flatten(obj):
    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
        return "_".join(obj)
    return obj


def serialize(data_to_serialize):
    data = deepcopy(data_to_serialize)
    if isinstance(data, (int, float, str, bool)):
        return data
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, list):
        return [serialize(i) for i in data]
    if isinstance(data, dict):
        return {flatten(key): serialize(value) for key, value in data.items()}
    if data is None:
        return data
    raise NotImplementedError(
        f"Serialisation is not implemented for {data_to_serialize} of type {type(data_to_serialize)}"
    )
