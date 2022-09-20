import re
from enum import Enum

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
