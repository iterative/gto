import json
import sys
from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime
from enum import Enum

import click
from tabulate import tabulate

from gto.config import yaml


def flatten(obj):
    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
        return "_".join(obj)
    return obj


def serialize(data_to_serialize):  # pylint: disable=too-many-return-statements
    data = deepcopy(data_to_serialize)
    if isinstance(data, (int, float, str, bool)):
        return data
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, list):
        return [serialize(i) for i in data]
    if isinstance(data, dict):
        return {flatten(key): serialize(value) for key, value in data.items()}
    if isinstance(data, tuple):
        return (serialize(i) for i in data)
    if isinstance(data, set):
        return {serialize(i) for i in data}
    if isinstance(data, Enum):
        return data.value
    if data is None:
        return data
    raise NotImplementedError(
        f"Serialisation is not implemented for {data_to_serialize} of type {type(data_to_serialize)}"
    )


def format_echo(result, format, format_table=None, if_empty="", missing_value="-"):

    if format == "yaml":
        yaml.dump(serialize(result), sys.stdout)
        # or another way
        # https://stackoverflow.com/questions/61722242/dump-the-yaml-to-a-variable-instead-of-streaming-it-in-stdout-using-ruamel-yaml
    elif format == "json":
        click.echo(json.dumps(serialize(result)))
    elif format == "table":
        click.echo(
            tabulate(
                result[0],
                headers=result[1],
                tablefmt=format_table,
                showindex=False,
                missingval=missing_value,
            )
            if len(result)
            else if_empty
        )
    else:
        raise NotImplementedError(f"Format {format} is not implemented")
