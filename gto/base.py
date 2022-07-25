from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Union

import git
from pydantic import BaseModel

from gto.config import RegistryConfig
from gto.constants import Action, VersionSort
from gto.ext import Enrichment
from gto.versions import SemVer

from .exceptions import ArtifactNotFound, ManyVersions, VersionRequired


class BaseAssignment(BaseModel):
    artifact: str
    version: str
    stage: str
    created_at: datetime
    author: str
    author_email: Optional[str]  # remove as optional later
    message: Optional[str]  # remove as optional later
    commit_hexsha: str
    tag: str


class BaseVersion(BaseModel):
    artifact: str
    name: str
    created_at: datetime
    author: str
    author_email: Optional[str]  # remove as optional later
    message: Optional[str]  # remove as optional later
    commit_hexsha: str
    discovered: bool = False
    tag: Optional[str] = None
    assignments: List[BaseAssignment] = []
    enrichments: List[Enrichment] = []

    @property
    def is_registered(self):
        """Tells if this is an explicitly registered version"""
        return self.tag is not None  # SemVer.is_valid(self.name)

    @property
    def version(self):
        # TODO: this should be read from config, how to pass it down here?
        return SemVer(self.name)

    def add_assignment(self, assignment: BaseAssignment):
        self.assignments.append(assignment)
        self.assignments.sort(key=lambda p: p.created_at)

    def dict_status(self):
        version = self.dict(exclude={"assignments"})
        version["assignments"] = (
            [a.dict() for a in self.assignments] if self.assignments else None
        )
        return version


def sort_versions(
    versions,
    sort=VersionSort.SemVer,
    ascending=False,
    version="name",
    timestamp="created_at",
):
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
    # if ascending:
    #     sorted_versions.reverse()
    return sorted_versions


class BaseArtifact(BaseModel):
    name: str
    versions: List[BaseVersion]

    @property
    def stages(self):
        return [
            assignment
            for version in self.versions
            for assignment in version.assignments
        ]

    @property
    def unique_stages(self):
        return {assignment.stage for assignment in self.stages}

    def __repr__(self) -> str:
        versions = ", ".join(f"'{v.name}'" for v in self.versions)
        stages = ", ".join(f"'{p}'" for p in self.unique_stages)
        return f"Artifact(versions=[{versions}], stages=[{stages}])"

    def get_versions(
        self,
        include_non_explicit=False,
        include_discovered=False,
        sort=VersionSort.SemVer,
        ascending=False,
    ) -> List[BaseVersion]:
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
    ) -> Optional[BaseVersion]:
        versions = self.get_versions(
            include_non_explicit=not registered_only, sort=sort
        )
        if versions:
            return versions[0]
        return None

    def get_assignments(
        self,
        registered_only=False,
        last_stage=False,
        sort=VersionSort.SemVer,
    ) -> Dict[str, Union[BaseAssignment, List[BaseAssignment]]]:
        versions = self.get_versions(
            include_non_explicit=not registered_only, sort=sort
        )
        if sort == VersionSort.Timestamp:
            # for this sort we need to sort not versions, as above ^
            # but assignments themselves
            raise NotImplementedError("Sorting by timestamp is not implemented yet")
        stages: Dict[str, List[BaseAssignment]] = {}
        for version in versions:
            for a in (
                version.assignments[::-1][:1] if last_stage else version.assignments
            ):
                if a.stage not in stages:
                    stages[a.stage] = []
                if a.version not in [i.version for i in stages[a.stage]]:
                    stages[a.stage].append(a)
        return stages  # type: ignore

    def add_version(self, version: BaseVersion):
        self.versions.append(version)

    def add_assignment(self, assignment: BaseAssignment):
        self.find_version(name=assignment.version).add_assignment(assignment)  # type: ignore

    def update_enrichments(self, version, enrichments):
        self.find_version(
            name=version, include_discovered=True
        ).enrichments = enrichments

    @property
    def discovered(self):
        return any(not v.discovered for v in self.versions)

    # @overload
    # def find_version(
    #     self,
    #     name: str = None,
    #     commit_hexsha: str = None,
    #     raise_if_not_found: Literal[True] = ...,
    #     allow_multiple: Literal[False] = ...,
    # ) -> BaseVersion:
    #     ...

    # @overload
    # def find_version(
    #     self,
    #     name: str = None,
    #     commit_hexsha: str = None,
    #     raise_if_not_found: Literal[False] = ...,
    #     allow_multiple: Literal[False] = ...,
    # ) -> Optional[BaseVersion]:
    #     ...

    # @overload
    # def find_version(
    #     self,
    #     name: str = None,
    #     commit_hexsha: str = None,
    #     raise_if_not_found: Literal[False] = ...,
    #     allow_multiple: Literal[True] = ...,
    # ) -> List[BaseVersion]:
    #     ...

    def find_version(
        self,
        name: str = None,
        commit_hexsha: str = None,
        raise_if_not_found: bool = False,
        allow_multiple=False,
        include_discovered=False,
    ) -> Union[None, BaseVersion, List[BaseVersion]]:
        versions = [
            v
            for v in self.versions
            if (v.name == name if name else True)
            and (v.commit_hexsha == commit_hexsha if commit_hexsha else True)
            and (True if include_discovered else not v.discovered)
        ]

        if allow_multiple:
            return versions
        if raise_if_not_found and not versions:
            raise VersionRequired(name=self.name)
        if len(versions) > 1:
            raise ManyVersions(
                name=self.name,
                versions=[v.name for v in versions],
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
            if (v.created_at <= latest_datetime if latest_datetime else True)  # type: ignore
        ][-1]


class BaseRegistryState(BaseModel):
    artifacts: Dict[str, BaseArtifact] = {}

    class Config:
        arbitrary_types_allowed = True

    def add_artifact(self, name):
        self.artifacts[name] = BaseArtifact(name=name, versions=[])

    def update_artifact(self, artifact: BaseArtifact):
        self.artifacts[artifact.name] = artifact

    def get_artifacts(self):
        return self.artifacts

    def find_artifact(self, name: str, create_new=False) -> BaseArtifact:
        if not name:
            raise ValueError("Artifact name is required")
        if name not in self.artifacts:
            if create_new:
                self.artifacts[name] = BaseArtifact(name=name, versions=[])
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
        assigned = self.find_artifact(name).get_assignments(
            registered_only=registered_only
        )
        if stage in assigned:
            return assigned[stage] if all else assigned[stage][0]
        if raise_if_not_found:
            raise ValueError(f"Stage {stage} not found for {name}")
        return None

    def sort(self):
        for name in self.artifacts:  # pylint: disable=consider-using-dict-items
            self.artifacts[name].versions.sort(key=lambda x: (x.created_at, x.name))
            self.artifacts[name].stages.sort(
                key=lambda x: (x.created_at, x.version, x.stage)
            )


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

    # better to uncomment this for typing, but it breaks the pylint

    # def register(self, name, version, ref, message):
    #     raise NotImplementedError

    # def assign(self, name, stage, ref, message):
    #     raise NotImplementedError

    def check_ref(self, ref: str, state: BaseRegistryState):
        raise NotImplementedError
