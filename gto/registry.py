import logging
import os
from contextlib import contextmanager
from typing import List, Optional, TypeVar, cast

from funcy import distinct
from pydantic import BaseModel, ConfigDict
from scmrepo.git import Git

from gto.base import (
    Assignment,
    BaseEvent,
    BaseRegistryState,
    Deprecation,
    Deregistration,
    Registration,
    Unassignment,
)
from gto.config import CONFIG_FILE_NAME, RegistryConfig, read_registry_config
from gto.constants import NAME, assert_fullname_is_valid
from gto.exceptions import (
    InvalidTagName,
    NotImplementedInGTO,
    VersionAlreadyRegistered,
    VersionExistsForCommit,
    WrongArgs,
)
from gto.git_utils import RemoteRepoMixin, git_push_tag
from gto.index import EnrichmentManager
from gto.tag import (
    TagArtifactManager,
    TagStageManager,
    TagVersionManager,
    delete_tag,
    parse_name,
)
from gto.ui import echo
from gto.versions import SemVer

TBaseEvent = TypeVar("TBaseEvent", bound=BaseEvent)


class GitRegistry(BaseModel, RemoteRepoMixin):
    scm: Git
    cloned: bool
    artifact_manager: TagArtifactManager
    version_manager: TagVersionManager
    stage_manager: TagStageManager
    enrichment_manager: EnrichmentManager
    config: RegistryConfig
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    @contextmanager
    def from_scm(
        cls,
        scm: Git,
        cloned: bool = False,
        config: Optional[RegistryConfig] = None,
    ):
        if config is None:
            config = read_registry_config(os.path.join(scm.root_dir, CONFIG_FILE_NAME))

        yield cls(
            scm=scm,
            cloned=cloned,
            config=config,
            artifact_manager=TagArtifactManager(scm=scm, config=config),
            version_manager=TagVersionManager(scm=scm, config=config),
            stage_manager=TagStageManager(scm=scm, config=config),
            enrichment_manager=EnrichmentManager(scm=scm, config=config),
        )

    def is_gto_repo(self):
        if self.config.config_file_exists():
            return True
        if self.config.check_index_exist(self.scm.root_dir):
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
        state = self.artifact_manager.update_state(state)
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
        name: Optional[str] = None,
        create_new=False,
        all_branches=False,
        all_commits=False,
    ):
        return self.get_state(
            all_branches=all_branches,
            all_commits=all_commits,
        ).find_artifact(
            name,  # type: ignore
            create_new=create_new,
        )

    def register(  # pylint: disable=too-many-locals  # noqa: C901
        self,
        name,
        rev,
        version=None,
        message=None,
        simple=None,
        force=False,
        bump_major=False,
        bump_minor=False,
        bump_patch=False,
        push=False,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Registration:
        """Register artifact version"""
        assert_fullname_is_valid(name)
        version_args = sum(
            bool(i) for i in (version, bump_major, bump_minor, bump_patch)
        )
        if version_args > 1:
            raise WrongArgs("Need to specify either version or single bump argument")
        rev = self.scm.resolve_rev(rev)
        found_artifact = self.find_artifact(name, create_new=True)
        # check that this commit don't have a version already
        found_version = found_artifact.find_version(commit_hexsha=rev)
        if found_version is not None:
            if not force and found_version.is_registered and found_version.is_active:
                raise VersionExistsForCommit(name, found_version.version)
            if not version:
                version = found_version.version
            elif found_version.version != version:
                raise WrongArgs(
                    f"For this REF you can only register {found_version.version}"
                )
        # if version name is provided, use it
        if version:
            SemVer(version)
            if found_artifact.find_version(name=version) != found_version:
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
            rev,
            message=message or f"Registering artifact {name} version {version}",
            simple=simple,
            author=author,
            author_email=author_email,
        )
        if stdout:
            echo(f"Created git tag '{tag}' that registers version")
        self._push_tag_or_echo_reminder(tag_name=tag, push=push, stdout=stdout)
        return self._return_event(tag)

    def deregister(  # pylint: disable=too-many-locals
        self,
        name,
        rev=None,
        version=None,
        message=None,
        simple=None,
        force=False,
        delete=False,
        push: bool = False,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Deregistration:
        """Deregister artifact version"""
        self._check_args(name, version, rev)
        if rev is not None:
            rev = self.scm.resolve_rev(rev)
        found_artifact = self.find_artifact(name, create_new=True)
        if not force:
            found_version = found_artifact.find_version(
                name=version, commit_hexsha=rev, raise_if_not_found=True
            )
            if not found_version.is_registered:
                raise WrongArgs(
                    f"The version at ref '{found_version.commit_hexsha}' is not registered"
                )
            if not found_version.is_active:
                raise WrongArgs(
                    f"The version at ref '{found_version.commit_hexsha}' was deregistered already"
                )

        found_version = found_artifact.find_version(name=version, commit_hexsha=rev)
        version = version or getattr(found_version, "version", None)
        commit_hexsha = rev or getattr(found_version, "commit_hexsha", None)
        if not (version and commit_hexsha):
            raise WrongArgs("Can't deregister a version that have no git tags")

        if delete:
            tags = distinct(
                [
                    e.tag
                    for e in found_version.get_events(ascending=True)
                    if hasattr(e, "tag")
                ]
            )
            return self._delete_tags(tags, stdout=stdout, push=push)

        tag = self.version_manager.deregister(
            name,
            version,
            found_version.commit_hexsha,
            message=message or f"Deregistering artifact {name} version {version}",
            simple=simple,
            author=author,
            author_email=author_email,
        )
        if stdout:
            echo(f"Created git tag '{tag}' that deregisters version")
        self._push_tag_or_echo_reminder(
            tag_name=tag, push=push, stdout=stdout, delete=delete
        )
        return self._return_event(tag)

    def assign(  # pylint: disable=too-many-locals  # noqa: C901
        self,
        name,
        stage,
        version=None,
        rev=None,
        name_version=None,
        message=None,
        simple=False,
        force=False,
        push: bool = False,
        skip_registration=False,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Assignment:
        """Assign stage to specific artifact version"""
        self._check_args(name, version, rev, stage)
        if name_version:
            self._check_version(name_version)
        if name_version and skip_registration:
            raise WrongArgs(
                "You either need to supply version name or skip registration"
            )
        if rev:
            rev = self.scm.resolve_rev(rev)
        found_artifact = self.find_artifact(name, create_new=True)
        if version:
            found_version = found_artifact.find_version(
                name=version, raise_if_not_found=False
            )
            if not found_version:
                raise WrongArgs(f"Version '{version}' is not registered")
            rev = self.find_commit(name, version)
        else:
            found_version = found_artifact.find_version(commit_hexsha=rev)
            if found_version:
                if name_version:
                    raise WrongArgs(
                        f"Can't register '{SemVer(name_version).version}', since '{found_version.version}' is registered already at this ref"
                    )
            else:
                if not skip_registration:
                    self.register(
                        name,
                        version=name_version,
                        rev=rev,
                        simple=True,
                        stdout=stdout,
                        push=push,
                    )
                found_version = self.find_artifact(name, create_new=True).find_version(
                    commit_hexsha=rev, create_new=True
                )
        if (
            not force
            and found_version
            and found_version.stages
            and any(vstage.stage == stage for vstage in found_version.get_vstages())
        ):
            raise WrongArgs(
                f"Version '{found_version.version}' is already in stage '{stage}'. Use the '--force' flag to create a new Git tag nevertheless."
            )
        # TODO: getting tag name as a result and using it
        # is leaking implementation details in base module
        # it's roughly ok to have until we add other implementations
        # beside tag-based assignments
        tag = self.stage_manager.assign(  # type: ignore
            name,
            stage,
            rev=rev,
            message=message
            or f"Assigning stage {stage} to artifact {name} "
            + (
                f"version {found_version.version}" if found_version else f"commit {rev}"
            ),
            simple=simple,
            author=author,
            author_email=author_email,
        )
        if stdout:
            echo(
                f"Created git tag '{tag}' that assigns stage to version '{found_version.version}'"
            )
        self._push_tag_or_echo_reminder(tag_name=tag, push=push, stdout=stdout)
        return self._return_event(tag)

    def unassign(  # pylint: disable=too-many-locals
        self,
        name,
        stage,
        version=None,
        rev=None,
        message=None,
        simple=False,
        force=False,
        delete=False,
        push: bool = False,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Unassignment:
        """Unassign stage to specific artifact version"""
        self._check_args(name, version, rev, stage)
        if rev:
            rev = self.scm.resolve_rev(rev)
        found_artifact = self.find_artifact(name)
        found_version = found_artifact.find_version(
            name=version, commit_hexsha=rev, raise_if_not_found=True
        )
        if not force and all(s != stage for s in getattr(found_version, "stages", [])):
            raise WrongArgs(
                f"Stage '{stage}' is not assigned to a version '{found_version.version}'"
            )
        if delete:
            tags = distinct(
                [
                    e.tag
                    for e in found_version.get_events(ascending=True)
                    if hasattr(e, "tag") and hasattr(e, "stage") and e.stage == stage
                ]
            )
            return self._delete_tags(tags, push=push, stdout=stdout)

        # TODO: getting tag name as a result and using it
        # is leaking implementation details in base module
        # it's roughly ok to have until we add other implementations
        # beside tag-based assignments
        tag = self.stage_manager.unassign(  # type: ignore
            name,
            stage,
            rev=found_version.commit_hexsha,
            message=message
            or f"Unassigning stage '{stage}' to artifact '{name}' version '{found_version.version}'",
            simple=simple,
            author=author,
            author_email=author_email,
        )
        if stdout:
            echo(
                f"Created git tag '{tag}' that unassigns stage from version '{found_version.version}'"
            )
        self._push_tag_or_echo_reminder(
            tag_name=tag, push=push, stdout=stdout, delete=delete
        )
        return self._return_event(tag)

    def deprecate(
        self,
        name,
        rev=None,
        message=None,
        simple=False,
        force=False,
        delete=False,
        push: bool = False,
        stdout=False,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Optional[Deprecation]:
        """Deprecate artifact"""
        assert_fullname_is_valid(name)
        if force:
            if simple:
                raise WrongArgs("Can't use 'force' with 'simple=True'")
            simple = False
        else:
            if simple is None:
                simple = True
            found_artifact = self.find_artifact(name)
            if not found_artifact.is_active:
                raise WrongArgs("Artifact was deprecated already")
        if delete:
            tags = distinct(
                [
                    e.tag
                    for e in self.find_artifact(name=name).get_events(ascending=True)
                    if hasattr(e, "tag")
                ]
            )
            return self._delete_tags(tags, stdout=stdout, push=push)
        if rev is None:
            if name in self.get_artifacts():
                rev = self.find_artifact(name=name).get_events()[0].commit_hexsha
            else:
                rev = "HEAD"
        tag = self.artifact_manager.deprecate(  # type: ignore
            name,
            rev=rev,
            message=message or f"Deprecating artifact '{name}'",
            simple=simple,
            author=author,
            author_email=author_email,
        )
        if stdout:
            echo(f"Created git tag '{tag}' that deprecates artifact")
        self._push_tag_or_echo_reminder(
            tag_name=tag, push=push, stdout=stdout, delete=delete
        )
        return self._return_event(tag)

    def _check_args(self, name, version, rev, stage=None):
        assert_fullname_is_valid(name)
        if stage is not None:
            self.config.assert_stage(stage)
        if version:
            self._check_version(version)
        if not (version is None) ^ (rev is None):
            raise WrongArgs("One and only one of (version, rev) must be specified.")

    @staticmethod
    def _check_version(version):
        if not SemVer.is_valid(version):
            raise WrongArgs(
                f"Version '{version}' is not valid. Example of valid version: 'v1.0.0'"
            )

    def _return_event(self, tag) -> TBaseEvent:  # type: ignore[type-var]
        event = self.check_ref(tag)
        if len(event) > 1:
            raise NotImplementedInGTO("Can't process a tag that caused multiple events")
        return cast(TBaseEvent, event[0])

    @staticmethod
    def _echo_git_suggestion(tag, delete=False):
        echo("To push the changes upstream, run:")
        echo(f"    git push{' --delete ' if delete else ' '}origin {tag}")

    def _delete_tags(self, tags, stdout, push: bool):
        tags = list(tags)
        for tag in tags:
            delete_tag(self.scm, tag)
            if stdout:
                echo(f"Deleted git tag '{tag}'")
            self._push_tag_or_echo_reminder(
                tag_name=tag,
                push=push,
                stdout=stdout,
                delete=True,
            )

    def check_ref(self, ref: str) -> List[BaseEvent]:
        "Find out what was registered/assigned in this ref"
        try:
            name = ""
            tag_name = ref[len("refs/tags/") :] if ref.startswith("refs/tags/") else ref
            if self.scm.get_tag(tag_name):
                # check the ref follows the GTO format
                name = parse_name(tag_name)[NAME]
        except InvalidTagName:
            pass
        if not name:
            logging.info(f"Ref '{ref}' doesn't exist or it is not of GTO format")
            return []
        state = self.get_state()
        return [
            event
            for aname, artifact in state.get_artifacts().items()
            if aname == name
            for event in artifact.get_events()
            # TODO: support matching the shortened commit hashes
            if event.ref == tag_name
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
        return self.config.stages

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

    def _push_tag_or_echo_reminder(
        self, tag_name: str, push: bool, stdout: bool, delete: bool = False
    ) -> None:
        if push or self.cloned:
            if stdout:
                echo(
                    f"Running `git push{' --delete ' if delete else ' '}origin {tag_name}`"
                )
            git_push_tag(
                scm=self.scm,
                tag_name=tag_name,
                delete=delete,
            )
            if stdout:
                echo(
                    f"Successfully {'deleted' if delete else 'pushed'} git tag {tag_name} on remote."
                )
        elif stdout:
            self._echo_git_suggestion(tag_name, delete=delete)
