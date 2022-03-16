from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Union

import git
from pydantic import BaseModel

from gto.constants import Action
from gto.index import ArtifactCommits

from .exceptions import ArtifactNotFound, ManyVersions, VersionRequired


class BaseLabel(BaseModel):  # pylint: disable=too-many-instance-attributes
    # category: str
    artifact: str
    version: str
    name: str
    creation_date: datetime
    author: str
    commit_hexsha: str
    deprecated_date: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"Label('{self.artifact}', '{self.version}', '{self.name}')"

    @property
    def is_registered(self):
        return self.deprecated_date is None


class BaseVersion(BaseModel):
    # category: str
    artifact: str
    name: str
    creation_date: datetime
    author: str
    commit_hexsha: str
    deprecated_date: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"Version('{self.artifact}', '{self.name}')"

    @property
    def is_registered(self):
        return self.deprecated_date is None


class BaseArtifact(BaseModel):
    name: str
    versions: List[BaseVersion]
    labels: List[BaseLabel]

    @property
    def unique_labels(self):
        return {l.name for l in self.labels}

    def __repr__(self) -> str:
        versions = ", ".join(f"'{v.name}'" for v in self.versions)
        labels = ", ".join(f"'{l}'" for l in self.unique_labels)
        return f"Artifact(versions=[{versions}], labels=[{labels}])"

    def get_latest_version(self, include_deprecated=False) -> Optional[BaseVersion]:
        versions = sorted(
            (v for v in self.versions if include_deprecated or v.is_registered),
            key=lambda x: x.creation_date,
        )
        if versions:
            return versions[-1]
        return None

    @property
    def latest_labels(self) -> Dict[str, BaseLabel]:
        labels: Dict[str, BaseLabel] = {}
        for label in self.labels:
            # TODO: check that version exists and wasn't demoted???
            # probably this check should be done during State construction
            # as the rules to know it are all there
            if not label.is_registered:
                continue
            if (
                label.name not in labels
                or labels[label.name].creation_date < label.creation_date
            ):
                labels[label.name] = label
        return labels

    def find_version(
        self,
        name: str = None,
        commit_hexsha: str = None,
        raise_if_not_found=False,
        skip_deprecated=True,
        allow_multiple=False,
    ) -> Union[None, BaseVersion, List[BaseVersion]]:
        versions = [
            v
            for v in self.versions
            if (v.name == name if name else True)
            and (v.commit_hexsha == commit_hexsha if commit_hexsha else True)
            and (v.deprecated_date is None if skip_deprecated else True)
        ]
        if allow_multiple:
            return versions
        if raise_if_not_found and not versions:
            raise VersionRequired(name=self.name, skip_deprecated=skip_deprecated)
        if len(versions) > 1:
            raise ManyVersions(
                name=self.name, versions=len(versions), skip_deprecated=skip_deprecated
            )
        return versions[0] if versions else None


class BaseRegistryState(BaseModel):
    artifacts: Dict[str, BaseArtifact]

    class Config:
        arbitrary_types_allowed = True

    def find_artifact(self, name):
        art = self.artifacts.get(name)
        if not art:
            raise ArtifactNotFound(name)
        return art

    @property
    def unique_labels(self):
        return sorted({l for o in self.artifacts.values() for l in o.unique_labels})

    def find_commit(self, name, version):
        return (
            self.find_artifact(name)
            .find_version(name=version, raise_if_not_found=True, skip_deprecated=False)
            .commit_hexsha
        )

    def which(self, name, label, raise_if_not_found=True):
        """Return label active in specific env"""
        latest_labels = self.find_artifact(name).latest_labels
        if label in latest_labels:
            return latest_labels[label]
        if raise_if_not_found:
            raise ValueError(f"Label {label} not found for {name}")
        return None

    def sort(self):
        for name in self.artifacts:
            self.artifacts[name].versions.sort(key=lambda x: (x.creation_date, x.name))
            self.artifacts[name].labels.sort(
                key=lambda x: (x.creation_date, x.version, x.name)
            )


class BaseManager(BaseModel):
    repo: git.Repo
    actions: FrozenSet[Action]

    class Config:
        arbitrary_types_allowed = True

    def update_state(
        self, state: BaseRegistryState, index: ArtifactCommits
    ) -> BaseRegistryState:  # pylint: disable=no-self-use
        raise NotImplementedError

    # better to uncomment this for typing, but it breaks the pylint

    # def register(self, name, version, ref, message):
    #     raise NotImplementedError

    # def deprecate(self, name, version):
    #     raise NotImplementedError

    # def promote(self, name, label, ref, message):
    #     raise NotImplementedError

    # def demote(self, name, label, message):
    #     raise NotImplementedError

    def check_ref(self, ref: str, state: BaseRegistryState):
        raise NotImplementedError
