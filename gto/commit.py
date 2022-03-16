import logging
from typing import Dict, FrozenSet

from git import BadName

from .base import BaseManager, BaseRegistryState, BaseVersion
from .constants import Action
from .index import ArtifactCommits


class CommitVersionManager(BaseManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE, Action.DEMOTE))

    def update_state(
        self, state: BaseRegistryState, index: ArtifactCommits
    ) -> BaseRegistryState:
        # each commit is a version if artifact is indexed in that commit
        for name, commits in index.items():
            for hexsha in commits:
                commit = self.repo.commit(hexsha)
                state.artifacts[name].versions.append(
                    BaseVersion(
                        artifact=name,
                        name=hexsha,
                        creation_date=commit.committed_datetime,
                        author=commit.author.name,
                        commit_hexsha=hexsha,
                    )
                )
        return state

    def check_ref(self, ref: str, state: BaseRegistryState) -> Dict[str, BaseVersion]:
        try:
            # check this is a commit and it exists
            assert all(r.name != ref for r in self.repo.refs)
            ref = self.repo.commit(ref).hexsha
        except (BadName, AssertionError):
            logging.warning("Reference is not a commit hexsha or it doesn't exist")
            return {}
        return {
            name: version
            for name in state.artifacts
            for version in state.artifacts[name].versions
            if version.commit_hexsha == ref
        }
