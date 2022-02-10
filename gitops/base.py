from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Tuple

import click
import git
from pydantic import BaseModel, Field

from gitops.constants import Action
from gitops.index import RepoIndexState, read_index

from .config import CONFIG
from .exceptions import (
    GitopsException,
    NoActiveLabel,
    ObjectNotFound,
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
    objects: Dict[Tuple[str, str], BaseObject]

    class Config:
        arbitrary_types_allowed = True

    def find_object(self, category, object, allow_new=False):
        obj = self.objects.get((category, object))
        if not obj and allow_new:
            return BaseObject(category=category, name=object, versions=[], labels=[])
        if not obj:
            raise ObjectNotFound(category, object)
        return obj

    @property
    def unique_labels(self):
        return sorted({l for o in self.objects.values() for l in o.unique_labels})

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

    # def register(self, category, object, version, ref, message):
    #     raise NotImplementedError

    # def unregister(self, category, object, version):
    #     raise NotImplementedError

    # def promote(self, category, object, label, ref, message):
    #     raise NotImplementedError

    # def demote(self, category, object, label, message):
    #     raise NotImplementedError


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
                (cat, obj): BaseObject(category=cat, name=obj, versions=[], labels=[])
                for cat, obj in self.index.object_centric_representation()
            }
        )
        state = self.version_manager.update_state(state, self.index)
        state = self.env_manager.update_state(state, self.index)
        self.state = state

    def register(self, category, object, version, ref=None):
        """Register object version"""
        self.update_state()
        if ref is None:
            ref = self.repo.active_branch.commit.hexsha
        # TODO: add the same check for other actions, to promote and etc
        # also we need to check integrity of the index+state
        self.index.assert_existence(category, object, ref)
        found_object = self.state.find_object(category, object, allow_new=True)
        found_version = found_object.find_version(version, skip_unregistered=False)
        if found_version is not None:
            raise VersionAlreadyRegistered(version)
        found_version = found_object.find_version(None, ref, skip_unregistered=True)
        if found_version is not None:
            raise VersionExistsForCommit(object, found_version.name)
        if (
            found_object.versions
            and CONFIG.versions_class(version) < found_object.latest_version
        ):
            raise VersionIsOld(latest=found_object.latest_version, suggested=version)
        self.version_manager.register(
            category,
            object,
            version,
            ref,
            message=f"Registering object {object} version {version}",
        )

    def unregister(self, category, object, version):
        self.update_state()
        return self.version_manager.unregister(category, object, version)

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
        CONFIG.assert_env(label)
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
                    promote_version = CONFIG.versions_class(last_version).bump().version
                self.register(category, object, name_version, ref=promote_commit)
                click.echo(
                    f"Registered new version '{promote_version}' of {category} '{object}' at commit '{promote_commit}'"
                )
        self.env_manager.promote(
            category,
            object,
            label,
            ref=promote_commit,
            message=f"Promoting {category} {object} version {promote_version} to label {label}",
        )
        return {"version": promote_version}

    def demote(self, category, object, label):
        """De-promote object from given label"""
        # TODO: check if label wasn't demoted already
        self.update_state()
        if self.state.find_object(category, object).latest_labels.get(label) is None:
            raise NoActiveLabel(label=label, category=category, object=object)
        return self.env_manager.demote(
            category,
            object,
            label,
            message=f"Demoting {category} {object} from label {label}",
        )

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
