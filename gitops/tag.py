from typing import Iterable, Optional, Union

import git
import pandas as pd

from gitops.exceptions import MissingArg, RefNotFound, UnknownAction

from .base import BaseLabel, BaseObject, BaseRegistry, BaseVersion
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


def parse_name(name: Union[str, git.Tag], raise_on_fail: bool = True):
    def add_dashes(string):
        return f"-{string}-"

    def deduce_category(object):
        i = object.index("-")
        category, object = object[:i], object[i + 1 :]
        return category, object

    if isinstance(name, git.Tag):
        name = name.name

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


def find(
    action: Action = None,
    category: Optional[str] = None,
    object: Optional[str] = None,
    version: Optional[str] = None,
    label: Optional[str] = None,
    repo: Optional[git.Repo] = None,
    sort: str = "by_time",
    tags: Optional[Iterable[git.Tag]] = None,
):
    if tags is None:
        if repo is None:
            raise MissingArg(arg="repo")
        tags = [t for t in repo.tags if parse_name(t.name, raise_on_fail=False)]
    if category:
        tags = [t for t in tags if parse_name(t.name)[CATEGORY] == category]
    if action:
        tags = [t for t in tags if parse_name(t.name)[ACTION] == action]
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


def find_registered(category: str, object: str, repo: str):
    """Return all registered versions for object"""
    register_tags = find(
        category=category, action=Action.REGISTER, object=object, repo=repo
    )
    unregister_tags = find(
        category=category, action=Action.UNREGISTER, object=object, repo=repo
    )
    return [
        r
        for r in register_tags
        if not any(
            r.commit.hexsha == u.commit.hexsha
            and parse_name(r.name)[CATEGORY] == parse_name(u.name)[CATEGORY]
            and parse_name(r.name)[OBJECT] == parse_name(u.name)[OBJECT]
            and parse_name(r.name)[VERSION] == parse_name(u.name)[VERSION]
            for u in unregister_tags
        )
    ]


def find_latest(category: str, object: str, repo: str):
    """Return latest registered version for object"""
    return find_registered(category, object, repo)[-1]


def find_promoted(category: str, object: str, label: str, repo: str):
    """Return all promoted versions for object"""
    promote_tags = find(
        category=category, action=Action.PROMOTE, object=object, label=label, repo=repo
    )
    demote_tags = find(
        category=category, action=Action.DEMOTE, object=object, label=label, repo=repo
    )
    # what we do if someone promotes and demotes one object+commit several times?
    return [
        p
        for p in promote_tags
        if not any(
            p.commit.hexsha == d.commit.hexsha
            and parse_name(p.name)[CATEGORY] == d.name[CATEGORY]
            and parse_name(p.name)[OBJECT] == parse_name(d.name)[OBJECT]
            and parse_name(p.name)[LABEL] == parse_name(d.name)[LABEL]
            for d in demote_tags
        )
    ]


def find_current_promoted(category, object, label, repo):
    """Return latest promoted version for object"""
    return find_promoted(category, object, label, repo)[-1]


def find_version(category, object, label, repo):
    """Return version of object with specific label active"""
    tags = find(
        category=category, action=Action.PROMOTE, object=object, label=label, repo=repo
    )
    version_sha = tags[-1].commit.hexsha

    # if this commit has been tagged several times (object-v1, object-v2)
    # you may have several tags with different versions
    # so when you PROMOTE object, you won't know which version you've promoted
    # v1 or v2
    tags = find(category=category, action=Action.REGISTER, object=object, repo=repo)
    tags = [t for t in tags if t.commit.hexsha == version_sha]
    return parse_name(tags[-1].name)["version"]


def create_tag(repo, name, ref, message):
    if all(c.hexsha != ref for c in repo.iter_commits()):
        raise RefNotFound(ref=ref)

    repo.create_tag(
        name,
        ref=ref,
        message=message,
    )


class ObjectTag:
    object: str
    version: Optional[str]
    label: Optional[str]
    tag: git.Tag

    def __init__(self, tag) -> None:
        parsed = parse_name(tag.name)
        self.action = Action(parsed[ACTION])
        self.category = parsed[CATEGORY]
        self.object = parsed[OBJECT]
        self.version = parsed.get(VERSION)
        self.label = parsed.get(LABEL)
        self.creation_date = pd.Timestamp(tag.tag.tagged_date * 10 ** 9)
        self.tag = tag


class TagBasedVersion(BaseVersion):
    @classmethod
    def from_tag(cls, tag):
        mtag = ObjectTag(tag)
        return cls(
            category=mtag.category,
            object=mtag.object,
            name=mtag.version,
            creation_date=mtag.creation_date,
            author=tag.tag.tagger.name,
            commit_hexsha=tag.commit.hexsha,
            tag_name=tag.name,
        )


class TagBasedLabel(BaseLabel):
    @classmethod
    def from_tag(cls, tag: git.Tag) -> "TagBasedLabel":
        mtag = ObjectTag(tag)
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
        version = ObjectTag(version_candidates[0]).version
        return cls(
            category=mtag.category,
            object=mtag.object,
            version=version,
            name=mtag.label,
            creation_date=mtag.creation_date,
            author=tag.tag.tagger.name,
            commit_hexsha=tag.commit.hexsha,
            tag_name=tag.name,
        )


class TagBasedObject(BaseObject):
    def index_tag(self, tag: git.Tag) -> None:
        mtag = ObjectTag(tag)
        if mtag.action == Action.REGISTER:
            self.versions.append(TagBasedVersion.from_tag(tag))
        if mtag.action == Action.UNREGISTER:
            self.find_version(mtag.version).unregistered_date = mtag.creation_date  # type: ignore
        if mtag.action == Action.PROMOTE:
            self.labels.append(TagBasedLabel.from_tag(tag))
        if mtag.action == Action.DEMOTE:
            if mtag.label not in self.latest_labels:
                raise ValueError(f"Active label '{mtag.label}' not found")
            self.latest_labels[mtag.label].unregistered_date = mtag.creation_date  # type: ignore


class TagBasedRegistry(BaseRegistry):

    Object = TagBasedObject  # type: ignore

    @property
    def objects(self):
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        tags = [ObjectTag(t) for t in find(repo=self.repo)]
        objects = {}
        for tag in tags:
            # add category to this check?
            if tag.object not in objects:
                objects[tag.object] = TagBasedObject(
                    category=tag.category, name=tag.object, versions=[], labels=[]
                )
            objects[tag.object].index_tag(tag.tag)
        return objects.values()

    @property
    def _labels(self):
        return [
            parse_name(t.name)[LABEL]
            for t in find(repo=self.repo)
            if LABEL in parse_name(t.name)
        ]

    def _register(self, category, object, version, ref, message):
        create_tag(
            self.repo,
            name_tag(
                Action.REGISTER, category, object, version=version, repo=self.repo
            ),
            ref=ref,
            message=message,
        )

    def unregister(self, category, object, version):
        """Unregister object version"""
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

    def find_commit(self, category, object, version):
        return self.repo.tags[
            name_tag(Action.REGISTER, category, object, version=version)
        ].commit.hexsha

    def _promote(self, category, object, label, ref, message):
        create_tag(
            self.repo,
            name_tag(Action.PROMOTE, category, object, label=label, repo=self.repo),
            ref=ref,
            message=message,
        )

    def _demote(self, category, object, label, message):
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
