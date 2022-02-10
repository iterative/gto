from typing import FrozenSet

from .base import BaseManager, BaseRegistryState, BaseVersion
from .constants import Action
from .index import RepoIndexState


class CommitVersionManager(BaseManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE, Action.DEMOTE))

    def update_state(
        self, state: BaseRegistryState, index: RepoIndexState
    ) -> BaseRegistryState:
        # each commit is a version if object is indexed in that commit
        for name, commits in index.object_centric_representation().items():
            for hexsha in commits:
                commit = self.repo.commit(hexsha)
                state.objects[name].versions.append(
                    BaseVersion(
                        object=name,
                        name=hexsha,
                        creation_date=commit.committed_datetime,
                        author=commit.author.name,
                        commit_hexsha=hexsha,
                    )
                )
        return state
