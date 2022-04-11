import os
from typing import Union

import click
import git
from git import InvalidGitRepositoryError, Repo
from pydantic import BaseModel

from gto.base import BaseManager, BasePromotion, BaseRegistryState
from gto.config import CONFIG_FILE_NAME, RegistryConfig
from gto.exceptions import (
    NoRepo,
    VersionAlreadyRegistered,
    VersionExistsForCommit,
    VersionIsOld,
)


class GitRegistry(BaseModel):
    repo: git.Repo
    version_manager: BaseManager
    stage_manager: BaseManager
    enrichment_manager: BaseManager
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
            version_manager=config.VERSION_MANAGER_CLS(repo=repo, config=config),
            stage_manager=config.STAGE_MANAGER_CLS(repo=repo, config=config),
            enrichment_manager=config.ENRICHMENT_MANAGER_CLS(repo=repo, config=config),
        )

    def get_state(
        self, discover: bool = False, all_branches=False, all_commits=False
    ) -> BaseRegistryState:
        state = BaseRegistryState()
        state = self.version_manager.update_state(state)
        state = self.stage_manager.update_state(state)
        state = self.enrichment_manager.update_state(  # type: ignore
            state, discover=discover, all_branches=all_branches, all_commits=all_commits
        )
        state.sort()
        return state

    def get_artifacts(self, discover=False, all_branches=False, all_commits=False):
        return self.get_state(
            discover=discover, all_branches=all_branches, all_commits=all_commits
        ).get_artifacts()

    def find_artifact(
        self,
        name: str = None,
        create_new=False,
        discover=False,
        all_branches=False,
        all_commits=False,
    ):
        return self.get_state(
            discover=discover, all_branches=all_branches, all_commits=all_commits
        ).find_artifact(
            name, create_new=create_new  # type: ignore
        )

    def register(self, name, ref, version=None, bump=None):
        """Register artifact version"""
        ref = self.repo.commit(ref).hexsha
        # TODO: add the same check for other actions, to promote and etc
        # also we need to check integrity of the index+state
        found_artifact = self.get_state().find_artifact(name, create_new=True)
        # check that this commit don't have a version already
        found_version = found_artifact.find_version(commit_hexsha=ref)
        if found_version is not None:
            raise VersionExistsForCommit(name, found_version.name)
        # if version name is provided, use it
        if version:
            if found_artifact.find_version(name=version) is not None:
                raise VersionAlreadyRegistered(version)
            if found_artifact.discovered:
                latest_ver = found_artifact.get_latest_version().name
                if self.config.VERSION_CLS(version) < latest_ver:
                    raise VersionIsOld(latest=latest_ver, suggested=version)
        # if version name wasn't provided but there were some, bump the last one
        elif found_artifact.discovered:
            version = (
                self.config.VERSION_CLS(
                    self.get_state().find_artifact(name).get_latest_version().name
                )
                .bump(**({"part": bump} if bump else {}))
                .version
            )
        # if no versions exist, use the minimal version possible
        else:
            version = self.config.VERSION_CLS.get_minimal().version
        self.version_manager.register(
            name,
            version,
            ref,
            message=f"Registering artifact {name} version {version}",
        )
        return (
            self.get_state()
            .find_artifact(name)
            .find_version(name=version, raise_if_not_found=True)
        )

    def promote(
        self,
        name,
        stage,
        promote_version=None,
        promote_ref=None,
        name_version=None,
        simple=False,
    ) -> BasePromotion:
        """Assign stage to specific artifact version"""
        self.config.assert_stage(stage)
        if not (promote_version is None) ^ (promote_ref is None):
            raise ValueError("One and only one of (version, ref) must be specified.")
        if promote_ref:
            promote_ref = self.repo.commit(promote_ref).hexsha
        found_artifact = self.get_state().find_artifact(name, create_new=True)
        if promote_version is not None:
            found_version = found_artifact.find_version(
                name=promote_version, raise_if_not_found=True
            )
            promote_ref = self.find_commit(name, promote_version)
        else:
            found_version = found_artifact.find_version(commit_hexsha=promote_ref)
            if found_version is None:
                version = self.register(name, version=name_version, ref=promote_ref)
                click.echo(
                    f"Registered new version '{version.name}' of '{name}' at commit '{promote_ref}'"
                )
        self.stage_manager.promote(  # type: ignore
            name,
            stage,
            ref=promote_ref,
            message=f"Promoting {name} version {promote_version} to stage {stage}",
            simple=simple,
        )
        return self.get_state().find_artifact(name).promoted[stage]

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
                stage
                for o in self.get_state().artifacts.values()
                for stage in o.promoted
            }
        return self.config.stages or {
            stage
            for o in self.get_state().artifacts.values()
            for stage in o.unique_stages
        }
