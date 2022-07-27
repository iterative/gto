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
