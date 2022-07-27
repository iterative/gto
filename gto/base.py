from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Sequence, Union

import git
from pydantic import BaseModel

from gto.config import RegistryConfig
from gto.constants import Action, VersionSort
from gto.ext import Enrichment
from gto.versions import SemVer

from .exceptions import (
    ArtifactNotFound,
    ManyVersions,
    NoStageForVersion,
    NotImplementedInGTO,
    VersionRequired,
)


# EVENTS: deprecation, registration, deregistration, assignment, unassignment
class BaseEvent(BaseModel):
    # some fields here are implementation details of tag-based
    # if we add other approaches beside tags, we'll need to fix this
    artifact: str
    created_at: datetime
    author: str
    author_email: str
    message: str
    commit_hexsha: str
    tag: str


class Creation(BaseEvent):
    pass


class Deprecation(BaseEvent):
    pass


class Registration(BaseEvent):
    version: str


class Deregistration(BaseEvent):
    version: str


class Assignment(BaseEvent):
    version: str
    stage: str


class Unassignment(BaseEvent):
    version: str
    stage: str


# ENTITIES: Artifact, Version, Stage
class BaseObject(BaseModel):
    artifact: str

    def add_event(self, event: BaseEvent):
        raise NotImplementedError()

    def get_events(self, ascending: bool = False) -> Sequence[BaseEvent]:
        raise NotImplementedError()

    def is_active(self):
        raise NotImplementedError()

    @property
    def activated_at(self):
        raise NotImplementedError()


class VStage(BaseObject):
    commit_hexsha: str
    version: str
    stage: str
    assignments: List[Assignment] = []
    unassignments: List[Unassignment] = []

    def add_event(self, event: BaseEvent):
        if isinstance(event, Assignment):
            self.assignments.append(event)
            self.assignments.sort(key=lambda p: p.created_at)
        elif isinstance(event, Unassignment):
            self.unassignments.append(event)
            self.unassignments.sort(key=lambda p: p.created_at)
        else:
            raise NotImplementedInGTO(f"Unknown event {event} of class {type(event)}")
        return event

    def get_events(self, ascending=False) -> Sequence[BaseEvent]:
        return sorted(
            self.assignments + self.unassignments, key=lambda e: e.created_at  # type: ignore
        )[:: 1 if ascending else -1]

    def is_active(self):
        return isinstance(self.get_events()[0], Assignment)

    @property
    def activated_at(self):
        if isinstance(self.get_events()[0], Assignment):
            return self.get_events()[0].created_at
        return None


class Version(BaseObject):
    commit_hexsha: str
    version: str
    discovered: bool = False
    registrations: List[Registration] = []
    deregistrations: List[Deregistration] = []
    stages: Dict[str, VStage] = {}
    enrichments: List[Enrichment] = []

    def add_event(self, event: BaseEvent):
        if isinstance(event, Registration):
            self.registrations.append(event)
            self.registrations.sort(key=lambda e: e.created_at)
        elif isinstance(event, Deregistration):
            self.deregistrations.append(event)
            self.deregistrations.sort(key=lambda e: e.created_at)
        elif isinstance(event, (Assignment, Unassignment)):
            self.get_vstage(event.stage, create_new=True).add_event(event)
        else:
            raise NotImplementedInGTO(f"Unknown event {event} of class {type(event)}")
        return event

    def get_events(self, ascending=False):
        return sorted(
            self.registrations
            + self.deregistrations
            + [e for s in self.stages.values() for e in s.get_events()],
            key=lambda e: e.created_at,
        )[:: 1 if ascending else -1]

    def is_active(self):
        if len(self.get_events()) == 0:
            return True
        return isinstance(self.get_events()[0], Registration)

    @property
    def activated_at(self):
        # TODO: handle the case with deregistration?
        if self.registrations:
            return self.registrations[0].created_at
        return self.get_events(ascending=True)[0].created_at

    @property
    def is_registered(self):
        """Tells if this is an explicitly registered version"""
        return len(self.registrations) > 0  # SemVer.is_valid(self.name)

    @property
    def semver(self):
        return SemVer(self.version)

    def get_vstage(self, stage, create_new=False):
        if create_new and stage not in self.stages:
            self.stages[stage] = VStage(
                artifact=self.artifact,
                version=self.version,
                stage=stage,
                commit_hexsha=self.commit_hexsha,
            )
        if stage in self.stages:
            return self.stages[stage]
        raise NoStageForVersion(self.artifact, self.version, stage)

    def get_vstages(self, active_only=True, ascending=False):
        return sorted(
            [s for s in self.stages.values() if not active_only or s.is_active()],
            key=lambda s: s.activated_at,
        )[:: 1 if ascending else -1]

    def dict_status(self):
        version = self.dict()
        version["stages"] = [stage.dict() for stage in self.get_vstages()]
        return version


def sort_versions(
    versions,
    sort=VersionSort.SemVer,
    ascending=False,
    version="version",
    timestamp="created_at",
):
    """This function is used both in Studio and in GTO"""

    def get(obj, key):
        if isinstance(obj, dict):
            return obj[key]
        if isinstance(obj, BaseModel):
            return getattr(obj, key)
        raise NotImplementedError("Can sort either dict or BaseModel")

    sort = sort if isinstance(sort, VersionSort) else VersionSort[sort]
    if sort == VersionSort.SemVer:
        # sorting SemVer versions in a right way
        sorted_versions = sorted(
            (v for v in versions if SemVer.is_valid(get(v, version))),
            key=lambda x: SemVer(get(x, version)),
        )[:: 1 if ascending else -1]
        # sorting hexsha versions alphabetically
        sorted_versions.extend(
            sorted(
                (v for v in versions if not SemVer.is_valid(get(v, version))),
                key=lambda x: get(x, version),
            )[:: 1 if ascending else -1]
        )
    else:
        sorted_versions = sorted(
            versions,
            key=lambda x: get(x, timestamp),
        )[:: 1 if ascending else -1]
    return sorted_versions


class Artifact(BaseObject):
    versions: List[Version]
    creations: List[Creation] = []
    deprecations: List[Deprecation] = []

    def add_event(self, event: BaseEvent):
        if isinstance(event, Creation):
            self.creations.append(event)
            self.creations.sort(key=lambda e: e.created_at)
        elif isinstance(event, Deprecation):
            self.deprecations.append(event)
            self.deprecations.sort(key=lambda e: e.created_at)
        elif isinstance(
            event, (Registration, Deregistration, Assignment, Unassignment)
        ):
            self.find_version(
                event.version, commit_hexsha=event.commit_hexsha, create_new=True
            ).add_event(  # type: ignore
                event
            )
        else:
            raise NotImplementedInGTO(f"Unknown event {event} of class {type(event)}")
        return event

    def get_events(self, ascending=False) -> Sequence[BaseEvent]:
        return sorted(
            self.creations
            + self.deprecations  # type: ignore
            + [e for v in self.versions for e in v.get_events()],
            key=lambda e: e.created_at,
        )[:: 1 if ascending else -1]

    def is_active(self):
        if len(self.get_events()) == 0:
            return True
        return isinstance(self.get_events()[0], Creation)

    @property
    def activated_at(self):
        # TODO: handle the case with deprecation
        if self.creations:
            return self.creations[0].created_at
        return self.get_events(ascending=True)[0].created_at

    @property
    def unique_stages(self):
        return set(self.get_stages())

    def __repr__(self) -> str:
        versions = ", ".join(f"'{v.version}'" for v in self.versions)
        stages = ", ".join(f"'{p}'" for p in self.unique_stages)
        return f"Artifact(versions=[{versions}], stages=[{stages}])"

    def get_versions(
        self,
        include_non_explicit=False,
        include_discovered=False,
        sort=VersionSort.SemVer,
        ascending=False,
    ) -> List[Version]:
        versions = [
            v
            for v in self.versions
            if (v.is_registered and not v.discovered)
            or (include_discovered and v.discovered)
            or (include_non_explicit and not v.is_registered)
        ]
        return sort_versions(versions, sort=sort, ascending=ascending)

    def get_latest_version(
        self, registered_only=False, sort=VersionSort.SemVer
    ) -> Optional[Version]:
        versions = self.get_versions(
            include_non_explicit=not registered_only, sort=sort
        )
        if versions:
            return versions[0]
        return None

    def get_stages(
        self,
        registered_only=False,
        last_stage=False,
        sort=VersionSort.SemVer,
    ) -> Dict[str, List[Assignment]]:
        versions = self.get_versions(
            include_non_explicit=not registered_only, sort=sort
        )
        if sort == VersionSort.Timestamp:
            # for this sort we need to sort not versions, as above ^
            # but assignments themselves
            raise NotImplementedError("Sorting by timestamp is not implemented yet")
        stages: Dict[str, List[VStage]] = {}
        for version in versions:
            for a in (
                version.get_vstages()[-1:]
                if last_stage
                else version.get_vstages(ascending=True)
            ):
                if a.stage not in stages:
                    stages[a.stage] = []
                if a.version not in [i.version for i in stages[a.stage]]:
                    stages[a.stage].append(a)
        return stages  # type: ignore

    def update_enrichments(self, version, enrichments):
        self.find_version(
            name=version, include_discovered=True
        ).enrichments = enrichments

    @property
    def discovered(self):
        return any(not v.discovered for v in self.versions)

    def find_version(
        self,
        name: str = None,
        commit_hexsha: str = None,
        raise_if_not_found: bool = False,
        allow_multiple=False,
        include_discovered=False,
        create_new=False,
    ) -> Union[None, Version, List[Version]]:
        versions = [
            v
            for v in self.versions
            if (v.version == name if name else True)
            and (v.commit_hexsha == commit_hexsha if commit_hexsha else True)
            and (True if include_discovered else not v.discovered)
        ]
        if create_new and not versions:
            v = Version(
                artifact=self.artifact,
                version=name or commit_hexsha,
                commit_hexsha=commit_hexsha,
            )
            self.versions.append(v)
            versions = [v]
        if allow_multiple and versions:
            return versions
        if raise_if_not_found and not versions:
            raise VersionRequired(name=self.artifact)
        if len(versions) > 1:
            raise ManyVersions(
                name=self.artifact,
                versions=[v.version for v in versions],
            )
        return versions[0] if versions else None

    def find_version_at_commit(
        self, commit_hexsha: str, latest_datetime: datetime = None
    ):
        return [
            v
            for v in self.find_version(  # type: ignore
                commit_hexsha=commit_hexsha,
                raise_if_not_found=True,
                allow_multiple=True,
            )
            if (v.activated_at <= latest_datetime if latest_datetime else True)  # type: ignore
        ][-1]


class BaseRegistryState(BaseModel):
    artifacts: Dict[str, Artifact] = {}

    class Config:
        arbitrary_types_allowed = True

    def add_artifact(self, name):
        self.artifacts[name] = Artifact(artifact=name, versions=[])

    def update_artifact(self, artifact: Artifact):
        self.artifacts[artifact.artifact] = artifact

    def get_artifacts(self):
        return self.artifacts

    def find_artifact(self, name: str, create_new=False) -> Artifact:
        if name not in self.artifacts:
            if create_new:
                self.artifacts[name] = Artifact(artifact=name, versions=[])
            else:
                raise ArtifactNotFound(name)
        return self.artifacts[name]

    @property
    def unique_stages(self):
        return sorted({p for o in self.artifacts.values() for p in o.unique_stages})

    def find_commit(self, name, version):
        return (
            self.find_artifact(name)
            .find_version(name=version, raise_if_not_found=True)
            .commit_hexsha
        )

    def which(
        self, name, stage, raise_if_not_found=True, all=False, registered_only=False
    ):
        """Return stage active in specific stage"""
        assigned = self.find_artifact(name).get_stages(registered_only=registered_only)
        if stage in assigned:
            return assigned[stage] if all else assigned[stage][0]
        if raise_if_not_found:
            raise ValueError(f"Stage {stage} not found for {name}")
        return None


class BaseManager(BaseModel):
    repo: git.Repo
    actions: FrozenSet[Action]
    config: RegistryConfig

    class Config:
        arbitrary_types_allowed = True

    def update_state(
        self, state: BaseRegistryState
    ) -> BaseRegistryState:  # pylint: disable=no-self-use
        raise NotImplementedError

    def check_ref(self, ref: str, state: BaseRegistryState):
        raise NotImplementedError
