from datetime import datetime
from typing import Dict, FrozenSet, List, Optional

import git
from pydantic import BaseModel

from gto.constants import Action
from gto.index import ObjectCommits

from .exceptions import GTOException, ObjectNotFound


class BaseLabel(BaseModel):  # pylint: disable=too-many-instance-attributes
    # category: str
    object: str
    version: str
    name: str
    creation_date: datetime
    author: str
    commit_hexsha: str
    unregistered_date: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"Label('{self.object}', '{self.version}', '{self.name}')"

    @property
    def is_registered(self):
        return self.unregistered_date is None


class BaseVersion(BaseModel):
    # category: str
    object: str
    name: str
    creation_date: datetime
    author: str
    commit_hexsha: str
    unregistered_date: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"Version('{self.object}', '{self.name}')"

    @property
    def is_registered(self):
        return self.unregistered_date is None


class BaseObject(BaseModel):
    name: str
    versions: List[BaseVersion]
    labels: List[BaseLabel]

    @property
    def unique_labels(self):
        return {l.name for l in self.labels}

    def __repr__(self) -> str:
        versions = ", ".join(f"'{v.name}'" for v in self.versions)
        labels = ", ".join(f"'{l}'" for l in self.unique_labels)
        return f"Object(versions=[{versions}], labels=[{labels}])"

    @property
    def latest_version(self) -> Optional[BaseVersion]:
        if self.versions:
            return sorted(
                (v for v in self.versions if v.is_registered),
                key=lambda x: x.creation_date,
            )[-1]
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
        skip_unregistered=True,
    ) -> Optional[BaseVersion]:
        versions = [
            v
            for v in self.versions
            if (v.name == name if name else True)
            and (v.commit_hexsha == commit_hexsha if commit_hexsha else True)
            and (v.unregistered_date is None if skip_unregistered else True)
        ]
        if raise_if_not_found:
            if len(versions) != 1:
                raise GTOException(
                    f"{len(versions)} versions of object {self.name} found"
                    + ", skipping unregistered"
                    if skip_unregistered
                    else ""
                )
            return versions[0]

        if len(versions) > 1:
            raise GTOException(
                f"{len(versions)} versions of object {self.name} found"
                + ", skipping unregistered"
                if skip_unregistered
                else ""
            )
        return versions[0] if versions else None


class BaseRegistryState(BaseModel):
    objects: Dict[str, BaseObject]

    class Config:
        arbitrary_types_allowed = True

    def find_object(self, name):
        obj = self.objects.get(name)
        if not obj:
            raise ObjectNotFound(name)
        return obj

    @property
    def unique_labels(self):
        return sorted({l for o in self.objects.values() for l in o.unique_labels})

    def find_commit(self, name, version):
        return (
            self.find_object(name)
            .find_version(
                name=version, raise_if_not_found=True, skip_unregistered=False
            )
            .commit_hexsha
        )

    def which(self, name, label, raise_if_not_found=True):
        """Return label active in specific env"""
        latest_labels = self.find_object(name).latest_labels
        if label in latest_labels:
            return latest_labels[label]
        if raise_if_not_found:
            raise ValueError(f"Label {label} not found for {name}")
        return None

    def sort(self):
        for name in self.objects:
            self.objects[name].versions.sort(key=lambda x: (x.creation_date, x.name))
            self.objects[name].labels.sort(
                key=lambda x: (x.creation_date, x.version, x.name)
            )


class BaseManager(BaseModel):
    repo: git.Repo
    actions: FrozenSet[Action]

    class Config:
        arbitrary_types_allowed = True

    def update_state(
        self, state: BaseRegistryState, index: ObjectCommits
    ) -> BaseRegistryState:  # pylint: disable=no-self-use
        raise NotImplementedError

    # better to uncomment this for typing, but it breaks the pylint

    # def register(self, name, version, ref, message):
    #     raise NotImplementedError

    # def unregister(self, name, version):
    #     raise NotImplementedError

    # def promote(self, name, label, ref, message):
    #     raise NotImplementedError

    # def demote(self, name, label, message):
    #     raise NotImplementedError

    def check_ref(self, ref: str, state: BaseRegistryState):
        raise NotImplementedError
