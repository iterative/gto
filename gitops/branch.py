# pylint: disable=no-self-argument, no-else-return, unused-argument, no-self-use, unused-import
import logging
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
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # we assume each commit in a branch is a promotion to branch env
            # if object was indexed
            for name, commits in index.object_centric_representation().items():
                for hexsha in commits:
                    commit = self.repo.commit(hexsha)
                    for branch in find_branches(self.repo, hexsha):
                        env = CONFIG.branch_to_env(branch.name)
                        if env is None:
                            continue
                        state.objects[name].labels.append(
                            BaseLabel(
                                object=name,
                                version=commit.hexsha,
                                name=env,
                                creation_date=commit.committed_date,
                                author=commit.author.name,
                                commit_hexsha=commit.hexsha,
                                unregistered_date=None,
                            )
                        )
        else:
            # we assume that the model is promoted the same moment it is registered
            for name in state.objects:
                for version in state.objects[name].versions:
                    # TODO: For each branch that has this commit in history
                    # we assume the model was promoted to corresponding env
                    # we should see are there any options to do this differently
                    for branch in find_branches(self.repo, version.commit_hexsha):
                        # figure out env from branch name
                        env = CONFIG.branch_to_env(branch.name)
                        if env is None:
                            continue
                        state.objects[name].labels.append(
                            BaseLabel(
                                object=version.object,
                                version=version.name,
                                name=env,
                                creation_date=version.creation_date,
                                author=version.author,
                                commit_hexsha=version.commit_hexsha,
                                unregistered_date=version.unregistered_date,
                            )
                        )
        return state

    def promote(
        self,
        name,
        label,
        ref,
        message=None,  # arg is ignored
    ):
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # to promote, we need to register the version
            # with this setting, the versions should be already registered in BaseRegistry.promote
            # so we should not need to do anything here, except for maybe checking that it's done

            # special case: if you are trying to promote a commit
            # which has a version already registered and you don't want to deprecate it,
            # then you need to create new commit with a model you want to use and register a version there
            return None

        # to promote, we don't need anything
        if self.repo.heads[CONFIG.env_to_branch(label)].commit.hexsha == ref:
            logging.info(
                "HEAD commit in BRANCH is promoted to ENV by default, so you don't need to run 'promote' command"
            )
            return None
        # except maybe creating a commit in the branch (do we want this?):
        # "gitops promote $MODEL $PATH staging" -> create commit in branch for "staging"
        raise NotImplementedError(
            "If you want to promote a REF which is not HEAD of the appropriate branch, "
            "you need to create a new commit to that branch "
            "or move HEAD of it to the REF you want to promote"
        )

    def demote(self, name, label, message=None):
        if CONFIG.VERSION_REQUIRED_FOR_ENV:
            # can be done by deprecating a version. Need something like --deprecate_version flag for CLI
            # to acknowledge the actor understands the implication
            raise NotImplementedError("To demote, you need to deprecate a version")

        # can be done by reversing commit. Need something like --reverse_commit flag for CLI?
        # that will generate a commit with the model from the previous commit
        raise NotImplementedError(
            "To demote, you need to reverse a commit, "
            "move HEAD of the branch to the previous commit, "
            "or create a new commit with the model from the previous commit"
        )
