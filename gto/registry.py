import os
from typing import Union

import git
from git import InvalidGitRepositoryError, Repo
from pydantic import BaseModel

from gto.base import BasePromotion, BaseRegistryState
from gto.config import CONFIG_FILE_NAME, RegistryConfig
from gto.exceptions import (
    NoRepo,
    VersionAlreadyRegistered,
    VersionExistsForCommit,
    WrongArgs,
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
        # discover: bool = False,
        all_branches=False,
        all_commits=False,
    ) -> BaseRegistryState:
        state = BaseRegistryState()
        state = self.version_manager.update_state(state)
        state = self.stage_manager.update_state(state)
        state = self.enrichment_manager.update_state(
            state,  # discover=discover,
            all_branches=all_branches,
            all_commits=all_commits,
        )
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

    def register(
        self,
        name,
        ref,
        version=None,
        bump_major=False,
        bump_minor=False,
        bump_patch=False,
        stdout=False,
    ):
        """Register artifact version"""
        version_args = sum(
            bool(i) for i in (version, bump_major, bump_minor, bump_patch)
        )
        if version_args > 1:
            raise WrongArgs("Need to specify either version or single bump argument")
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
            if not SemVer.is_valid(version):
                raise WrongArgs(
                    f"Version '{version}' is not valid. Example of valid version: 'v1.0.0'"
                )
        else:
            # if version name wasn't provided but there were some, bump the last one
            last_version = found_artifact.get_latest_version(registered=True)
            if last_version:
                version = (
                    SemVer(last_version.name)
                    .bump(
                        bump_major=bump_major,
                        bump_minor=bump_minor,
                        bump_patch=bump_patch if (bump_major or bump_minor) else True,
                    )
                    .version
                )
            elif version_args:
                raise WrongArgs(
                    "Can't apply bump, because this is the first version being registered"
                )
            else:
                version = SemVer.get_minimal().version
        self.version_manager.register(
            name,
            version,
            ref,
            message=f"Registering artifact {name} version {version}",
        )
        registered_version = self.find_artifact(name).find_version(
            name=version, raise_if_not_found=True
        )
        if stdout:
            echo(
                f"Created git tag '{registered_version.tag}' that registers a new version"
            )
        return registered_version

    def promote(
        self,
        name,
        stage,
        promote_version=None,
        promote_ref=None,
        name_version=None,
        simple=False,
        force=False,
        skip_registration=False,
        stdout=False,
    ) -> BasePromotion:
        """Assign stage to specific artifact version"""
        self.config.assert_stage(stage)
        if not (promote_version is None) ^ (promote_ref is None):
            raise WrongArgs("One and only one of (version, ref) must be specified.")
        if name_version and skip_registration:
            raise WrongArgs(
                "You either need to supply version name or skip registration"
            )
        if promote_ref:
            promote_ref = self.repo.commit(promote_ref).hexsha
        found_artifact = self.find_artifact(name, create_new=True)
        if promote_version:
            found_version = found_artifact.find_version(
                name=promote_version, raise_if_not_found=False
            )
            if not found_version:
                raise WrongArgs(f"Version '{promote_version}' is not registered")
            promote_ref = self.find_commit(name, promote_version)
        else:
            found_version = found_artifact.find_version(commit_hexsha=promote_ref)
            if found_version:
                if name_version:
                    raise WrongArgs(
                        f"Can't register '{SemVer(name_version).version}', since '{found_version.name}' is registered already at this ref"
                    )
            elif not skip_registration:
                self.register(
                    name, version=name_version, ref=promote_ref, stdout=stdout
                )
        if (
            not force
            and found_version
            and found_version.stage
            and found_version.stage.stage == stage
        ):
            raise WrongArgs(f"Version is already in stage '{stage}'")
        self.stage_manager.promote(  # type: ignore
            name,
            stage,
            ref=promote_ref,
            message=f"Promoting {name} version {promote_version} to stage {stage}",
            simple=simple,
        )
        promotion = self.get_state().find_artifact(name).promoted[stage]
        if stdout:
            echo(
                f"Created git tag '{promotion.tag}' that promotes '{promotion.version}'"
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
