import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from gto.exceptions import ValidationError

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


name = "[a-z][a-z0-9-/]*[a-z0-9]"
semver = r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
counter = "?P<counter>[0-9]+"
name_regexp = re.compile(f"^{name}$")
tag_regexp = re.compile(
    f"^(?P<artifact>{name})(((#(?P<stage>{name})|@(?P<version>v{semver}))(?P<cancel>!?))|@((?P<deprecated>deprecated)|(?P<created>created)))(#({counter}))?$"
)
shortcut_regexp = re.compile(
    f"^(?P<artifact>{name})(((#(?P<stage>{name})|@(?P<latest>latest)|@(?P<greatest>greatest))))$"
)


def check_name_is_valid(value):
    return bool(re.search(name_regexp, value))


def assert_name_is_valid(value):
    if not check_name_is_valid(value):
        raise ValidationError(
            f"Invalid value '{value}'. Only lowercase english letters, , '-', '/' are allowed."
            "Value must be of len >= 2, must with a letter and end with a letter or a number."
        )


class Shortcut(BaseModel):
    name: str
    stage: Optional[str] = None
    latest: bool = False
    shortcut: bool = False


def parse_shortcut(value):
    match = re.search(shortcut_regexp, value)
    if match:
        value = match["artifact"]
        if match["stage"]:
            assert_name_is_valid(match["stage"])
    assert_name_is_valid(value)
    return Shortcut(
        name=value,
        stage=match["stage"] if match and match["stage"] else None,
        latest=bool(match and (match["latest"] or match["greatest"])),
        shortcut=bool(match),
    )


# taken from https://stackoverflow.com/a/22312124/19782654, modified to include url without .git at the end
remote_git_repo_regex = re.compile(
    r"((git|ssh|http(s)?)|(git@[\w\.]+))(:(//)?)([\w\.@\:/\-~]+)(/)?"
)


def mark_artifact_unregistered(artifact_name):
    return f"*{artifact_name}"


class VersionSort(Enum):
    SemVer = "semver"
    Timestamp = "timestamp"


ASSIGNMENTS_PER_VERSION = -1
VERSIONS_PER_STAGE = 1
