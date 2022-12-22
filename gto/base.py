from datetime import datetime
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Union

import git
from pydantic import BaseModel

from gto.config import RegistryConfig
from gto.constants import (
    ASSIGNMENTS_PER_VERSION,
    VERSIONS_PER_STAGE,
    Action,
    VersionSort,
)
from gto.versions import SemVer

from .exceptions import (
    ArtifactNotFound,
    ManyVersions,
    NoStageForVersion,
    NotImplementedInGTO,
    VersionRequired,
    WrongArgs,
)


# EVENTS: deprecation, registration, deregistration, assignment, unassignment
class BaseEvent(BaseModel):
    priority: int
    addition: bool
    # some fields here are implementation details of tag-based
    # if we add other approaches beside tags, we'll need to fix this
    artifact: str
    created_at: datetime
    author: str
    author_email: str
    message: str
    commit_hexsha: str

    @property
    def event(self):
        return self.__class__.__name__.lower()

    def dict_state(self, exclude=None):
        state = self.dict(exclude=exclude)
        state["event"] = self.event
        return state

    @property
    def ref(self):
        return getattr(self, "tag", self.commit_hexsha)


class Commit(BaseEvent):
    priority = 0
    addition = True
    version: str
    enrichments: List[Any]
    committer: str
    committer_email: str

    def __str__(self):
        return f'Artifact "{self.artifact}" is annotated'


class Creation(BaseEvent):
    priority = 1
    addition = True
    tag: str

    def __str__(self):
        return f'Artifact "{self.artifact}" was created'


class Deprecation(BaseEvent):
    priority = 2
    addition = False
    tag: str

    def __str__(self):
        return f'Artifact "{self.artifact}" was deprecated'


class Registration(BaseEvent):
    priority = 3
    addition = True
    tag: str
    version: str

    def __str__(self):
        return f'Version "{self.version}" of artifact "{self.artifact}" was registered'


class Deregistration(BaseEvent):
    priority = 4
    addition = False
    tag: str
    version: str

    def __str__(self):
        return (
            f'Version "{self.version}" of artifact "{self.artifact}" was deregistered'
        )


class Assignment(BaseEvent):
    priority = 5
    addition = True
    tag: str
    version: str
    stage: str

    def __str__(self) -> str:
        return f'Stage "{self.stage}" was assigned to version "{self.version}" of artifact "{self.artifact}"'


class Unassignment(BaseEvent):
    priority = 6
    addition = False
    tag: str
    version: str
    stage: str

    def __str__(self) -> str:
        return f'Stage "{self.stage}" was unassigned from version "{self.version}" of artifact "{self.artifact}"'


# ENTITIES: Artifact, Version, Stage
class BaseObject(BaseModel):
    artifact: str

    def add_event(self, event: BaseEvent):
        raise NotImplementedError()

    def get_events(
        self, direct=True, indirect=True, ascending: bool = False
    ) -> Sequence[BaseEvent]:
        raise NotImplementedError()

    @property
    def is_active(self):
        raise NotImplementedError()

    @property
    def activated_at(self):
        raise NotImplementedError()

    @property
    def authoring_event(self):
        addition_events = [
            e for e in self.get_events(direct=True, indirect=False) if e.addition
        ]
        if addition_events:
            return addition_events[0]
        events = self.get_events(direct=False, indirect=True)
        except_enrichment = [e for e in events if e.event != "enrichment"]
        if except_enrichment:
            return except_enrichment[0]
        return events[0]

    @property
    def created_at(self):
        return self.authoring_event.created_at

    @property
    def author(self):
        return self.authoring_event.author

    @property
    def author_email(self):
        return self.authoring_event.author_email

    @property
    def message(self):
        return self.authoring_event.message

    @property
    def ref(self):
        return self.authoring_event.ref

    def dict_state(self, exclude=None):
        version = self.dict(exclude=exclude)
        version["is_active"] = self.is_active
        version["activated_at"] = self.activated_at
        version["created_at"] = self.created_at
        version["author"] = self.author
        version["author_email"] = self.author_email
        version["message"] = self.message
        version["ref"] = self.ref
        return version


class VStage(BaseObject):
    commit_hexsha: str
    version: str
    stage: str
    assignments: List[Assignment] = []
    unassignments: List[Unassignment] = []

    def add_event(self, event: BaseEvent):
        if event in self.get_events():
            return event
        if isinstance(event, Assignment):
            self.assignments.append(event)
            self.assignments.sort(key=lambda e: e.created_at)
        elif isinstance(event, Unassignment):
            self.unassignments.append(event)
            self.unassignments.sort(key=lambda e: e.created_at)
        else:
            raise NotImplementedInGTO(f"Unknown event {event} of class {type(event)}")
        return event

    def get_events(
        self, direct=True, indirect=True, ascending=False
    ) -> Sequence[BaseEvent]:  # pylint: disable=unused-argument
        return sorted(
            self.assignments + self.unassignments if direct else [], key=lambda e: e.created_at  # type: ignore
        )[:: 1 if ascending else -1]

    @property
    def is_active(self):
        return isinstance(self.get_events()[0], Assignment)

    @property
    def activated_at(self):
        if isinstance(self.get_events()[0], Assignment):
            return self.get_events()[0].created_at
        return None

    def dict_state(self, exclude=None):
        state = super().dict_state(exclude=exclude)
        state["assignments"] = [a.dict_state() for a in self.assignments]
        state["unassignments"] = [a.dict_state() for a in self.unassignments]
        return state


class Version(BaseObject):
    commit_hexsha: str
    version: str
    enrichments: List[Commit] = []
    registrations: List[Registration] = []
    deregistrations: List[Deregistration] = []
    stages: Dict[str, VStage] = {}

    def add_event(self, event: BaseEvent):
        if event in self.get_events():
            return event
        if isinstance(event, Registration):
            self.registrations.append(event)
            self.registrations.sort(key=lambda e: e.created_at)
        elif isinstance(event, Deregistration):
            self.deregistrations.append(event)
            self.deregistrations.sort(key=lambda e: e.created_at)
        elif isinstance(event, Commit):
            self.enrichments.append(event)
            self.enrichments.sort(key=lambda e: e.created_at)
        elif isinstance(event, (Assignment, Unassignment)):
            self.get_vstage(event.stage, create_new=True).add_event(event)
        else:
            raise NotImplementedInGTO(f"Unknown event {event} of class {type(event)}")
        return event

    def get_events(self, direct=True, indirect=True, ascending=False):
        return sorted(
            (self.registrations + self.deregistrations if direct else [])
            + (
                self.enrichments
                + [e for s in self.stages.values() for e in s.get_events()]
                if indirect
                else []
            ),
            key=lambda e: e.created_at,
        )[:: 1 if ascending else -1]

    @property
    def is_active(self):
        direct_events = self.get_events(direct=True, indirect=False)
        if direct_events:
            return isinstance(direct_events[0], Registration)
        indirect_events = self.get_events(direct=False, indirect=True)
        if indirect_events:
            return True
        return False

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
    def discovered(self):
        return len(self.get_events(direct=True, indirect=False)) == 0

    @property
    def get_enrichments_info(self):
        if len(self.enrichments) > 1:
            raise NotImplementedInGTO(
                "Multiple enrichments for a single version are not supported"
            )
        return self.enrichments[0].enrichments

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
            [s for s in self.stages.values() if not active_only or s.is_active],
            key=lambda s: s.activated_at,
        )[:: 1 if ascending else -1]

    def dict_state(self, exclude=None, assignments_per_version=ASSIGNMENTS_PER_VERSION):
        if assignments_per_version < -1:
            raise WrongArgs("'assignments_per_version' must be >= -1")
        version = super().dict_state(exclude=exclude)
        version["discovered"] = self.discovered
        version["stages"] = [stage.dict_state() for stage in self.get_vstages()]
        if assignments_per_version >= 0:
            version["stages"] = version["stages"][:assignments_per_version]
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
        if event in self.get_events():
            return event
        if isinstance(event, Creation):
            self.creations.append(event)
            self.creations.sort(key=lambda e: e.created_at)
        elif isinstance(event, Deprecation):
            self.deprecations.append(event)
            self.deprecations.sort(key=lambda e: e.created_at)
        elif isinstance(
            event, (Registration, Deregistration, Assignment, Unassignment, Commit)
        ):
            self.find_version(
                event.version, commit_hexsha=event.commit_hexsha, create_new=True
            ).add_event(  # type: ignore
                event
            )
        else:
            raise NotImplementedInGTO(f"Unknown event {event} of class {type(event)}")
        return event

    def get_events(
        self, direct=True, indirect=True, ascending=False
    ) -> Sequence[BaseEvent]:
        return sorted(
            (self.creations + self.deprecations if direct else [])  # type: ignore
            + ([e for v in self.versions for e in v.get_events()] if indirect else []),
            key=lambda e: e.created_at,
        )[:: 1 if ascending else -1]

    @property
    def is_active(self):
        if len(self.get_events()) == 0:
            return False
        return not isinstance(self.get_events()[0], Deprecation)

    @property
    def activated_at(self):
        # TODO: handle the case with deprecation
        if self.creations:
            return self.creations[0].created_at
        return self.get_events(ascending=True)[0].created_at

    @property
    def is_registered(self):
        """Tells if this is an a registered artifact - i.e. there are Git tags for it"""
        return not all(
            isinstance(e, Commit) for e in self.get_events(direct=True, indirect=True)
        )

    @property
    def unique_stages(self):
        return set(self.get_vstages())

    def __repr__(self) -> str:
        versions = ", ".join(f"'{v.version}'" for v in self.versions)
        stages = ", ".join(f"'{p}'" for p in self.unique_stages)
        return f"Artifact(versions=[{versions}], stages=[{stages}])"

    def get_versions(
        self,
        active_only=True,
        include_non_explicit=False,
        include_discovered=False,
        sort=VersionSort.SemVer,
        ascending=False,
    ) -> List[Version]:
        versions = [
            v
            for v in self.versions
            if not active_only
            or v.is_active
            and (
                (v.is_registered and not v.discovered)
                or (include_discovered and v.discovered)
                or (include_non_explicit and not v.is_registered)
            )
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

    def get_vstages(
        self,
        registered_only=False,
        assignments_per_version=ASSIGNMENTS_PER_VERSION,
        versions_per_stage=VERSIONS_PER_STAGE,
        sort=VersionSort.SemVer,
    ):
        if assignments_per_version < -1:
            raise WrongArgs("'assignments_per_version' must be >= -1")
        if versions_per_stage < -1:
            raise WrongArgs("'versions_per_stage' must be >=-1")
        versions = self.get_versions(
            include_non_explicit=not registered_only, sort=sort
        )
        stages: Dict[str, List[VStage]] = {}
        assignments = [
            a
            for version in versions
            for a in (
                version.get_vstages(ascending=True)[:assignments_per_version]
                if assignments_per_version > -1
                else version.get_vstages(ascending=True)
            )
        ]
        if sort == VersionSort.Timestamp:
            assignments = sorted(assignments, key=lambda a: a.created_at)[::-1]
        for a in assignments:
            if a.stage not in stages:
                stages[a.stage] = []
            if (
                versions_per_stage > -1  # pylint: disable=chained-comparison
                and len(stages[a.stage]) >= versions_per_stage
            ):
                continue
            if a.version not in [i.version for i in stages[a.stage]]:
                stages[a.stage].append(a)
        return stages

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
        self,
        name,
        stage,
        raise_if_not_found=True,
        assignments_per_version=None,
        versions_per_stage=None,
        registered_only=False,
    ):
        """Return stage active in specific stage"""
        assigned = self.find_artifact(name).get_vstages(
            registered_only=registered_only,
            assignments_per_version=assignments_per_version,
            versions_per_stage=versions_per_stage,
        )
        if stage in assigned:
            return assigned[stage]
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
