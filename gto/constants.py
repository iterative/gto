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
NUMBER = "number"


class Action(Enum):
    REGISTER = "register"
    ASSIGN = "assign"
    UNASSIGN = "unassign"


class VersionSort(Enum):
    SemVer = "semver"
    Timestamp = "timestamp"


ASSIGNMENTS_PER_VERSION = -1
VERSIONS_PER_STAGE = 1
