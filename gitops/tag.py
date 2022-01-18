from typing import Optional

import git
import pandas as pd

from .base import BaseLabel, BaseObject, BaseRegistry, BaseVersion
from .constants import (
    ACTION,
    CATEGORY,
    DEMOTE,
    LABEL,
    NUMBER,
    OBJECT,
    PROMOTE,
    REGISTER,
    UNREGISTER,
    VERSION,
)


def name_tag(action, category, object, version=None, label=None, repo=None):
    if action == REGISTER:
        return f"{category}-{object}-{REGISTER}-{version}"
    if action == UNREGISTER:
        return f"{category}-{object}-{UNREGISTER}-{version}"

    basename = f"{category}-{object}-{PROMOTE}-{label}"
    existing_names = [c.name for c in repo.tags if c.name.startswith(basename)]
    if existing_names:
        last_number = 1 + max(int(n[len(basename) + 1 :]) for n in existing_names)
    else:
        last_number = 1
    if action == PROMOTE:
        return f"{basename}-{last_number}"
    if action == DEMOTE:
        return f"{category}-{object}-{DEMOTE}-{label}-{last_number}"
    raise ValueError(f"Unknown action: {action}")


def parse_name(name, raise_on_fail=True):
    def add_dashes(string):
        return f"-{string}-"

    def deduce_category(object):
        i = object.index("-")
        category, object = object[:i], object[i + 1 :]
        return category, object

    if isinstance(name, git.Tag):
        name = name.name
    if add_dashes(UNREGISTER) in name:
        object, version = name.split(add_dashes(UNREGISTER))
        category, object = deduce_category(object)
        return {
            CATEGORY: category,
            ACTION: UNREGISTER,
            OBJECT: object,
            VERSION: version,
        }
    if add_dashes(REGISTER) in name:
        object, version = name.split(add_dashes(REGISTER))
        category, object = deduce_category(object)
        return {CATEGORY: category, ACTION: REGISTER, OBJECT: object, VERSION: version}
    if add_dashes(PROMOTE) in name:
        object, label = name.split(add_dashes(PROMOTE))
        category, object = deduce_category(object)
        label, number = label.split("-")
        return {
            CATEGORY: category,
            ACTION: PROMOTE,
            OBJECT: object,
            LABEL: label,
            NUMBER: int(number),
        }
    if add_dashes(DEMOTE) in name:
        object, label = name.split(add_dashes(DEMOTE))
        category, object = deduce_category(object)
        label, number = label.split("-")
        return {
            CATEGORY: category,
            ACTION: DEMOTE,
            OBJECT: object,
            LABEL: label,
            NUMBER: int(number),
        }
    if raise_on_fail:
        raise ValueError(f"Unknown tag name: {name}")
    return {}


def find(
    action=None,
    category=None,
    object=None,
    version=None,
    label=None,
    repo=None,
    sort="by_time",
    tags=None,
):
    if tags is None:
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


def find_registered(category, object, repo):
    """Return all registered versions for object"""
    register_tags = find(category=category, action=REGISTER, object=object, repo=repo)
    unregister_tags = find(
        category=category, action=UNREGISTER, object=object, repo=repo
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


def find_latest(category, object, repo):
    """Return latest registered version for object"""
    return find_registered(category, object, repo)[-1]


def find_promoted(category, object, label, repo):
    """Return all promoted versions for object"""
    promote_tags = find(
        category=category, action=PROMOTE, object=object, label=label, repo=repo
    )
    demote_tags = find(
        category=category, action=DEMOTE, object=object, label=label, repo=repo
    )
    # what we do if someone promotes and demotes one object+commit several times?
    return [
        p
        for p in promote_tags
        if not any(
            p.commit.hexsha == d.commit.hexsha
            and parse_name(p.name)[CATEGORY] == parse_name(d.name)[CATEGORY]
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
        category=category, action=PROMOTE, object=object, label=label, repo=repo
    )
    version_sha = tags[-1].commit.hexsha

    # if this commit has been tagged several times (object-v1, object-v2)
    # you may have several tags with different versions
    # so when you PROMOTE object, you won't know which version you've promoted
    # v1 or v2
    tags = find(category=category, action=REGISTER, object=object, repo=repo)
    tags = [t for t in tags if t.commit.hexsha == version_sha]
    return parse_name(tags[-1].name)["version"]


def create_tag(repo, name, ref, message):
    assert any(
        c.hexsha == ref for c in repo.iter_commits()
    ), "Can't find provided hexsha in repo history"

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
        self.action = parsed[ACTION]
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
            version=mtag.version,
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
                action=REGISTER,
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
        if mtag.action == REGISTER:
            self.versions.append(TagBasedVersion.from_tag(tag))
        if mtag.action == UNREGISTER:
            self.find_version(mtag.version).unregistered_date = mtag.creation_date  # type: ignore
        if mtag.action == PROMOTE:
            self.labels.append(TagBasedLabel.from_tag(tag))
        if mtag.action == DEMOTE:
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
                objects[tag.object] = TagBasedObject(tag.category, tag.object, [], [])
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
            name_tag(REGISTER, category, object, version=version, repo=self.repo),
            ref=ref,
            message=message,
        )

    def unregister(self, category, object, version):
        """Unregister object version"""
        tags = find(
            action=REGISTER,
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
            name_tag(UNREGISTER, category, object, version=version, repo=self.repo),
            ref=tags[0].commit.hexsha,
            message=f"Unregistering {category} {object} version {version}",
        )

    def find_commit(self, category, object, version):
        return self.repo.tags[
            name_tag(REGISTER, category, object, version=version)
        ].commit.hexsha

    def _promote(self, category, object, label, ref, message):
        create_tag(
            self.repo,
            name_tag(PROMOTE, category, object, label=label, repo=self.repo),
            ref=ref,
            message=message,
        )

    def _demote(self, category, object, label, message):
        promoted_tag = find(
            action=PROMOTE,
            category=category,
            object=object,
            label=label,
            repo=self.repo,
        )[-1]
        create_tag(
            self.repo,
            name_tag(DEMOTE, category, object, label=label, repo=self.repo),
            ref=promoted_tag.commit.hexsha,
            message=message,
        )
