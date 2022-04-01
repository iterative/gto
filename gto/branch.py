# pylint: disable=no-self-argument, no-else-return, unused-argument, no-self-use, unused-import
import logging
from datetime import datetime
from typing import Dict, FrozenSet, List

import git

from .base import BaseManager, BasePromotion, BaseRegistryState
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


class BranchStageManager(BaseManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE,))

    def update_state(self, state: BaseRegistryState) -> BaseRegistryState:
        if self.config.VERSION_REQUIRED_FOR_STAGE:
            # we assume that the model is promoted the same moment it is registered
            for name in state.artifacts:
                for version in state.artifacts[name].versions:
                    # TODO: For each branch that has this commit in history
                    # we assume the model was promoted to corresponding stage
                    # we should see are there any options to do this differently
                    for branch in find_branches(self.repo, version.commit_hexsha):
                        # figure out stage from branch name
                        stage = self.config.branch_to_stage(branch.name)
                        if stage is None:
                            continue
                        state.artifacts[name].add_promotion(
                            BasePromotion(
                                artifact=version.artifact,
                                version=version.name,
                                stage=stage,
                                creation_date=version.creation_date,
                                author=version.author,
                                commit_hexsha=version.commit_hexsha,
                            )
                        )
        else:
            # we assume each commit in a branch is a promotion to branch stage
            # if artifact was indexed
            for name, artifact in state.artifacts.items():
                for hexsha, index_artifact in artifact.commits.items():
                    commit = self.repo.commit(hexsha)
                    version = state.artifacts[name].find_version(commit_hexsha=hexsha)  # type: ignore
                    version = version.name if version else hexsha  # type: ignore
                    for branch in find_branches(self.repo, hexsha):
                        stage = self.config.branch_to_stage(branch.name)
                        if stage is None:
                            continue
                        state.artifacts[name].add_promotion(
                            BasePromotion(
                                artifact=index_artifact,
                                version=version,
                                stage=stage,
                                creation_date=datetime.fromtimestamp(
                                    commit.committed_date
                                ),
                                author=commit.author.name,
                                commit_hexsha=commit.hexsha,
                            )
                        )
        return state

    def promote(
        self,
        name,
        stage,
        ref,
        message=None,  # arg is ignored
    ):
        if self.config.VERSION_REQUIRED_FOR_STAGE:
            # to promote, we need to register the version
            # with this setting, the versions should be already registered in BaseRegistry.promote
            # so we should not need to do anything here, except for maybe checking that it's done

            # special case: if you are trying to promote a commit
            # which has a version already registered and you don't want to deprecate it,
            # then you need to create new commit with a model you want to use and register a version there
            return None

        # to promote, we don't need anything
        if self.repo.heads[self.config.stage_to_branch(stage)].commit.hexsha == ref:
            logging.info(
                "HEAD commit in BRANCH is promoted to STAGE by default, so you don't need to run 'promote' command"
            )
            return None
        # except maybe creating a commit in the branch (do we want this?):
        # "gto promote $MODEL $PATH staging" -> create commit in branch for "staging"
        raise NotImplementedError(
            "If you want to promote a REF which is not HEAD of the appropriate branch, "
            "you need to create a new commit to that branch "
            "or move HEAD of it to the REF you want to promote"
        )

    def check_ref(self, ref: str, state: BaseRegistryState) -> Dict[str, BasePromotion]:
        # TODO: we assume ref is a commit. If it's a tag then we don't need to return anything
        # this is my assumption that should be discussed
        # it's based on case when CI will be triggered twice - for registration tag and promotion commit
        # VERSION_BASE='tag' VERSION_REQUIRED_FOR_STAGE=True STAGE_BASE='branch'
        try:
            assert all(r.name != ref for r in self.repo.refs)
            ref = self.repo.commit(ref).hexsha
        except (git.BadName, AssertionError):
            logging.warning("Reference is not a commit hexsha or it doesn't exist")
            return {}
        return {
            name: promotion
            for name in state.artifacts
            for promotion in state.artifacts[name].stages
            if promotion.commit_hexsha == ref
        }
