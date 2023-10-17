import re
from enum import Enum
from typing import Optional

from gto.exceptions import ValidationError

from ._pydantic import BaseModel

COMMIT = "commit"
REF = "ref"
TAG = "tag"

ARTIFACT = "artifact"
ACTION = "action"
TYPE = "type"
NAME = "name"
PATH = "path"
VERSION = "version"
STAGE = "stage"
COUNTER = "counter"


class Action(Enum):
    CREATE = "create"
    DEPRECATE = "deprecate"
    DEREGISTER = "deregister"
    REGISTER = "register"
    ASSIGN = "assign"
    UNASSIGN = "unassign"


SEPARATOR_IN_NAME = ":"
SEPARATOR_IN_TAG = "="


def name_to_tag(value):
    return value.replace(SEPARATOR_IN_NAME, SEPARATOR_IN_TAG)


def tag_to_name(value):
    return value.replace(SEPARATOR_IN_TAG, SEPARATOR_IN_NAME)


dirname = "[a-zA-Z0-9-_./]+"  # improve?
name = r"[a-zA-Z0-9]([a-zA-Z0-9-/_]*[a-zA-Z0-9])?"
semver = r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
counter = "?P<counter>[0-9]+"
name_re = re.compile(f"^{name}$")
fullname = f"(?P<dirname>{dirname}{SEPARATOR_IN_NAME})?(?P<name>{name})"  # add test to check ":" is here only once?
fullname_in_tag = name_to_tag(fullname)
fullname_re = re.compile(f"^{fullname}$")
fullname_in_tag_re = re.compile(f"^{fullname_in_tag}$")

tag_re = re.compile(
    f"^(?P<artifact>{fullname_in_tag})(((#(?P<stage>{name})|@(?P<version>v{semver}))(?P<cancel>!?))|@((?P<deprecated>deprecated)|(?P<created>created)))(#({counter}))?$"
)
shortcut_re = re.compile(
    f"^(?P<artifact>{fullname})(#(?P<stage>{name})|@(?P<version>latest|greatest|v{semver}))$"
)
git_hexsha_re = re.compile(r"^[0-9a-fA-F]{40}$")


def is_hexsha(value):
    return bool(git_hexsha_re.search(value))


def check_string_is_valid(value, regex=name_re):
    return bool(regex.search(value))


def assert_name_is_valid(value):
    if not check_string_is_valid(value, regex=name_re):
        raise ValidationError(
            f"Invalid value '{value}'. Only letters, numbers, '_', '-', '/' are allowed."
            " Value must be of len >= 2 and must start and end with a letter or a number."
        )


def assert_fullname_is_valid(value):
    if not check_string_is_valid(value, regex=fullname_re):
        # fix error message to be regex-specific
        raise ValidationError(
            f"Invalid value '{value}'. Only letters, numbers, '_', '-', '/' are allowed."
            " Value must be of len >= 2 and must start and end with a letter or a number."
        )


class Shortcut(BaseModel):
    name: str
    stage: Optional[str] = None
    version: Optional[str] = None
    latest: bool = False
    shortcut: bool = False


def parse_shortcut(value):
    match = re.search(shortcut_re, value)
    if match:
        value = match["artifact"]
        if match["stage"]:
            assert_name_is_valid(match["stage"])
    latest = bool(match and (match["version"] in ("latest", "greatest")))
    return Shortcut(
        name=value,
        stage=match["stage"] if match and match["stage"] else None,
        version=match["version"] if match and match["version"] and not latest else None,
        latest=latest,
        shortcut=bool(match),
    )


def mark_artifact_unregistered(artifact_name):
    return f"*{artifact_name}"


class VersionSort(Enum):
    SemVer = "semver"
    Timestamp = "timestamp"


ASSIGNMENTS_PER_VERSION = -1
VERSIONS_PER_STAGE = 1
