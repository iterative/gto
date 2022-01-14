from typing import Optional

import git
import pandas as pd

from .base import BaseLabel, BaseObject, BaseRegistry, BaseVersion

REGISTER = "register"
UNREGISTER = "unregister"
PROMOTE = "promote"
DEMOTE = "demote"

ACTION = "action"
CATEGORY = "category"
OBJECT = "object"
VERSION = "version"
LABEL = "label"
NUMBER = "number"


def name(action, object, version=None, label=None, repo=None):
    if action == REGISTER:
        return f"model-{object}-{REGISTER}-{version}"
    if action == UNREGISTER:
        return f"model-{object}-{UNREGISTER}-{version}"

    basename = f"model-{object}-{PROMOTE}-{label}"
    existing_names = [c.name for c in repo.tags if c.name.startswith(basename)]
    if existing_names:
        last_number = 1 + max(int(n[len(basename) + 1 :]) for n in existing_names)
    else:
        last_number = 1
    if action == PROMOTE:
        return f"{basename}-{last_number}"
    if action == DEMOTE:
        return f"model-{object}-{DEMOTE}-{label}-{last_number}"
    raise ValueError(f"Unknown action: {action}")


def parse(name, raise_on_fail=True):
    def add_dashes(x):
        return f"-{x}-"

    if isinstance(name, git.Tag):
        name = name.name
    if add_dashes(UNREGISTER) in name:
        object, version = name.split(add_dashes(UNREGISTER))
        object = object[len("model-") :]
        return {ACTION: UNREGISTER, OBJECT: object, VERSION: version}
    if add_dashes(REGISTER) in name:
        object, version = name.split(add_dashes(REGISTER))
        object = object[len("model-") :]
        return {ACTION: REGISTER, OBJECT: object, VERSION: version}
    if add_dashes(PROMOTE) in name:
        object, label = name.split(add_dashes(PROMOTE))
        object = object[len("model-") :]
        label, number = label.split("-")
        return {ACTION: PROMOTE, OBJECT: object, LABEL: label, NUMBER: int(number)}
    if add_dashes(DEMOTE) in name:
        object, label = name.split(add_dashes(DEMOTE))
        object = object[len("model-") :]
        label, number = label.split("-")
        return {ACTION: DEMOTE, OBJECT: object, LABEL: label, NUMBER: int(number)}
    if raise_on_fail:
        raise ValueError(f"Unknown tag name: {name}")
    else:
        return dict()


def find(
    action=None,
    object=None,
    version=None,
    label=None,
    repo=None,
    sort="by_time",
    tags=None,
):
    if tags is None:
        tags = [t for t in repo.tags if parse(t.name, raise_on_fail=False)]
    if action:
        tags = [t for t in tags if parse(t.name)[ACTION] == action]
    if object:
        tags = [t for t in tags if parse(t.name).get(OBJECT) == object]
    if version:
        tags = [t for t in tags if parse(t.name).get(VERSION) == version]
    if label:
        tags = [t for t in tags if parse(t.name).get(LABEL) == label]
    if sort == "by_time":
        tags = sorted(tags, key=lambda t: t.tag.tagged_date)
    else:
        raise NotImplementedError(f"Unknown sort: {sort}")
    return tags


def find_registered(object, repo):
    """Return all registered versions for object"""
    register_tags = find(action=REGISTER, object=object, repo=repo)
    unregister_tags = find(action=UNREGISTER, object=object, repo=repo)
    return [
        r
        for r in register_tags
        if not any(
            r.commit.hexsha == u.commit.hexsha
            and parse(r.name)[OBJECT] == parse(u.name)[OBJECT]
            and parse(r.name)[VERSION] == parse(u.name)[VERSION]
            for u in unregister_tags
        )
    ]


def find_latest(object, repo):
    """Return latest registered version for model"""
    return find_registered(object, repo)[-1]


def find_promoted(object, label, repo):
    """Return all promoted versions for object"""
    promote_tags = find(action=PROMOTE, object=object, label=label, repo=repo)
    demote_tags = find(action=DEMOTE, object=object, label=label, repo=repo)
    # what we do if someone promotes and demotes one object+commit several times?
    return [
        p
        for p in promote_tags
        if not any(
            p.commit.hexsha == d.commit.hexsha
            and parse(p.name)[OBJECT] == parse(d.name)[OBJECT]
            and parse(p.name)[LABEL] == parse(d.name)[LABEL]
            for d in demote_tags
        )
    ]


def find_current_promoted(object, label, repo):
    """Return latest promoted version for object"""
    return find_promoted(object, label, repo)[-1]


def find_version(object, label, repo):
    """Return version of object with specific label active"""
    tags = find(action=PROMOTE, object=object, label=label, repo=repo)
    version_sha = tags[-1].commit.hexsha

    # if this commit has been tagged several times (object-v1, object-v2)
    # you may have several tags with different versions
    # so when you PROMOTE object, you won't know which version you've promoted
    # v1 or v2
    tags = find(action=REGISTER, object=object, repo=repo)
    tags = [t for t in tags if t.commit.hexsha == version_sha]
    return parse(tags[-1].name)["version"]


def create_tag(repo, name, ref, message):
    assert any(
        c.hexsha == ref for c in repo.iter_commits()
    ), "Can't find provided hexsha in repo history"

    repo.create_tag(
        name,
        ref=ref,
        message=message,
    )


class TagBasedVersion(BaseVersion):
    @classmethod
    def from_tag(cls, tag):
        mtag = ObjectTag(tag)
        return cls(
            mtag.object,
            mtag.version,
            mtag.creation_date,
            tag.tag.tagger.name,
            tag.commit.hexsha,
            tag.name,
        )


class TagBasedLabel(BaseLabel):
    @classmethod
    def from_tag(cls, tag: git.Tag) -> None:
        mtag = ObjectTag(tag)
        version_candidates = [
            t
            for t in find(action=REGISTER, object=mtag.object, repo=tag.repo)
            if t.commit.hexsha == tag.commit.hexsha
        ]
        if len(version_candidates) != 1:
            # TODO: resolve this
            raise ValueError(
                f"Found {len(version_candidates)} tags for object '{mtag.object}' label '{mtag.label}'"
            )
        version = ObjectTag(version_candidates[0]).version
        return cls(
            mtag.object,
            version,
            mtag.label,
            mtag.creation_date,
            tag.tag.tagger.name,
            tag.commit.hexsha,
            tag.name,
        )


class ObjectTag:
    object: str
    version: Optional[str]
    label: Optional[str]
    tag: git.Tag

    def __init__(self, tag) -> None:
        parsed = parse(tag.name)
        self.action = parsed[ACTION]
        self.object = parsed[OBJECT]
        self.version = parsed.get(VERSION)
        self.label = parsed.get(LABEL)
        self.creation_date = pd.Timestamp(tag.tag.tagged_date * 10 ** 9)
        self.tag = tag


class TagBasedObject(BaseObject):
    def index_tag(self, tag: git.Tag) -> None:
        mtag = ObjectTag(tag)
        if mtag.action == REGISTER:
            self.versions.append(TagBasedVersion.from_tag(tag))
        if mtag.action == UNREGISTER:
            self.find_version(mtag.version).unregistered_date = mtag.creation_date
        if mtag.action == PROMOTE:
            self.labels.append(TagBasedLabel.from_tag(tag))
        if mtag.action == DEMOTE:
            if mtag.label not in self.latest_labels:
                raise ValueError(f"Active label '{mtag.label}' not found")
            self.latest_labels[mtag.label].unregistered_date = mtag.creation_date


class TagBasedRegistry(BaseRegistry):

    Object = TagBasedObject

    @property
    def objects(self):
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        tags = [ObjectTag(t) for t in find(repo=self.repo)]
        objects = {}
        for t in tags:
            if t.object not in objects:
                objects[t.object] = TagBasedObject(t.object, [], [])
            objects[t.object].index_tag(t.tag)
        return [objects[k] for k in objects]

    @property
    def _labels(self):
        return [
            parse(t.name)[LABEL] for t in find(repo=self.repo) if LABEL in parse(t.name)
        ]

    def _register(self, object, version, ref, message):
        create_tag(
            self.repo,
            name(REGISTER, object, version=version, repo=self.repo),
            ref=ref,
            message=message,
        )

    def unregister(self, object, version):
        """Unregister object version"""
        tags = find(action=REGISTER, object=object, version=version, repo=self.repo)
        if len(tags) != 1:
            raise ValueError(
                f"Found {len(tags)} git tags for object {object} version {version}"
            )
        create_tag(
            self.repo,
            name(UNREGISTER, object, version=version, repo=self.repo),
            ref=tags[0].commit.hexsha,
            message=f"Unregistering object {object} version {version}",
        )

    def find_commit(self, object, version):
        return self.repo.tags[name(REGISTER, object, version=version)].commit.hexsha

    def _promote(self, object, label, ref, message):
        create_tag(
            self.repo,
            name(PROMOTE, object, label=label, repo=self.repo),
            ref=ref,
            message=message,
        )

    def _demote(self, object, label, message):
        promoted_tag = find(action=PROMOTE, object=object, label=label, repo=self.repo)[
            -1
        ]
        create_tag(
            self.repo,
            name(DEMOTE, object, label=label, repo=self.repo),
            ref=promoted_tag.commit.hexsha,
            message=message,
        )
