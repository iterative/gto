import os
from typing import Optional, Union

import git
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel

from gto.base import BaseAssignment, BaseRegistryState
from gto.config import (
    CONFIG_FILE_NAME,
    RegistryConfig,
    assert_name_is_valid,
    read_registry_config,
)
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
            except (InvalidGitRepositoryError, NoSuchPathError) as e:
                raise NoRepo(repo) from e
        if config is None:
            config = read_registry_config(
                os.path.join(repo.working_dir, CONFIG_FILE_NAME)
            )

        return cls(
            repo=repo,
            config=config,
            version_manager=TagVersionManager(repo=repo, config=config),
            stage_manager=TagStageManager(repo=repo, config=config),
            enrichment_manager=EnrichmentManager(repo=repo, config=config),
        )

    def is_gto_repo(self):
        if self.config.config_file_exists():
            return True
        if self.config.check_index_exist(self.repo.working_dir):
            return True
        if self.get_state() != BaseRegistryState():
            return True
        return False

    def get_state(
        self,
        all_branches=False,
        all_commits=False,
    ) -> BaseRegistryState:
        state = BaseRegistryState()
        state = self.version_manager.update_state(state)
        state = self.stage_manager.update_state(state)
        state = self.enrichment_manager.update_state(
            state,
            all_branches=all_branches,
            all_commits=all_commits,
        )
        state.sort()
        return state

    def get_artifacts(
        self,
        all_branches=False,
        all_commits=False,
    ):
        return self.get_state(
            all_branches=all_branches,
            all_commits=all_commits,
        ).get_artifacts()

    def find_artifact(
        self,
        name: str = None,
        create_new=False,
        all_branches=False,
        all_commits=False,
    ):
        return self.get_state(
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
        message=None,
        bump_major=False,
        bump_minor=False,
        bump_patch=False,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        """Register artifact version"""
        assert_name_is_valid(name)
        version_args = sum(
            bool(i) for i in (version, bump_major, bump_minor, bump_patch)
        )
        if version_args > 1:
            raise WrongArgs("Need to specify either version or single bump argument")
        ref = self.repo.commit(ref).hexsha
        # TODO: add the same check for other actions, to assign and etc
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
            last_version = found_artifact.get_latest_version(registered_only=True)
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
            message=message or f"Registering artifact {name} version {version}",
            author=author,
            author_email=author_email,
        )
        registered_version = self.find_artifact(name).find_version(
            name=version, raise_if_not_found=True
        )
        if stdout:
            echo(
                f"Created git tag '{registered_version.tag}' that registers a new version"
            )
        return registered_version

    def assign(  # pylint: disable=too-many-locals
        self,
        name,
        stage,
        version=None,
        ref=None,
        name_version=None,
        message=None,
        simple=False,
        force=False,
        skip_registration=False,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> BaseAssignment:
        """Assign stage to specific artifact version"""
        assert_name_is_valid(name)
        self.config.assert_stage(stage)
        if not (version is None) ^ (ref is None):
            raise WrongArgs("One and only one of (version, ref) must be specified.")
        if name_version and skip_registration:
            raise WrongArgs(
                "You either need to supply version name or skip registration"
            )
        if ref:
            ref = self.repo.commit(ref).hexsha
        found_artifact = self.find_artifact(name, create_new=True)
        if version:
            found_version = found_artifact.find_version(
                name=version, raise_if_not_found=False
            )
            if not found_version:
                raise WrongArgs(f"Version '{version}' is not registered")
            ref = self.find_commit(name, version)
        else:
            found_version = found_artifact.find_version(commit_hexsha=ref)
            if found_version:
                if name_version:
                    raise WrongArgs(
                        f"Can't register '{SemVer(name_version).version}', since '{found_version.name}' is registered already at this ref"
                    )
            elif not skip_registration:
                self.register(name, version=name_version, ref=ref, stdout=stdout)
        if (
            not force
            and found_version
            and found_version.assignments
            and any(a.stage == stage for a in found_version.assignments)
        ):
            raise WrongArgs(f"Version is already in stage '{stage}'")
        # TODO: getting tag name as a result and using it
        # is leaking implementation details in base module
        # it's roughly ok to have until we add other implementations
        # beside tag-based assignments
        tag = self.stage_manager.assign(  # type: ignore
            name,
            stage,
            ref=ref,
            message=message
            or f"Assigning stage {stage} to artifact {name} version {version}",
            simple=simple,
            author=author,
            author_email=author_email,
        )
        assignment = self.stage_manager.check_ref(tag, self.get_state())[name]
        if stdout:
            echo(
                f"Created git tag '{assignment.tag}' that assigns '{stage}' to '{assignment.version}'"
            )
        return assignment

    def _check_ref(self, ref, state):
        if ref.startswith("refs/tags/"):
            ref = ref[len("refs/tags/") :]
        if ref.startswith("refs/heads/"):
            ref = self.repo.commit(ref).hexsha
        return {
            "version": self.version_manager.check_ref(ref, state),
            "stage": self.stage_manager.check_ref(ref, state),
        }

    def check_ref(self, ref: str):
        "Find out what was registered/assigned in this ref"
        state = self.get_state()
        return self._check_ref(ref, state)

    def find_commit(self, name, version):
        return self.get_state().find_commit(name, version)

    def which(
        self, name, stage, raise_if_not_found=True, all=False, registered_only=False
    ):
        """Return stage active in specific stage"""
        return self.get_state().which(
            name, stage, raise_if_not_found, all=all, registered_only=registered_only
        )

    def latest(self, name: str, all: bool = False, registered: bool = True):
        """Return latest active version for artifact"""
        artifact = self.get_state().find_artifact(name)
        if all:
            return artifact.get_versions(include_non_explicit=not registered)
        return artifact.get_latest_version(registered_only=registered)

    def _get_allowed_stages(self):
        return self.config.STAGES

    def _get_used_stages(self):
        return sorted(
            {stage for o in self.get_artifacts().values() for stage in o.unique_stages}
        )

    def get_stages(self, allowed: bool = False, used: bool = False):
        """Return list of stages in the registry.
        If "allowed", return stages that are allowed in config.
        If "used", return stages that were used in registry.
        """
        assert not (allowed and used), """Either "allowed" or "used" can be set"""
        if allowed:
            return self._get_allowed_stages()
        if used:
            return self._get_used_stages()
        # if stages in config are set, return them
        if self._get_allowed_stages() is not None:
            return self._get_allowed_stages()
        # if stages aren't set in config, return those in use
        return self._get_used_stages()
