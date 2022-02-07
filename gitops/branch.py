from typing import FrozenSet

from .base import BaseManager, BaseRegistryState

# need to pass this when you initialize BranchEnvManager
from .config import CONFIG
from .constants import Action


class BranchEnvManager(BaseManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE, Action.DEMOTE))

    def update_state(self, state):
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # we assume that the model was promoted when it was registered
            pass
        else:
            # we assume each commit in a branch is a promotion to branch env
            pass
        return state

    def promote(self):
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # to promote, we need to register the version
            pass
        else:
            # to promote, we don't need anything
            #
            # except maybe creating a commit in the branch (do we want this?):
            # "gitops promote $MODEL $PATH staging" -> create commit in branch for "staging"
            pass

    def demote(self):
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # can be done by deprecating a version. Need something like --deprecate_version flag for CLI
            # to acknowledge the actor understands the implication
            pass
        else:
            # can be done by reversing commit. Need something like --reverse_commit flag for CLI?
            # that will generate a commit with the model from the previous commit
            pass
