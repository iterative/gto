import logging
from datetime import datetime
from typing import FrozenSet, Iterable, Optional, Union

import git
from pydantic import BaseModel

from gto.index import Artifact

from .base import BaseArtifact, BaseLabel, BaseManager, BaseRegistryState, BaseVersion
from .constants import ACTION, LABEL, NAME, NUMBER, VERSION, Action
from .exceptions import MissingArg, RefNotFound, UnknownAction

ActionSign = {
    Action.REGISTER: "@",
    Action.DEPRECATE: "@!",
    Action.PROMOTE: "#",
}


def name_tag(
    action: Action,
    name: str,
    version: Optional[str] = None,
    label: Optional[str] = None,
    repo: Optional[git.Repo] = None,
):
    if action in (Action.REGISTER, Action.DEPRECATE):
        return f"{name}{ActionSign[action]}{version}"

    if action in (Action.PROMOTE,):
        if repo is None:
            raise MissingArg(arg="repo")
        numbers = []
        for tag in repo.tags:
            parsed = parse_name(tag.name)
            if parsed[ACTION] in (Action.PROMOTE,):
                numbers.append(parsed[NUMBER])
        new_number = max(numbers) + 1 if numbers else 1
        return f"{name}{ActionSign[action]}{label}-{new_number}"
    raise UnknownAction(action=action)


def parse_name(name: str, raise_on_fail: bool = True):

    # order does matter if you take into account ActionSign values
    for action in (Action.DEPRECATE, Action.REGISTER):
        if ActionSign[action] in name:
            name, version = name.split(ActionSign[action])
            return {
                ACTION: action,
                NAME: name,
                VERSION: version,
            }

    # order does matter if you take into account ActionSign values
    for action in (Action.PROMOTE,):
        if ActionSign[action] in name:
            name, label = name.split(ActionSign[action])
            label, number = label.split("-")
            return {
                ACTION: action,
                NAME: name,
                LABEL: label,
                NUMBER: int(number),
            }
    if raise_on_fail:
        raise ValueError(f"Unknown tag name: {name}")
    return {}


class Tag(BaseModel):
    action: Action
    name: str
    version: Optional[str]
    label: Optional[str]
    creation_date: datetime
    tag: git.Tag

    class Config:
        arbitrary_types_allowed = True


def parse_tag(tag: git.Tag):
    return Tag(
        tag=tag,
        creation_date=datetime.fromtimestamp(tag.tag.tagged_date),
        **parse_name(tag.name),
    )


def find(
    action: Union[Action, FrozenSet[Action]] = None,
    name: Optional[str] = None,
    version: Optional[str] = None,
    label: Optional[str] = None,
    repo: Optional[git.Repo] = None,
    sort: str = "by_time",
    tags: Optional[Iterable[git.Tag]] = None,
):
    if isinstance(action, Action):
        action = frozenset([action])
    if tags is None:
        if repo is None:
            raise MissingArg(arg="repo")
        tags = [t for t in repo.tags if parse_name(t.name, raise_on_fail=False)]
    if action:
        tags = [t for t in tags if parse_name(t.name)[ACTION] in action]
    if name:
        tags = [t for t in tags if parse_name(t.name).get(NAME) == name]
    if version:
        tags = [t for t in tags if parse_name(t.name).get(VERSION) == version]
    if label:
        tags = [t for t in tags if parse_name(t.name).get(LABEL) == label]
    if sort == "by_time":
        tags = sorted(tags, key=lambda t: t.tag.tagged_date)
    else:
        raise NotImplementedError(f"Unknown sort: {sort}")
    return tags


def create_tag(repo, name, ref, message):
    if all(c.hexsha != ref for c in repo.iter_commits()):
        raise RefNotFound(ref=ref)

    repo.create_tag(
        name,
        ref=ref,
        message=message,
    )


def version_from_tag(artifact: Artifact, tag: git.Tag) -> BaseVersion:
    mtag = parse_tag(tag)
    return BaseVersion(
        artifact=artifact,
        name=mtag.version,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
    )


def label_from_tag(artifact: BaseArtifact, tag: git.Tag) -> BaseLabel:
    mtag = parse_tag(tag)
    registered_version = artifact.find_version(commit_hexsha=tag.commit.hexsha)
    if registered_version:
        version = None
        deprecated_date = None
        version_name = registered_version.name  # type: ignore
    else:
        deprecated_versions = artifact.find_version(
            commit_hexsha=tag.commit.hexsha,
            skip_deprecated=False,
            raise_if_not_found=True,
            allow_multiple=True,
        )
        version = sorted(
            [v for v in deprecated_versions if v.creation_date <= mtag.creation_date],  # type: ignore
            key=lambda v: v.creation_date,  # type: ignore
        )[-1]
        version_name = version.name  # type: ignore
        deprecated_date = version.creation_date  # type: ignore
    return BaseLabel(
        artifact=artifact.commits[tag.commit.hexsha],
        version=version_name,
        name=mtag.label,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
        deprecated_date=deprecated_date,
    )


def index_tag(artifact: BaseArtifact, tag: git.Tag) -> BaseArtifact:
    mtag = parse_tag(tag)
    hexsha = mtag.tag.commit.hexsha
    if hexsha not in artifact.commits:
        # issue a warning that we're ignoring a tag,
        # because artifact wasn't registered in that commit?
        return artifact
    if mtag.action == Action.REGISTER:
        artifact.versions.append(version_from_tag(artifact.commits[hexsha], tag))
    if mtag.action == Action.DEPRECATE:
        artifact.find_version(mtag.version).deprecated_date = mtag.creation_date  # type: ignore
    if mtag.action == Action.PROMOTE:
        artifact.labels.append(label_from_tag(artifact, tag))
    return artifact


class TagManager(BaseManager):  # pylint: disable=abstract-method
    def update_state(self, state: BaseRegistryState) -> BaseRegistryState:
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        tags = [parse_tag(t) for t in find(repo=self.repo, action=self.actions)]
        for tag in tags:
            state.artifacts[tag.name] = index_tag(state.artifacts[tag.name], tag.tag)
        return state


class TagVersionManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.REGISTER, Action.DEPRECATE))

    def register(self, name, version, ref, message):
        create_tag(
            self.repo,
            name_tag(Action.REGISTER, name, version=version, repo=self.repo),
            ref=ref,
            message=message,
        )

    def deprecate(self, name, version):
        """Unregister artifact version"""
        # TODO: search in self, move to base
        tags = find(
            action=Action.REGISTER,
            name=name,
            version=version,
            repo=self.repo,
        )
        if len(tags) != 1:
            raise ValueError(f"Found {len(tags)} git tags for {name} version {version}")
        create_tag(
            self.repo,
            name_tag(Action.DEPRECATE, name, version=version, repo=self.repo),
            ref=tags[0].commit.hexsha,
            message=f"Unregistering {name} version {version}",
        )

    def check_ref(self, ref: str, state: BaseRegistryState):
        try:
            _ = self.repo.tags[ref]
            art_name = parse_name(ref)[NAME]
            version_name = parse_name(ref)[VERSION]
        except (KeyError, ValueError, IndexError):
            logging.warning(
                "Provided ref doesn't exist or it is not a tag that registers a version"
            )
            return {}
        return {
            name: version
            for name in state.artifacts
            for version in state.artifacts[name].versions
            if name == art_name and version.name == version_name
        }


class TagEnvManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE,))

    def promote(self, name, label, ref, message):
        create_tag(
            self.repo,
            name_tag(Action.PROMOTE, name, label=label, repo=self.repo),
            ref=ref,
            message=message,
        )

    def check_ref(self, ref: str, state: BaseRegistryState):
        try:
            tag = self.repo.tags[ref]
            _ = parse_name(ref)[LABEL]
            art_name = parse_name(ref)[NAME]
        except (KeyError, ValueError, IndexError):
            logging.warning(
                "Provided ref doesn't exist or it is not a tag that promotes to an environment"
            )
            return {}
        return {
            name: label
            for name in state.artifacts
            for label in state.artifacts[name].labels
            if name == art_name
            and label.commit_hexsha == tag.commit.hexsha
            and label.creation_date == datetime.fromtimestamp(tag.tag.tagged_date)
        }
