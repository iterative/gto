from enum import Enum

REF = "ref"
# COMMIT = "commit"
TAG = "tag"
# BRANCH = "branch"
# FILE = "file"

ACTION = "action"
TYPE = "type"
NAME = "name"
PATH = "path"
VERSION = "version"
STAGE = "stage"
NUMBER = "number"


class Action(Enum):
    REGISTER = "register"
    PROMOTE = "promote"


class VersionSort(Enum):
    SemVer = "semver"
    Timestamp = "timestamp"
