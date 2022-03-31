import logging
from datetime import datetime
from typing import Dict, FrozenSet

from git import BadName

from .base import BaseManager, BaseRegistryState, BaseVersion
from .constants import Action


class CommitVersionManager(BaseManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE,))

    def update_state(self, state: BaseRegistryState) -> BaseRegistryState:
        # each commit is a version if artifact is indexed in that commit
        for name, artifact in state.artifacts.items():
            for hexsha, index_artifact in artifact.commits.items():
                commit = self.repo.commit(hexsha)
                state.artifacts[name].versions.append(
                    BaseVersion(
                        artifact=index_artifact,
                        name=hexsha,
                        creation_date=datetime.fromtimestamp(commit.committed_date),
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
