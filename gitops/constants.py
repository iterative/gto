from enum import Enum

ACTION = "action"
CATEGORY = "category"
OBJECT = "object"
VERSION = "version"
LABEL = "label"
NUMBER = "number"


class Action(Enum):
    REGISTER = "register"
    UNREGISTER = "unregister"
    PROMOTE = "promote"
    DEMOTE = "demote"
