from datetime import datetime
from typing import Dict, List, Optional

import click
import git
from pydantic import BaseModel, Field

from .config import CONFIG
from .exceptions import (
    GitopsException,
    NoActiveLabel,
    ObjectNotFound,
    UnknownEnvironment,
    VersionAlreadyRegistered,
    VersionExistsForCommit,
    VersionIsOld,
)


class BaseLabel(BaseModel):  # pylint: disable=too-many-instance-attributes
    category: str
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
    category: str
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
    category: str
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
    def latest_version(self) -> str:
        return sorted(
            (v for v in self.versions if v.is_registered),
            key=lambda x: x.creation_date,
        )[-1].name

    @property
    def latest_labels(self) -> Dict[str, Optional[BaseLabel]]:
        labels = {}
        for label in self.unique_labels:
            found = sorted(
                (
                    l
                    for l in self.labels
                    if l.name == label
                    and l.is_registered
                    and self.find_version(l.version) is not None
                ),
                key=lambda x: x.creation_date,
            )
            labels[label] = found[-1] if found else None
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
                raise GitopsException(
                    f"{len(versions)} versions of object {self.name} found"
                    + ", skipping unregistered"
                    if skip_unregistered
                    else ""
                )
            return versions[0]

        if len(versions) > 1:
            raise GitopsException(
                f"{len(versions)} versions of object {self.name} found"
                + ", skipping unregistered"
                if skip_unregistered
                else ""
            )
        return versions[0] if versions else None


class BaseRegistryState(BaseModel):
    objects: List[BaseObject]

    class Config:
        arbitrary_types_allowed = True

    def find_object(self, category, object, allow_new=False):
        objects = [
            m for m in self.objects if m.name == object and m.category == category
        ]
        if allow_new and not objects:
            return BaseObject(category=category, name=object, versions=[], labels=[])
        if not objects:
            raise ObjectNotFound(category, object)
        return objects[0]

    @property
    def unique_labels(self):
        return sorted({l for o in self.objects for l in o.unique_labels})

    def find_commit(self, category, object, version):
        return (
            self.find_object(category, object)
            .find_version(
                name=version, raise_if_not_found=True, skip_unregistered=False
            )
            .commit_hexsha
        )

    def which(self, category, object, label, raise_if_not_found=True):
        """Return version of object with specific label active"""
        latest_labels = self.find_object(category, object).latest_labels
        if label in latest_labels:
            return latest_labels[label].version
        if raise_if_not_found:
            raise ValueError(f"Label {label} not found for {category} {object}")
        return None


class BaseRegistry(BaseModel):
    repo: git.Repo = Field(default_factory=lambda: git.Repo("."))
    state: BaseRegistryState = Field(
        default_factory=lambda: BaseRegistryState(objects=[])
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_state()

    class Config:
        arbitrary_types_allowed = True
        environments = CONFIG.ENVIRONMENTS
        versions = CONFIG.versions_class

    def update_state(self):
        raise NotImplementedError

    def register(self, category, object, version, ref=None):
        """Register object version"""
        self.update_state()
        if ref is None:
            ref = self.repo.active_branch.commit.hexsha
        found_object = self.state.find_object(category, object, allow_new=True)
        found_version = found_object.find_version(version, skip_unregistered=False)
        if found_version is not None:
            raise VersionAlreadyRegistered(version)
        found_version = found_object.find_version(None, ref, skip_unregistered=True)
        if found_version is not None:
            raise VersionExistsForCommit(object, found_version.name)
        if (
            found_object.versions
            and self.__config__.versions(version) < found_object.latest_version
        ):
            raise VersionIsOld(latest=found_object.latest_version, suggested=version)
        self._register(
            category,
            object,
            version,
            ref,
            message=f"Registering object {object} version {version}",
        )

    def _register(self, category, object, version, ref, message):
        raise NotImplementedError

    def unregister(self, category, object, version):
        self.update_state()
        return self._unregister(category, object, version)

    def _unregister(self, category, object, version):
        raise NotImplementedError

    def promote(
        self,
        category,
        object,
        label,
        promote_version=None,
        promote_commit=None,
        name_version=None,
    ):
        """Assign label to specific object version"""
        if label not in self.__config__.environments:
            raise UnknownEnvironment(label)
        if promote_version is None and promote_commit is None:
            raise ValueError("Either version or commit must be specified")
        if promote_version is not None and promote_commit is not None:
            raise ValueError("Only one of version or commit must be specified")
        self.update_state()
        try:
            found_object = self.state.find_object(category, object)
        except ObjectNotFound as exc:
            raise BaseException(
                "To promote a object automatically you need to manually register it once."
            ) from exc
        if promote_version is not None:
            found_version = found_object.find_version(promote_version)
            if found_version is None:
                raise BaseException("Version is not found")
            promote_commit = self.find_commit(category, object, promote_version)
        else:
            found_version = found_object.find_version(None, promote_commit)
            if found_version is None:
                if name_version is None:
                    last_version = self.state.find_object(
                        category, object
                    ).latest_version
                    promote_version = (
                        self.__config__.versions(last_version).bump().version
                    )
                self.register(category, object, name_version, ref=promote_commit)
                click.echo(
                    f"Registered new version '{promote_version}' of {category} '{object}' at commit '{promote_commit}'"
                )
        self._promote(
            category,
            object,
            label,
            ref=promote_commit,
            message=f"Promoting {category} {object} version {promote_version} to label {label}",
        )
        return {"version": promote_version}

    def _promote(self, category, object, label, ref, message):
        raise NotImplementedError

    def demote(self, category, object, label):
        """De-promote object from given label"""
        # TODO: check if label wasn't demoted already
        self.update_state()
        if self.state.find_object(category, object).latest_labels.get(label) is None:
            raise NoActiveLabel(label=label, category=category, object=object)
        return self._demote(
            category,
            object,
            label,
            message=f"Demoting {category} {object} from label {label}",
        )

    def _demote(self, category, object, label, message):
        raise NotImplementedError

    def find_commit(self, category, object, version):
        self.update_state()
        return self.state.find_commit(category, object, version)

    def which(self, category, object, label, raise_if_not_found=True):
        """Return version of object with specific label active"""
        self.update_state()
        return self.state.which(category, object, label, raise_if_not_found)

    def latest(self, category: str, object: str):
        """Return latest version for object"""
        self.update_state()
        return self.state.find_object(category, object).latest_version
