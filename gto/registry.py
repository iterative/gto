import logging
import os
from typing import Optional, TypeVar, Union

import git
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel

from gto.base import (
    Assignment,
    BaseEvent,
    BaseRegistryState,
    Deregistration,
    Registration,
    Unassignment,
)
from gto.config import (
    CONFIG_FILE_NAME,
    RegistryConfig,
    assert_name_is_valid,
    read_registry_config,
)
from gto.constants import NAME
from gto.exceptions import (
    NoRepo,
    NotImplementedInGTO,
    VersionAlreadyRegistered,
    VersionExistsForCommit,
    WrongArgs,
)
from gto.index import EnrichmentManager
from gto.tag import TagStageManager, TagVersionManager, parse_name
from gto.ui import echo
from gto.versions import SemVer

TBaseEvent = TypeVar("TBaseEvent", bound=BaseEvent)


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
    ) -> Registration:
        """Register artifact version"""
        assert_name_is_valid(name)
        version_args = sum(
            bool(i) for i in (version, bump_major, bump_minor, bump_patch)
        )
        if version_args > 1:
            raise WrongArgs("Need to specify either version or single bump argument")
        ref = self.repo.commit(ref).hexsha
        found_artifact = self.find_artifact(name, create_new=True)
        # check that this commit don't have a version already
        found_version = found_artifact.find_version(commit_hexsha=ref)
        if found_version is not None and found_version.is_registered:
            raise VersionExistsForCommit(name, found_version.version)
        # if version name is provided, use it
        if version:
            if found_artifact.find_version(name=version) is not None:
                raise VersionAlreadyRegistered(version)
        else:
            # if version name wasn't provided but there were some, bump the last one
            last_version = found_artifact.get_latest_version(registered_only=True)
            if last_version:
                version = (
                    SemVer(last_version.version)
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
        tag = self.version_manager.register(
            name,
            version,
            ref,
            message=message or f"Registering artifact {name} version {version}",
            author=author,
            author_email=author_email,
        )
        return self._return_event(tag, stdout=stdout)

    def deregister(
        self,
        name,
        ref=None,
        version=None,
        message=None,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Deregistration:
        """Deregister artifact version"""
        self._check_args(name, version, ref)
        if ref is not None:
            ref = self.repo.commit(ref).hexsha
        found_artifact = self.find_artifact(name, create_new=True)
        found_version = found_artifact.find_version(name=version, commit_hexsha=ref)
        tag = self.version_manager.deregister(
            name,
            found_version.version,
            found_version.commit_hexsha,
            message=message or f"Deregistering artifact {name} version {version}",
            author=author,
            author_email=author_email,
        )
        return self._return_event(tag, stdout=stdout)

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
    ) -> Assignment:
        """Assign stage to specific artifact version"""
        self._check_args(name, version, ref, stage)
        if name_version:
            self._check_version(name_version)
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
                        f"Can't register '{SemVer(name_version).version}', since '{found_version.version}' is registered already at this ref"
                    )
            elif not skip_registration:
                self.register(name, version=name_version, ref=ref, stdout=stdout)
        if (
            not force
            and found_version
            and found_version.stages
            and any(vstage.stage == stage for vstage in found_version.get_vstages())
        ):
            raise WrongArgs(
                f"Version '{found_version.version}' is already in stage '{stage}'"
            )
        # TODO: getting tag name as a result and using it
        # is leaking implementation details in base module
        # it's roughly ok to have until we add other implementations
        # beside tag-based assignments
        tag = self.stage_manager.assign(  # type: ignore
            name,
            stage,
            ref=ref,
            message=message
            or f"Assigning stage {stage} to artifact {name} "
            + (
                f"version {found_version.version}" if found_version else f"commit {ref}"
            ),
            simple=simple,
            author=author,
            author_email=author_email,
        )
        return self._return_event(tag, stdout=stdout)

    def unassign(  # pylint: disable=too-many-locals
        self,
        name,
        stage,
        version=None,
        ref=None,
        message=None,
        simple=False,
        force=False,
        delete=False,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Unassignment:
        """Unassign stage to specific artifact version"""
        self._check_args(name, version, ref, stage)
        if ref:
            ref = self.repo.commit(ref).hexsha
        found_artifact = self.find_artifact(name)
        found_version = found_artifact.find_version(
            name=version, commit_hexsha=ref, raise_if_not_found=True
        )
        if (
            not force
            and found_version
            and found_version.stages
            and all(s != stage for s in found_version.stages)
        ):
            raise WrongArgs(
                f"Stage '{stage}' is not assigned to a version '{found_version.version}'"
            )
        if delete and any([message, author, author_email, simple, force]):
            raise WrongArgs(
                "Deleting a git tag doesn't require any of 'message', 'force', 'simple', 'author' or 'author_email'"
            )
        # TODO: getting tag name as a result and using it
        # is leaking implementation details in base module
        # it's roughly ok to have until we add other implementations
        # beside tag-based assignments
        tag = self.stage_manager.unassign(  # type: ignore
            name,
            stage,
            ref=found_version.commit_hexsha,
            message=message
            or f"Unassigning stage '{stage}' to artifact '{name}' version '{found_version.version}'",
            simple=simple,
            delete=delete,
            author=author,
            author_email=author_email,
        )
        return self._return_event(tag, stdout=stdout)

    def _check_args(self, name, version, ref, stage=None):
        assert_name_is_valid(name)
        if stage is not None:
            self.config.assert_stage(stage)
        if version:
            self._check_version(version)
        if not (version is None) ^ (ref is None):
            raise WrongArgs("One and only one of (version, ref) must be specified.")

    @staticmethod
    def _check_version(version):
        if not SemVer.is_valid(version):
            raise WrongArgs(
                f"Version '{version}' is not valid. Example of valid version: 'v1.0.0'"
            )

    def _return_event(self, tag, stdout) -> TBaseEvent:
        event = self.check_ref(tag)
        if len(event) > 1:
            raise NotImplementedInGTO("Can't process a tag that caused multiple events")
        event = event[0]
        if stdout:
            echo(f"Created git tag '{tag}'")
        return event

    def check_ref(self, ref: str):
        "Find out what was registered/assigned in this ref"
        try:
            if ref.startswith("refs/tags/"):
                ref = ref[len("refs/tags/") :]
            if ref.startswith("refs/heads/"):
                ref = self.repo.commit(ref).hexsha
            # check the ref exists
            _ = self.repo.tags[ref]
            # check the ref follows the GTO format
            name = parse_name(ref)[NAME]
        except (KeyError, ValueError, IndexError):
            logging.info("Provided ref doesn't exist or it is not of GTO format")
            return []
        state = self.get_state()
        return [
            event
            for aname, artifact in state.get_artifacts().items()
            if aname == name
            for event in artifact.get_events()
            # TODO: support matching the shortened commit hashes
            if event.ref == ref
        ]

    def find_commit(self, name, version):
        return self.get_state().find_commit(name, version)

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
        return self.get_state().which(
            name,
            stage,
            raise_if_not_found,
            assignments_per_version=assignments_per_version,
            versions_per_stage=versions_per_stage,
            registered_only=registered_only,
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
