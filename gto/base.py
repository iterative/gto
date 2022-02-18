from datetime import datetime
from typing import Dict, FrozenSet, List, Optional

import click
import git
from pydantic import BaseModel, Field

from gto.constants import Action
from gto.index import RepoIndexState, read_index

from .config import CONFIG
from .exceptions import (
    gtoException,
    NoActiveLabel,
    ObjectNotFound,
    VersionAlreadyRegistered,
    VersionExistsForCommit,
    VersionIsOld,
)


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
    def latest_version(self) -> Optional[str]:
        if self.versions:
            return sorted(
                (v for v in self.versions if v.is_registered),
                key=lambda x: x.creation_date,
            )[-1].name
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
                raise gtoException(
                    f"{len(versions)} versions of object {self.name} found"
                    + ", skipping unregistered"
                    if skip_unregistered
                    else ""
                )
            return versions[0]

        if len(versions) > 1:
            raise gtoException(
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
        """Return version of object with specific label active"""
        latest_labels = self.find_object(name).latest_labels
        if label in latest_labels:
            return latest_labels[label].version
        if raise_if_not_found:
            raise ValueError(f"Label {label} not found for {name}")
        return None


class BaseManager(BaseModel):
    repo: git.Repo
    actions: FrozenSet[Action]

    class Config:
        arbitrary_types_allowed = True

    def update_state(
        self, state: BaseRegistryState, index: RepoIndexState
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


class BaseRegistry(BaseModel):
    repo: git.Repo
    version_manager: BaseManager
    env_manager: BaseManager
    state: BaseRegistryState = Field(
        default_factory=lambda: BaseRegistryState(objects=[])
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_state()

    class Config:
        arbitrary_types_allowed = True

    @property
    def index(self) -> RepoIndexState:
        return read_index(self.repo)

    def update_state(self):
        state = BaseRegistryState(
            objects={
                name: BaseObject(name=name, versions=[], labels=[])
                for name in self.index.object_centric_representation()
            }
        )
        state = self.version_manager.update_state(state, self.index)
        state = self.env_manager.update_state(state, self.index)
        self.state = state

    def register(self, name, version, ref):
        """Register object version"""
        self.update_state()
        ref = self.repo.commit(ref).hexsha
        # TODO: add the same check for other actions, to promote and etc
        # also we need to check integrity of the index+state
        self.index.assert_existence(name, ref)
        found_object = self.state.find_object(name)
        found_version = found_object.find_version(name=version, skip_unregistered=False)
        if found_version is not None:
            raise VersionAlreadyRegistered(version)
        found_version = found_object.find_version(
            commit_hexsha=ref, skip_unregistered=True
        )
        if found_version is not None:
            raise VersionExistsForCommit(name, found_version.name)
        if (
            found_object.versions
            and CONFIG.versions_class(version) < found_object.latest_version
        ):
            raise VersionIsOld(latest=found_object.latest_version, suggested=version)
        self.version_manager.register(
            name,
            version,
            ref,
            message=f"Registering object {name} version {version}",
        )

    def unregister(self, name, version):
        self.update_state()
        return self.version_manager.unregister(name, version)

    def promote(
        self,
        name,
        label,
        promote_version=None,
        promote_ref=None,
        name_version=None,
    ):
        """Assign label to specific object version"""
        CONFIG.assert_env(label)
        if promote_version is None and promote_ref is None:
            raise ValueError("Either version or commit must be specified")
        if promote_version is not None and promote_ref is not None:
            raise ValueError("Only one of version or commit must be specified")
        if promote_ref:
            promote_ref = self.repo.commit(promote_ref).hexsha
        self.update_state()
        if promote_ref:
            self.index.assert_existence(name, promote_ref)
        found_object = self.state.find_object(name)
        if promote_version is not None:
            found_version = found_object.find_version(
                name=promote_version, raise_if_not_found=True
            )
            promote_ref = self.find_commit(name, promote_version)
        else:
            found_version = found_object.find_version(commit_hexsha=promote_ref)
            if found_version is None:
                if name_version is None:
                    last_version = self.state.find_object(name).latest_version
                    promote_version = CONFIG.versions_class(last_version).bump().version
                self.register(name, name_version, ref=promote_ref)
                click.echo(
                    f"Registered new version '{promote_version}' of '{name}' at commit '{promote_ref}'"
                )
        self.env_manager.promote(
            name,
            label,
            ref=promote_ref,
            message=f"Promoting {name} version {promote_version} to label {label}",
        )
        return {"version": promote_version}

    def demote(self, name, label):
        """De-promote object from given label"""
        # TODO: check if label wasn't demoted already
        self.update_state()
        if self.state.find_object(name).latest_labels.get(label) is None:
            raise NoActiveLabel(label=label, name=name)
        return self.env_manager.demote(
            name,
            label,
            message=f"Demoting {name} from label {label}",
        )

    def check_ref(self, ref: str):
        "Find out what was registered/promoted in this ref"
        self.update_state()
        return {
            "version": self.version_manager.check_ref(ref, self.state),
            "env": self.env_manager.check_ref(ref, self.state),
        }

    def find_commit(self, name, version):
        self.update_state()
        return self.state.find_commit(name, version)

    def which(self, name, label, raise_if_not_found=True):
        """Return version of object with specific label active"""
        self.update_state()
        return self.state.which(name, label, raise_if_not_found)

    def latest(self, name: str):
        """Return latest version for object"""
        self.update_state()
        return self.state.find_object(name).latest_version
