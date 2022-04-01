from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Union

import git
from pydantic import BaseModel

from gto.config import RegistryConfig
from gto.constants import Action
from gto.index import Artifact, ArtifactCommits
from gto.versions import NumberedVersion, SemVer

from .exceptions import ArtifactNotFound, ManyVersions, VersionRequired


class BasePromotion(BaseModel):
    artifact: Artifact
    version: str
    stage: str
    creation_date: datetime
    author: str
    commit_hexsha: str


class BaseVersion(BaseModel):
    artifact: Artifact
    name: str
    creation_date: datetime
    author: str
    commit_hexsha: str
    promotions: List[BasePromotion] = []

    @property
    def version(self):
        # TODO: this should be read from config, how to pass it down here?
        try:
            return NumberedVersion(self.name)
        except:  # pylint: disable=bare-except
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
    commits: ArtifactCommits
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

    def get_latest_version(self) -> Optional[BaseVersion]:
        versions = sorted(
            self.versions,
            key=lambda x: x.creation_date,
        )
        if versions:
            return versions[-1]
        return None

    @property
    def promoted(self) -> Dict[str, BasePromotion]:
        stages: Dict[str, BasePromotion] = {}
        for version in sorted(self.versions, key=lambda x: x.version, reverse=True):
            promotion = version.stage
            if promotion:
                stages[promotion.stage] = stages.get(promotion.stage) or promotion
        return stages

    def add_promotion(self, promotion: BasePromotion):
        self.find_version(name=promotion.version).promotions.append(  # type: ignore
            promotion
        )

    def find_version(
        self,
        name: str = None,
        commit_hexsha: str = None,
        raise_if_not_found=False,
        allow_multiple=False,
    ) -> Union[None, BaseVersion, List[BaseVersion]]:
        versions = [
            v
            for v in self.versions
            if (v.name == name if name else True)
            and (v.commit_hexsha == commit_hexsha if commit_hexsha else True)
        ]
        if allow_multiple:
            return versions
        if raise_if_not_found and not versions:
            for v in self.versions:
                print(v)
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
    artifacts: Dict[str, BaseArtifact]

    class Config:
        arbitrary_types_allowed = True

    def find_artifact(self, name):
        art = self.artifacts.get(name)
        if not art:
            raise ArtifactNotFound(name)
        return art

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
        for name in self.artifacts:
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
