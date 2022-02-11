import logging
from datetime import datetime
from typing import FrozenSet, Iterable, Optional, Union

import git
from pydantic import BaseModel

from .base import BaseLabel, BaseManager, BaseObject, BaseRegistryState, BaseVersion
from .constants import ACTION, LABEL, NAME, NUMBER, VERSION, Action
from .exceptions import MissingArg, RefNotFound, UnknownAction
from .index import RepoIndexState


def name_tag(
    action: Action,
    name: str,
    version: Optional[str] = None,
    label: Optional[str] = None,
    repo: Optional[git.Repo] = None,
):
    if action in (Action.REGISTER, Action.UNREGISTER):
        return f"{name}-{action.value}-{version}"

    if action in (Action.PROMOTE, Action.DEMOTE):
        if repo is None:
            raise MissingArg(arg="repo")
        basename = f"{name}-{Action.PROMOTE.value}-{label}"
        if existing_names := [c.name for c in repo.tags if c.name.startswith(basename)]:
            last_number = 1 + max(int(n[len(basename) + 1 :]) for n in existing_names)
        else:
            last_number = 1
        return f"{name}-{action.value}-{label}-{last_number}"
    raise UnknownAction(action=action.value)


def add_dashes(string: str):
    return f"-{string}-"


def parse_name(name: str, raise_on_fail: bool = True):

    for action in (Action.REGISTER, Action.UNREGISTER):
        if add_dashes(action.value) in name:
            name, version = name.split(add_dashes(action.value))
            return {
                ACTION: action,
                NAME: name,
                VERSION: version,
            }

    for action in (Action.PROMOTE, Action.DEMOTE):
        if add_dashes(action.value) in name:
            name, label = name.split(add_dashes(action.value))
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


class ObjectTag(BaseModel):
    action: Action
    name: str
    version: Optional[str]
    label: Optional[str]
    creation_date: datetime
    tag: git.Tag

    class Config:
        arbitrary_types_allowed = True


def parse_tag(tag: git.Tag):
    return ObjectTag(
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


def version_from_tag(tag: git.Tag) -> BaseVersion:
    mtag = parse_tag(tag)
    return BaseVersion(
        object=mtag.name,
        name=mtag.version,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
    )


def label_from_tag(tag: git.Tag, obj: BaseObject) -> BaseLabel:
    mtag = parse_tag(tag)
    return BaseLabel(
        object=mtag.name,
        version=obj.find_version(
            commit_hexsha=tag.commit.hexsha, raise_if_not_found=True
        ).name,  # type: ignore
        name=mtag.label,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
    )


def index_tag(obj: BaseObject, tag: git.Tag) -> BaseObject:
    mtag = parse_tag(tag)
    if mtag.action == Action.REGISTER:
        obj.versions.append(version_from_tag(tag))
    if mtag.action == Action.UNREGISTER:
        obj.find_version(mtag.version).unregistered_date = mtag.creation_date  # type: ignore
    if mtag.action == Action.PROMOTE:
        obj.labels.append(label_from_tag(tag, obj))
    if mtag.action == Action.DEMOTE:
        if mtag.label not in obj.latest_labels:
            raise ValueError(f"Active label '{mtag.label}' not found")
        obj.latest_labels[mtag.label].unregistered_date = mtag.creation_date  # type: ignore
    return obj


class TagManager(BaseManager):  # pylint: disable=abstract-method
    def update_state(
        self, state: BaseRegistryState, index: RepoIndexState
    ) -> BaseRegistryState:
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        tags = [parse_tag(t) for t in find(repo=self.repo, action=self.actions)]
        for tag in tags:
            if tag.name not in state.objects:
                state.objects[tag.name] = BaseObject(
                    name=tag.name, versions=[], labels=[]
                )
            state.objects[tag.name] = index_tag(state.objects[tag.name], tag.tag)
        return state


class TagVersionManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.REGISTER, Action.UNREGISTER))

    def register(self, name, version, ref, message):
        create_tag(
            self.repo,
            name_tag(Action.REGISTER, name, version=version, repo=self.repo),
            ref=ref,
            message=message,
        )

    def unregister(self, name, version):
        """Unregister object version"""
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
            name_tag(Action.UNREGISTER, name, version=version, repo=self.repo),
            ref=tags[0].commit.hexsha,
            message=f"Unregistering {name} version {version}",
        )

    def parse_ref(self, ref: str, state: BaseRegistryState):
        try:
            version_name = parse_name(ref)[VERSION]
        except (KeyError, ValueError):
            logging.warning("Provided ref is not a tag that registers a version")
            return {}
        return {
            name: version
            for name in state.objects
            for version in state.objects[name].versions
            if version.name == version_name
        }


class TagEnvManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE, Action.DEMOTE))

    def promote(self, name, label, ref, message):
        create_tag(
            self.repo,
            name_tag(Action.PROMOTE, name, label=label, repo=self.repo),
            ref=ref,
            message=message,
        )

    def demote(self, name, label, message):
        # TODO: search in self, move to base
        promoted_tag = find(
            action=Action.PROMOTE,
            name=name,
            label=label,
            repo=self.repo,
        )[-1]
        create_tag(
            self.repo,
            name_tag(Action.DEMOTE, name, label=label, repo=self.repo),
            ref=promoted_tag.commit.hexsha,
            message=message,
        )

    def parse_ref(self, ref: str, state: BaseRegistryState):
        try:
            parse_name(ref)[LABEL]
        except (KeyError, ValueError):
            logging.warning("Provided ref is not a tag that promotes to an environment")

        tag = self.repo.tag(ref)
        return {
            name: label
            for name in state.objects
            for label in state.objects[name].labels
            if label.commit_hexsha == tag.commit.hexsha
            and label.creation_date == datetime.fromtimestamp(tag.tag.tagged_date)
        }
