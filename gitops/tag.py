from datetime import datetime
from typing import FrozenSet, Iterable, List, Optional, Union

import git
from pydantic import BaseModel

from gitops.exceptions import MissingArg, RefNotFound, UnknownAction

from .base import BaseLabel, BaseManager, BaseObject, BaseRegistryState, BaseVersion
from .constants import ACTION, CATEGORY, LABEL, NUMBER, OBJECT, VERSION, Action


def name_tag(
    action: Action,
    category: str,
    object: str,
    version: Optional[str] = None,
    label: Optional[str] = None,
    repo: Optional[git.Repo] = None,
):
    if action in (Action.REGISTER, Action.UNREGISTER):
        return f"{category}-{object}-{action.value}-{version}"

    if action in (Action.PROMOTE, Action.DEMOTE):
        if repo is None:
            raise MissingArg(arg="repo")
        basename = f"{category}-{object}-{Action.PROMOTE.value}-{label}"
        existing_names = [c.name for c in repo.tags if c.name.startswith(basename)]
        if existing_names:
            last_number = 1 + max(int(n[len(basename) + 1 :]) for n in existing_names)
        else:
            last_number = 1
        return f"{category}-{object}-{action.value}-{label}-{last_number}"
    raise UnknownAction(action=action.value)


def add_dashes(string: str):
    return f"-{string}-"


def parse_name(name: str, raise_on_fail: bool = True):
    def deduce_category(string: str):
        i = string.index("-")
        category, object = string[:i], string[i + 1 :]
        return category, object

    for action in (Action.REGISTER, Action.UNREGISTER):
        if add_dashes(action.value) in name:
            object, version = name.split(add_dashes(action.value))
            category, object = deduce_category(object)
            return {
                CATEGORY: category,
                ACTION: action,
                OBJECT: object,
                VERSION: version,
            }

    for action in (Action.PROMOTE, Action.DEMOTE):
        if add_dashes(action.value) in name:
            object, label = name.split(add_dashes(action.value))
            category, object = deduce_category(object)
            label, number = label.split("-")
            return {
                CATEGORY: category,
                ACTION: action,
                OBJECT: object,
                LABEL: label,
                NUMBER: int(number),
            }
    if raise_on_fail:
        raise ValueError(f"Unknown tag name: {name}")
    return {}


class ObjectTag(BaseModel):
    action: Action
    category: str
    object: str
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
    action: Union[Action, List[Action]] = None,
    category: Optional[str] = None,
    object: Optional[str] = None,
    version: Optional[str] = None,
    label: Optional[str] = None,
    repo: Optional[git.Repo] = None,
    sort: str = "by_time",
    tags: Optional[Iterable[git.Tag]] = None,
):
    if isinstance(action, Action):
        action = [action]
    if tags is None:
        if repo is None:
            raise MissingArg(arg="repo")
        tags = [t for t in repo.tags if parse_name(t.name, raise_on_fail=False)]
    if category:
        tags = [t for t in tags if parse_name(t.name)[CATEGORY] == category]
    if action:
        tags = [t for t in tags if parse_name(t.name)[ACTION] in action]
    if object:
        tags = [t for t in tags if parse_name(t.name).get(OBJECT) == object]
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
        category=mtag.category,
        object=mtag.object,
        name=mtag.version,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
    )


def label_from_tag(tag: git.Tag) -> BaseLabel:
    mtag = parse_tag(tag)
    version_candidates = [
        t
        for t in find(
            category=mtag.category,
            action=Action.REGISTER,
            object=mtag.object,
            repo=tag.repo,
        )
        if t.commit.hexsha == tag.commit.hexsha
    ]
    if len(version_candidates) != 1:
        # TODO: resolve this
        raise ValueError(
            f"Found {len(version_candidates)} tags for {mtag.category} '{mtag.object}' label '{mtag.label}'"
        )
    version = parse_tag(version_candidates[0]).version
    return BaseLabel(
        category=mtag.category,
        object=mtag.object,
        version=version,
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
        obj.labels.append(label_from_tag(tag))
    if mtag.action == Action.DEMOTE:
        if mtag.label not in obj.latest_labels:
            raise ValueError(f"Active label '{mtag.label}' not found")
        obj.latest_labels[mtag.label].unregistered_date = mtag.creation_date  # type: ignore
    return obj


class TagManager(BaseManager):
    def update_state(self, state):
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        tags = [parse_tag(t) for t in find(repo=self.repo, action=self.actions)]
        objects = state.objects
        for tag in tags:
            # add category to this check?
            if tag.object not in objects:
                objects[tag.object] = BaseObject(
                    category=tag.category, name=tag.object, versions=[], labels=[]
                )
            objects[tag.object] = index_tag(objects[tag.object], tag.tag)
        return BaseRegistryState(objects=list(objects.values()))


class TagVersionManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.REGISTER, Action.UNREGISTER))

    def _register(self, category, object, version, ref, message):
        create_tag(
            self.repo,
            name_tag(
                Action.REGISTER, category, object, version=version, repo=self.repo
            ),
            ref=ref,
            message=message,
        )

    def _unregister(self, category, object, version):
        """Unregister object version"""
        # TODO: search in self, move to base
        tags = find(
            action=Action.REGISTER,
            category=category,
            object=object,
            version=version,
            repo=self.repo,
        )
        if len(tags) != 1:
            raise ValueError(
                f"Found {len(tags)} git tags for {category} {object} version {version}"
            )
        create_tag(
            self.repo,
            name_tag(
                Action.UNREGISTER, category, object, version=version, repo=self.repo
            ),
            ref=tags[0].commit.hexsha,
            message=f"Unregistering {category} {object} version {version}",
        )


class TagEnvManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE, Action.DEMOTE))

    def _promote(self, category, object, label, ref, message):
        create_tag(
            self.repo,
            name_tag(Action.PROMOTE, category, object, label=label, repo=self.repo),
            ref=ref,
            message=message,
        )

    def _demote(self, category, object, label, message):
        # TODO: search in self, move to base
        promoted_tag = find(
            action=Action.PROMOTE,
            category=category,
            object=object,
            label=label,
            repo=self.repo,
        )[-1]
        create_tag(
            self.repo,
            name_tag(Action.DEMOTE, category, object, label=label, repo=self.repo),
            ref=promoted_tag.commit.hexsha,
            message=message,
        )
