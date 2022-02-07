from typing import FrozenSet, List

import git

from .base import BaseLabel, BaseManager, BaseRegistryState
from .config import CONFIG  # need to pass this when you initialize BranchEnvManager
from .constants import Action


def traverse_commit(commit: git.Commit, desired: git.Commit):
    if commit == desired:
        return True
    return any(traverse_commit(c, desired) for c in commit.parents)


def find_branches(repo: git.Repo, desired: str) -> List[git.Head]:
    return [
        branch
        for branch in repo.heads
        if traverse_commit(branch.commit, repo.commit(desired))
    ]


class BranchEnvManager(BaseManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE, Action.DEMOTE))

    def update_state(self, state):
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # we assume that the model is promoted the same moment it is registered
            for obj in state.objects:
                for version in state.objects[obj].versions:
                    # TODO: For each branch that has this commit in history
                    # we assume the model was promoted to corresponding env
                    # we should see are there any options to do this differently
                    for branch in find_branches(self.repo, version.commit_hexsha):
                        # figure out env from branch name
                        if CONFIG.ENV_BRANCH_MAPPING:
                            name = CONFIG.ENV_BRANCH_MAPPING.get(branch.name)
                        else:
                            name = branch.name
                        if name is None:
                            continue
                        state.objects[obj].labels.append(
                            BaseLabel(
                                category=version.category,
                                object=version.object,
                                version=version.name,
                                name=branch.name,
                                creation_date=version.creation_date,
                                author=version.author,
                                commit_hexsha=version.commit_hexsha,
                                unregistered_date=version.unregistered_date,
                            )
                        )
            return state
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
