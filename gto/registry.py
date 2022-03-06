import os
from typing import Union

import click
import git
from git import Repo
from pydantic import BaseModel

from gto.base import BaseManager, BaseObject, BaseRegistryState
from gto.config import CONFIG_FILE, RegistryConfig
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
    config: RegistryConfig

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_repo(cls, repo=Union[str, Repo], config=None):
        if isinstance(repo, str):
            repo = git.Repo(repo)
        if config is None:
            config = RegistryConfig(
                CONFIG_FILE=os.path.join(repo.working_dir, CONFIG_FILE)
            )

        return cls(
            repo=repo,
            version_manager=config.VERSION_MANAGERS_MAPPING[config.VERSION_BASE](
                repo=repo
            ),
            env_manager=config.ENV_MANAGERS_MAPPING[config.ENV_BASE](repo=repo),
            config=config,
        )

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

    def register(self, name, ref, version=None, bump=None):
        """Register object version"""
        ref = self.repo.commit(ref).hexsha
        # TODO: add the same check for other actions, to promote and etc
        # also we need to check integrity of the index+state
        self.index.assert_existence(name, ref)
        found_object = self.state.find_object(name)
        # check that this commit don't have a version already
        found_version = found_object.find_version(
            commit_hexsha=ref, skip_unregistered=True
        )
        if found_version is not None:
            raise VersionExistsForCommit(name, found_version.name)
        # if version name is provided, use it
        if version:
            if (
                found_object.find_version(name=version, skip_unregistered=False)
                is not None
            ):
                raise VersionAlreadyRegistered(version)
            if (
                found_object.versions
                and self.config.versions_class(version)
                < found_object.latest_version.name
            ):
                raise VersionIsOld(
                    latest=found_object.latest_version.name, suggested=version
                )
        # if version name wasn't provided but there were some, bump the last one
        elif found_object.versions:
            version = (
                self.config.versions_class(
                    self.state.find_object(name).latest_version.name
                )
                .bump(**({"part": bump} if bump else {}))
                .version
            )
        # if no versions exist, use the minimal version possible
        else:
            version = self.config.versions_class.get_minimal().version
        self.version_manager.register(
            name,
            version,
            ref,
            message=f"Registering object {name} version {version}",
        )
        return self.state.find_object(name).find_version(
            name=version, raise_if_not_found=True
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
        self.config.assert_env(label)
        if not (promote_version is None) ^ (promote_ref is None):
            raise ValueError("One and only one of (version, commit) must be specified.")
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
                self.register(name, version=name_version, ref=promote_ref)
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
        """Return label active in specific env"""
        return self.state.which(name, label, raise_if_not_found)

    def latest(self, name: str):
        """Return latest version for object"""
        return self.state.find_object(name).latest_version
