from enum import Enum

REF = "ref"
COMMIT = "commit"
TAG = "tag"
BRANCH = "branch"
FILE = "file"

ACTION = "action"
NAME = "name"
VERSION = "version"
LABEL = "label"
NUMBER = "number"


class Action(Enum):
    REGISTER = "register"
    UNREGISTER = "unregister"
    PROMOTE = "promote"
    DEMOTE = "demote"


class VersionPart(Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
