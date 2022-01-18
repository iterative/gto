from typing import Dict, List, Optional

import click
import git
import pandas as pd
from pydantic import BaseModel

from .config import CONFIG
from .exceptions import (
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
    creation_date: pd.Timestamp
    author: str
    commit_hexsha: str
    tag_name: str
    unregistered_date: Optional[pd.Timestamp] = None

    def __repr__(self) -> str:
        return f"Label('{self.object}', '{self.version}', '{self.name}')"


class BaseVersion(BaseModel):
    category: str
    object: str
    name: str
    creation_date: pd.Timestamp
    author: str
    commit_hexsha: str
    tag_name: str
    unregistered_date: Optional[pd.Timestamp] = None

    def __repr__(self) -> str:
        return f"Version('{self.object}', '{self.name}')"


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
            filter(lambda x: x.unregistered_date is None, self.versions),
            key=lambda x: x.creation_date,
        )[-1].name

    @property
    def latest_labels(self) -> Dict[str, Optional[BaseLabel]]:
        labels = {}
        for label in self.unique_labels:
            found = sorted(
                filter(
                    lambda x: x.name == label  # pylint: disable=cell-var-from-loop
                    and x.unregistered_date is None
                    and self.find_version(x.version) is not None,
                    self.labels,
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
            assert len(versions) == 1, (
                f"{len(versions)} versions of object {self.name} found"
                + ", skipping unregistered"
                if skip_unregistered
                else ""
            )
            return versions[0]

        assert len(versions) <= 1, (
            f"{len(versions)} versions of object {self.name} found"
            + ", skipping unregistered"
            if skip_unregistered
            else ""
        )
        return versions[0] if versions else None


class BaseRegistry:
    repo: git.Repo
    objects: List[BaseObject]
    config = CONFIG
    Object: BaseObject

    def __init__(self, repo: git.Repo = git.Repo(".")):
        self.repo = repo

    def find_object(self, category, object, allow_new=False):
        objects = [
            m for m in self.objects if m.name == object and m.category == category
        ]
        if allow_new and not objects:
            return self.Object(category, object, [], [])
        if not objects:
            raise ObjectNotFound(object)
        return objects[0]

    @property
    def _labels(self):
        raise NotImplementedError

    @property
    def labels(self):
        return sorted(set(self._labels))

    def _register(self, category, object, version, ref, message):
        raise NotImplementedError

    def register(self, category, object, version, ref=None):
        """Register object version"""
        if ref is None:
            ref = self.repo.active_branch.commit.hexsha
        found_object = self.find_object(category, object, allow_new=True)
        found_version = found_object.find_version(version, skip_unregistered=False)
        if found_version is not None:
            raise VersionAlreadyRegistered(version)
        found_version = found_object.find_version(None, ref, skip_unregistered=True)
        if found_version is not None:
            raise VersionExistsForCommit(object, found_version.name)
        if (
            found_object.versions
            and self.config.__versions__(version) < found_object.latest_version
        ):
            raise VersionIsOld(latest=found_object.latest_version, suggested=version)
        self._register(
            category,
            object,
            version,
            ref,
            message=f"Registering object {object} version {version}",
        )

    def unregister(self, category, object, version):
        raise NotImplementedError

    def find_commit(self, category, object, version):
        raise NotImplementedError

    def _promote(self, category, object, label, ref, message):
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
        if label not in self.config.ENVIRONMENTS:
            raise UnknownEnvironment(label)
        if promote_version is None and promote_commit is None:
            raise ValueError("Either version or commit must be specified")
        if promote_version is not None and promote_commit is not None:
            raise ValueError("Only one of version or commit must be specified")
        try:
            found_object = self.find_object(category, object)
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
                    last_version = self.find_object(category, object).latest_version
                    promote_version = (
                        self.config.__versions__(last_version).bump().version
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

    def _demote(self, category, object, label, message):
        raise NotImplementedError

    def demote(self, category, object, label):
        """De-promote object from given label"""
        # TODO: check if label wasn't demoted already
        assert (
            self.find_object(category, object).latest_labels.get(label) is not None
        ), f"No active label '{label}' was found for {category} '{object}'"
        return self._demote(
            category,
            object,
            label,
            message=f"Demoting {category} {object} from label {label}",
        )

    def which(self, category, object, label, raise_if_not_found=True):
        """Return version of object with specific label active"""
        latest_labels = self.find_object(category, object).latest_labels
        if label in latest_labels:
            return latest_labels[label].version
        if raise_if_not_found:
            raise ValueError(f"Label {label} not found for {category} {object}")
        return None
