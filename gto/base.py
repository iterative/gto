from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Union

import git
from pydantic import BaseModel

from gto.config import RegistryConfig
from gto.constants import Action
from gto.ext import Enrichment
from gto.versions import SemVer

from .exceptions import ArtifactNotFound, ManyVersions, VersionRequired


class BasePromotion(BaseModel):
    artifact: str
    version: str
    stage: str
    creation_date: datetime
    author: str
    commit_hexsha: str
    tag: str


class BaseVersion(BaseModel):
    artifact: str
    name: str
    creation_date: datetime
    author: str
    commit_hexsha: str
    discovered: bool = False
    tag: Optional[str] = None
    promotions: List[BasePromotion] = []
    enrichments: List[Enrichment] = []

    @property
    def is_registered(self):
        """Tells if this is an explicitly registered version"""
        return self.tag is not None  # SemVer.is_valid(self.name)

    @property
    def version(self):
        # TODO: this should be read from config, how to pass it down here?
        return SemVer(self.name)

    @property
    def stage(self):
        promotions = sorted(self.promotions, key=lambda p: p.creation_date)
        return promotions[-1] if promotions else None

    def dict_status(self):
        version = self.dict(exclude={"promotions"})
        version["stage"] = self.stage.dict() if self.stage else None
        return version


class BaseArtifact(BaseModel):
    name: str
    versions: List[BaseVersion]

    @property
    def stages(self):
        return [l for v in self.versions for l in v.promotions]

    @property
    def unique_stages(self):
        return {l.stage for l in self.stages}

    def __repr__(self) -> str:
        versions = ", ".join(f"'{v.name}'" for v in self.versions)
        stages = ", ".join(f"'{l}'" for l in self.unique_stages)
        return f"Artifact(versions=[{versions}], stages=[{stages}])"

    def get_latest_version(self, registered=False) -> Optional[BaseVersion]:
        versions = sorted(
            (
                v
                for v in self.versions
                if not v.discovered and (not registered or v.is_registered)
            ),
            key=lambda x: x.creation_date,
        )
        if versions:
            return versions[-1]
        return None

    @property
    def promoted(self) -> Dict[str, BasePromotion]:
        stages: Dict[str, BasePromotion] = {}
        # semver
        versions = sorted(
            (v for v in self.versions if v.is_registered),
            key=lambda x: x.version,
            reverse=True,
        )
        # TODO: regular commits - these should be sorted by stage tag creation maybe?
        # E.g. when you created "rf#prod" tag, then you created a version.
        # It's probably should be a flag on CLI that will tell how to sort promoted for return.
        versions.extend(
            sorted(
                (v for v in self.versions if not v.is_registered),
                key=lambda x: x.creation_date,
                reverse=True,
            )
        )
        for version in versions:
            promotion = version.stage
            if promotion:
                stages[promotion.stage] = stages.get(promotion.stage) or promotion
        return stages

    def add_version(self, version: BaseVersion):
        self.versions.append(version)

    def add_promotion(self, promotion: BasePromotion):
        self.find_version(name=promotion.version).promotions.append(  # type: ignore
            promotion
        )

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

    def get_versions(self, include_discovered=False):
        return [v for v in self.versions if include_discovered or not v.discovered]

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
            if (v.creation_date <= latest_datetime if latest_datetime else True)  # type: ignore
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

    def find_artifact(self, name: str, create_new=False):
        if not name:
            raise ValueError("Artifact name is required")
        if name not in self.artifacts:
            if create_new:
                self.artifacts[name] = BaseArtifact(name=name, versions=[])
            else:
                raise ArtifactNotFound(name)
        return self.artifacts.get(name)

    @property
    def unique_stages(self):
        return sorted({l for o in self.artifacts.values() for l in o.unique_stages})

    def find_commit(self, name, version):
        return (
            self.find_artifact(name)
            .find_version(name=version, raise_if_not_found=True)
            .commit_hexsha
        )

    def which(self, name, stage, raise_if_not_found=True):
        """Return stage active in specific stage"""
        promoted = self.find_artifact(name).promoted
        if stage in promoted:
            return promoted[stage]
        if raise_if_not_found:
            raise ValueError(f"Stage {stage} not found for {name}")
        return None

    def sort(self):
        for name in self.artifacts:  # pylint: disable=consider-using-dict-items
            self.artifacts[name].versions.sort(key=lambda x: (x.creation_date, x.name))
            self.artifacts[name].stages.sort(
                key=lambda x: (x.creation_date, x.version, x.stage)
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

    # def promote(self, name, stage, ref, message):
    #     raise NotImplementedError

    def check_ref(self, ref: str, state: BaseRegistryState):
        raise NotImplementedError
