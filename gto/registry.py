import click
import git
from pydantic import BaseModel

from gto.base import BaseManager, BaseObject, BaseRegistryState
from gto.config import CONFIG
from gto.exceptions import (
    NoActiveLabel,
    VersionAlreadyRegistered,
    VersionExistsForCommit,
    VersionIsOld,
)
from gto.index import RepoIndexManager


class GitRegistry(BaseModel):
    repo: git.Repo
    version_manager: BaseManager
    env_manager: BaseManager

    class Config:
        arbitrary_types_allowed = True

    @property
    def index(self):
        return RepoIndexManager(repo=self.repo)

    @property
    def state(self):
        index = self.index.object_centric_representation()
        state = BaseRegistryState(
            objects={
                name: BaseObject(name=name, versions=[], labels=[]) for name in index
            }
        )
        state = self.version_manager.update_state(state, index)
        state = self.env_manager.update_state(state, index)
        state.sort()
        return state

    def register(self, name, version, ref):
        """Register object version"""
        ref = self.repo.commit(ref).hexsha
        # TODO: add the same check for other actions, to promote and etc
        # also we need to check integrity of the index+state
        self.index.assert_existence(name, ref)
        found_object = self.state.find_object(name)
        found_version = found_object.find_version(name=version, skip_unregistered=False)
        if found_version is not None:
            raise VersionAlreadyRegistered(version)
        found_version = found_object.find_version(
            commit_hexsha=ref, skip_unregistered=True
        )
        if found_version is not None:
            raise VersionExistsForCommit(name, found_version.name)
        if (
            found_object.versions
            and CONFIG.versions_class(version) < found_object.latest_version
        ):
            raise VersionIsOld(latest=found_object.latest_version, suggested=version)
        self.version_manager.register(
            name,
            version,
            ref,
            message=f"Registering object {name} version {version}",
        )

    def unregister(self, name, version):
        return self.version_manager.unregister(name, version)

    def promote(
        self,
        name,
        label,
        promote_version=None,
        promote_ref=None,
        name_version=None,
    ):
        """Assign label to specific object version"""
        CONFIG.assert_env(label)
        if promote_version is None and promote_ref is None:
            raise ValueError("Either version or commit must be specified")
        if promote_version is not None and promote_ref is not None:
            raise ValueError("Only one of version or commit must be specified")
        if promote_ref:
            promote_ref = self.repo.commit(promote_ref).hexsha
        if promote_ref:
            self.index.assert_existence(name, promote_ref)
        found_object = self.state.find_object(name)
        if promote_version is not None:
            found_version = found_object.find_version(
                name=promote_version, raise_if_not_found=True
            )
            promote_ref = self.find_commit(name, promote_version)
        else:
            found_version = found_object.find_version(commit_hexsha=promote_ref)
            if found_version is None:
                if name_version is None:
                    last_version = self.state.find_object(name).latest_version
                    promote_version = CONFIG.versions_class(last_version).bump().version
                self.register(name, name_version, ref=promote_ref)
                click.echo(
                    f"Registered new version '{promote_version}' of '{name}' at commit '{promote_ref}'"
                )
        self.env_manager.promote(
            name,
            label,
            ref=promote_ref,
            message=f"Promoting {name} version {promote_version} to label {label}",
        )
        return {"version": promote_version}

    def demote(self, name, label):
        """De-promote object from given label"""
        # TODO: check if label wasn't demoted already
        if self.state.find_object(name).latest_labels.get(label) is None:
            raise NoActiveLabel(label=label, name=name)
        return self.env_manager.demote(
            name,
            label,
            message=f"Demoting {name} from label {label}",
        )

    def check_ref(self, ref: str):
        "Find out what was registered/promoted in this ref"
        return {
            "version": self.version_manager.check_ref(ref, self.state),
            "env": self.env_manager.check_ref(ref, self.state),
        }

    def find_commit(self, name, version):
        return self.state.find_commit(name, version)

    def which(self, name, label, raise_if_not_found=True):
        """Return version of object with specific label active"""
        return self.state.which(name, label, raise_if_not_found)

    def latest(self, name: str):
        """Return latest version for object"""
        return self.state.find_object(name).latest_version
