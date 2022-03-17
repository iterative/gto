from enum import Enum

REF = "ref"
COMMIT = "commit"
TAG = "tag"
BRANCH = "branch"
FILE = "file"

ACTION = "action"
TYPE = "type"
NAME = "name"
PATH = "path"
VERSION = "version"
LABEL = "label"
NUMBER = "number"


class Action(Enum):
    REGISTER = "register"
    DEPRECATE = "deprecate"
    PROMOTE = "promote"
    DEMOTE = "demote"


class VersionPart(Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
