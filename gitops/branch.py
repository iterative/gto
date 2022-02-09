# pylint: disable=no-self-argument, no-else-return, unused-argument, no-self-use, unused-import
from typing import FrozenSet, List

import git

from gitops.index import RepoIndexState

from .base import BaseLabel, BaseManager, BaseObject, BaseRegistryState
from .config import CONFIG  # need to pass this when you initialize BranchEnvManager
from .constants import Action


def traverse_commit_check(commit: git.Commit, desired: git.Commit):
    if commit == desired:
        return True
    return any(traverse_commit_check(c, desired) for c in commit.parents)


def find_branches(repo: git.Repo, desired: str) -> List[git.Head]:
    return [
        branch
        for branch in repo.heads
        if traverse_commit_check(branch.commit, repo.commit(desired))
    ]


# def traverse_commit_apply(commit: git.Commit, func: callable):
#     func(commit)
#     for parent in commit.parents:
#         traverse_commit_apply(parent, func)


# def add_baselabel(commit: git.Commit, obj: BaseObject):
#     obj.labels.append(
#         BaseLabel(
#             category=obj.category,
#             object=obj.name,
#             version=commit.hexsha,
#             name=branch.name,
#             creation_date=commit.committed_date,
#             author=commit.author,
#             commit_hexsha=commit.hexsha,
#         )
#     )


class BranchEnvManager(BaseManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE, Action.DEMOTE))

    def update_state(
        self, state: BaseRegistryState, index: RepoIndexState
    ) -> BaseRegistryState:
        if not CONFIG.VERSION_REQUIRED_FOR_ENV:
            # we assume each commit in a branch is a promotion to branch env
            # removing those commits in which the object was not indexed
            for (cat, obj), commits in index.object_centric_representation().items():
                for commit in commits:
                    state.objects[(cat, obj)].labels.append(
                        BaseLabel(
                            category=cat,
                            object=obj,
                            version=commit.hexsha,
                            name="ALL BRANCHES THROUGH WHICH I CAN DISCOVER THIS COMMIT",
                            creation_date=commit.committed_date,
                            author=commit.author,
                            commit_hexsha=commit.hexsha,
                            unregistered_date=None,
                        )
                    )
            return state
            # raise NotImplementedError
        # we assume that the model is promoted the same moment it is registered
        for cat, obj in state.objects:
            for version in state.objects[(cat, obj)].versions:
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
                    state.objects[(cat, obj)].labels.append(
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

    def promote(
        category,
        object,
        label,
        ref,
        message=None,  # arg is ignored
    ):
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # to promote, we need to register the version
            # with this setting, the versions should be already registered in BaseRegistry.promote
            # so we should not need to do anything here
            # special case: if you are trying to promote not the HEAD but another commit
            #   which has a version already registered and you don't want to deprecate it,
            #   then you need to create new commit with a model you want to use and register a version there
            return
        else:
            # to promote, we don't need anything
            #
            # except maybe creating a commit in the branch (do we want this?):
            # "gitops promote $MODEL $PATH staging" -> create commit in branch for "staging"
            raise NotImplementedError

    def demote(self):
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # can be done by deprecating a version. Need something like --deprecate_version flag for CLI
            # to acknowledge the actor understands the implication
            pass
        else:
            # can be done by reversing commit. Need something like --reverse_commit flag for CLI?
            # that will generate a commit with the model from the previous commit
            pass
