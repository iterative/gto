import os
from typing import List, Union

import git
from git import InvalidGitRepositoryError, Repo
from pydantic import BaseModel

from gto.base import Artifact, BasePromotion, BaseRegistryState
from gto.config import CONFIG_FILE_NAME, RegistryConfig
from gto.exceptions import (
    NoRepo,
    VersionAlreadyRegistered,
    VersionExistsForCommit,
)
from gto.index import EnrichmentManager
from gto.tag import TagStageManager, TagVersionManager
from gto.ui import echo
from gto.versions import SemVer


class GitRegistry(BaseModel):
    repo: git.Repo
    version_manager: TagVersionManager
    stage_manager: TagStageManager
    enrichment_manager: EnrichmentManager
    config: RegistryConfig

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_repo(cls, repo=Union[str, Repo], config: RegistryConfig = None):
        if isinstance(repo, str):
            try:
                repo = git.Repo(repo, search_parent_directories=True)
            except InvalidGitRepositoryError as e:
                raise NoRepo(repo) from e
        if config is None:
            config = RegistryConfig(
                CONFIG_FILE_NAME=os.path.join(repo.working_dir, CONFIG_FILE_NAME)
            )

        return cls(
            repo=repo,
            config=config,
            version_manager=TagVersionManager(repo=repo, config=config),
            stage_manager=TagStageManager(repo=repo, config=config),
            enrichment_manager=EnrichmentManager(repo=repo, config=config),
        )

    def get_state(
        self,
        # discover: bool = False, TODO
        all_branches=False,  # TODO pylint: disable=unused-argument
        all_commits=False,  # TODO pylint: disable=unused-argument
    ) -> BaseRegistryState:
        state = BaseRegistryState()
        state = self.version_manager.update_state(state)
        state = self.stage_manager.update_state(state)
        # state = self.enrichment_manager.update_state(
        #     state,  # discover=discover,
        #     all_branches=all_branches,
        #     all_commits=all_commits,
        # )
        state.sort()
        return state

    def get_artifacts(
        self,
        # discover=False,
        all_branches=False,
        all_commits=False,
    ):
        return self.get_state(
            # discover=discover,
            all_branches=all_branches,
            all_commits=all_commits,
        ).get_artifacts()

    def find_artifact(
        self,
        name: str = None,
        create_new=False,
        # discover=False,
        all_branches=False,
        all_commits=False,
    ):
        return self.get_state(
            # discover=discover,
            all_branches=all_branches,
            all_commits=all_commits,
        ).find_artifact(
            name, create_new=create_new  # type: ignore
        )

    def register(  # pylint: disable=too-many-locals
        self,
        name,
        ref,
        version=None,
        bump=None,
        stdout=False,
        type: str = None,
        path: str = None,
        virtual: bool = False,
        tags: List[str] = None,
        description: str = "",
        inherit_from: str = None,
    ):
        """Register artifact version"""
        ref = self.repo.commit(ref).hexsha
        # TODO: add the same check for other actions, to promote and etc
        # also we need to check integrity of the index+state
        found_artifact = self.find_artifact(name, create_new=True)
        # check that this commit don't have a version already
        found_version = found_artifact.find_version(commit_hexsha=ref)
        if found_version is not None and found_version.is_registered:
            raise VersionExistsForCommit(name, found_version.name)
        # if version name is provided, use it
        if version:
            if found_artifact.find_version(name=version) is not None:
                raise VersionAlreadyRegistered(version)
        else:
            # if version name wasn't provided but there were some, bump the last one
            last_version = found_artifact.get_latest_version(registered=True)
            if last_version:
                version = (
                    SemVer(last_version.name)
                    .bump(**({"part": bump} if bump else {}))
                    .version
                )
            # if no versions exist, use the minimal version possible
            else:
                version = SemVer.get_minimal().version
        if inherit_from:
            artifact = self.find_artifact(name).find_version(name=inherit_from).details
        else:
            last_version = self.find_artifact(name, create_new=True).get_latest_version(
                registered=True
            )
            artifact = last_version.details if last_version else Artifact(name=name)
        # update
        artifact.type = type or artifact.type
        artifact.path = path or artifact.path
        artifact.virtual = virtual or artifact.virtual
        artifact.tags = tags or artifact.tags
        artifact.description = description or artifact.description

        self.version_manager.register(
            name,
            version,
            ref,
            message=artifact.json(exclude_defaults=True),
        )
        registered_version = self.find_artifact(name).find_version(
            name=version, raise_if_not_found=True
        )
        if stdout:
            echo(
                f"Created git tag '{registered_version.tag}' that registers a new version with details: "
                f"{artifact.json(exclude_defaults=True)}"
            )
        return registered_version

    def promote(  # pylint: disable=too-many-locals
        self,
        name,
        stage,
        promote_version=None,
        promote_ref=None,
        name_version=None,
        simple=False,
        stdout=False,
        type: str = None,
        path: str = None,
        virtual: bool = False,
        tags: List[str] = None,
        description: str = "",
        inherit_from: str = None,
    ) -> BasePromotion:
        """Assign stage to specific artifact version"""
        self.config.assert_stage(stage)
        if not (promote_version is None) ^ (promote_ref is None):
            raise ValueError("One and only one of (version, ref) must be specified.")
        if promote_ref:
            promote_ref = self.repo.commit(promote_ref).hexsha
        found_artifact = self.find_artifact(name, create_new=True)
        if promote_version is not None:
            found_version = found_artifact.find_version(
                name=promote_version, raise_if_not_found=True
            )
            promote_ref = self.find_commit(name, promote_version)
        else:
            found_version = found_artifact.find_version(commit_hexsha=promote_ref)
            if found_version is None:
                self.register(
                    name,
                    version=name_version,
                    ref=promote_ref,
                    stdout=stdout,
                    type=type,
                    path=path,
                    virtual=virtual,
                    tags=tags,
                    description=description,
                )
        # TODO: can inherit from promotion tags also, so --inherit=<tag> should be supported
        if inherit_from:
            artifact = self.find_artifact(name).find_version(name=inherit_from).details
        else:
            last_version = self.find_artifact(name, create_new=True).get_latest_version(
                registered=True
            )
            # take last promotion first
            if last_version.promotions:
                artifact = last_version.promotions[-1].details
            # if no promotions, take version
            elif last_version:
                artifact = last_version.details
            # otherwise empty
            else:
                artifact = Artifact(name=name)
        # update
        artifact.type = type or artifact.type
        artifact.path = path or artifact.path
        artifact.virtual = virtual or artifact.virtual
        artifact.tags = tags or artifact.tags
        artifact.description = description or artifact.description

        self.stage_manager.promote(  # type: ignore
            name,
            stage,
            ref=promote_ref,
            message=artifact.json(exclude_defaults=True),
            simple=simple,
        )
        promotion = self.get_state().find_artifact(name).promoted[stage]
        if stdout:
            echo(
                f"Created git tag '{promotion.tag}' that promotes '{promotion.version}' with details: "
                f"{artifact.json(exclude_defaults=True)}"
            )
        return promotion

    def check_ref(self, ref: str):
        "Find out what was registered/promoted in this ref"
        return {
            "version": self.version_manager.check_ref(ref, self.get_state()),
            "stage": self.stage_manager.check_ref(ref, self.get_state()),
        }

    def find_commit(self, name, version):
        return self.get_state().find_commit(name, version)

    def which(self, name, stage, raise_if_not_found=True):
        """Return stage active in specific stage"""
        return self.get_state().which(name, stage, raise_if_not_found)

    def latest(self, name: str):
        """Return latest active version for artifact"""
        return self.get_state().find_artifact(name).get_latest_version()

    def get_stages(self, in_use: bool = False):
        """Return list of stages in the registry.
        If "in_use", return only those which are in use for non-deprecated artifacts.
        If not, return all available: either all allowed or all ever used.
        """
        if in_use:
            return {
                stage for o in self.get_artifacts().values() for stage in o.promoted
            }
        return self.config.stages or {
            stage for o in self.get_artifacts().values() for stage in o.unique_stages
        }
