from enum import Enum

GTO = "gto"
MLEM = "mlem"

REF = "ref"
# COMMIT = "commit"
TAG = "tag"
# BRANCH = "branch"
# FILE = "file"

ACTION = "action"
NAME = "name"
VERSION = "version"
STAGE = "stage"
NUMBER = "number"

TYPE = "type"
PATH = "path"
DESCRIPTION = "description"


class Action(Enum):
    REGISTER = "register"
    PROMOTE = "promote"
