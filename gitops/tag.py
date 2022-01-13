from typing import Optional

import git
import pandas as pd

from .base import BaseLabel, BaseModel, BaseRegistry, BaseVersion

REGISTER = "register"
UNREGISTER = "unregister"
PROMOTE = "promote"
DEMOTE = "demote"


def name(action, model, version=None, label=None, repo=None):
    if action == REGISTER:
        return f"model-{model}-{REGISTER}-{version}"
    if action == UNREGISTER:
        return f"model-{model}-{UNREGISTER}-{version}"

    basename = f"model-{model}-{PROMOTE}-{label}"
    existing_names = [c.name for c in repo.tags if c.name.startswith(basename)]
    if existing_names:
        last_number = 1 + max(int(n[len(basename) + 1 :]) for n in existing_names)
    else:
        last_number = 1
    if action == PROMOTE:
        return f"{basename}-{last_number}"
    if action == DEMOTE:
        return f"model-{model}-{DEMOTE}-{label}-{last_number}"
    raise ValueError(f"Unknown action: {action}")


def parse(name, raise_on_fail=True):
    def add_dashes(x):
        return f"-{x}-"

    if isinstance(name, git.Tag):
        name = name.name
    if add_dashes(UNREGISTER) in name:
        model, version = name.split(add_dashes(UNREGISTER))
        model = model[len("model-") :]
        return dict(action=UNREGISTER, model=model, version=version)
    if add_dashes(REGISTER) in name:
        model, version = name.split(add_dashes(REGISTER))
        model = model[len("model-") :]
        return dict(action=REGISTER, model=model, version=version)
    if add_dashes(PROMOTE) in name:
        model, label = name.split(add_dashes(PROMOTE))
        model = model[len("model-") :]
        label, number = label.split("-")
        return dict(action=PROMOTE, model=model, label=label, number=number)
    if add_dashes(DEMOTE) in name:
        model, label = name.split(add_dashes(DEMOTE))
        model = model[len("model-") :]
        label, number = label.split("-")
        return dict(action=DEMOTE, model=model, label=label, number=number)
    if raise_on_fail:
        raise ValueError(f"Unknown tag name: {name}")
    else:
        return dict()


def find(
    action=None,
    model=None,
    version=None,
    label=None,
    repo=None,
    sort="by_time",
    tags=None,
):
    if tags is None:
        tags = [t for t in repo.tags if parse(t.name, raise_on_fail=False)]
    if action:
        tags = [t for t in tags if parse(t.name)["action"] == action]
    if model:
        tags = [t for t in tags if parse(t.name).get("model") == model]
    if version:
        tags = [t for t in tags if parse(t.name).get("version") == version]
    if label:
        tags = [t for t in tags if parse(t.name).get("label") == label]
    if sort == "by_time":
        tags = sorted(tags, key=lambda t: t.tag.tagged_date)
    return tags


def find_registered(model, repo):
    """Return all registered versions for model"""
    register_tags = find(action=REGISTER, model=model, repo=repo)
    unregister_tags = find(action=UNREGISTER, model=model, repo=repo)
    return [
        r
        for r in register_tags
        if not any(
            r.commit.hexsha == u.commit.hexsha
            and parse(r.name)["model"] == parse(u.name)["model"]
            and parse(r.name)["version"] == parse(u.name)["version"]
            for u in unregister_tags
        )
    ]


def find_latest(model, repo):
    """Return latest registered version for model"""
    return find_registered(model, repo)[-1]


def find_promoted(model, label, repo):
    """Return all promoted versions for model"""
    promote_tags = find(action=PROMOTE, model=model, label=label, repo=repo)
    demote_tags = find(action=DEMOTE, model=model, label=label, repo=repo)
    # what we do if someone promotes and demotes one model+commit several times?
    return [
        p
        for p in promote_tags
        if not any(
            p.commit.hexsha == d.commit.hexsha
            and parse(p.name)["model"] == parse(d.name)["model"]
            and parse(p.name)["label"] == parse(d.name)["label"]
            for d in demote_tags
        )
    ]


def find_current_promoted(model, label, repo):
    """Return latest promoted version for model"""
    return find_promoted(model, label, repo)[-1]


def find_version(model, label, repo):
    """Return version of model with specific label active"""
    tags = find(action=PROMOTE, model=model, label=label, repo=repo)
    version_sha = tags[-1].commit.hexsha

    # if this commit has been tagged several times (model-v1, model-v2)
    # you may have several tags with different versions
    # so when you PROMOTE model, you won't know which version you've promoted
    # v1 or v2
    tags = find(action=REGISTER, model=model, repo=repo)
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
        mtag = ModelTag(tag)
        return cls(
            mtag.model,
            mtag.version,
            mtag.creation_date,
            tag.tag.tagger.name,
            tag.commit.hexsha,
            tag.name,
        )


class TagBasedLabel(BaseLabel):
    @classmethod
    def from_tag(cls, tag: git.Tag) -> None:
        mtag = ModelTag(tag)
        version_candidates = [
            t
            for t in find(action=REGISTER, model=mtag.model, repo=tag.repo)
            if t.commit.hexsha == tag.commit.hexsha
        ]
        if len(version_candidates) != 1:
            # TODO: resolve this
            raise ValueError(
                f"Found {len(version_candidates)} tags for model '{mtag.model}' label '{mtag.label}'"
            )
        version = ModelTag(version_candidates[0]).version
        return cls(
            mtag.model,
            version,
            mtag.label,
            mtag.creation_date,
            tag.tag.tagger.name,
            tag.commit.hexsha,
            tag.name,
        )


class ModelTag:
    model: str
    version: Optional[str]
    label: Optional[str]
    tag: git.Tag

    def __init__(self, tag) -> None:
        parsed = parse(tag.name)
        self.action = parsed["action"]
        self.model = parsed["model"]
        self.version = parsed.get("version")
        self.label = parsed.get("label")
        self.creation_date = pd.Timestamp(tag.tag.tagged_date * 10 ** 9)
        self.tag = tag


class TagBasedModel(BaseModel):
    def index_tag(self, tag: git.Tag) -> None:
        mtag = ModelTag(tag)
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

    Model = TagBasedModel

    @property
    def models(self):
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        tags = [ModelTag(t) for t in find(repo=self.repo)]
        models = {}
        for t in tags:
            if t.model not in models:
                models[t.model] = TagBasedModel(t.model, [], [])
            models[t.model].index_tag(t.tag)
        return [models[k] for k in models]

    @property
    def _labels(self):
        return [
            parse(t.name)["label"]
            for t in find(repo=self.repo)
            if "label" in parse(t.name)
        ]

    def _register(self, model, version, ref, message):
        create_tag(
            self.repo,
            name(REGISTER, model, version=version, repo=self.repo),
            ref=ref,
            message=message,
        )

    def unregister(self, model, version):
        """Unregister model version"""
        tags = find(action=REGISTER, model=model, version=version, repo=self.repo)
        if len(tags) != 1:
            raise ValueError(
                f"Found {len(tags)} git tags for model {model} version {version}"
            )
        create_tag(
            self.repo,
            name(UNREGISTER, model, version=version, repo=self.repo),
            ref=tags[0].commit.hexsha,
            message=f"Unregistering model {model} version {version}",
        )

    def find_commit(self, model, version):
        return self.repo.tags[name(REGISTER, model, version=version)].commit.hexsha

    def _promote(self, model, label, ref, message):
        create_tag(
            self.repo,
            name(PROMOTE, model, label=label, repo=self.repo),
            ref=ref,
            message=message,
        )

    def _demote(self, model, label, message):
        promoted_tag = find(action=PROMOTE, model=model, label=label, repo=self.repo)[
            -1
        ]
        create_tag(
            self.repo,
            name(DEMOTE, model, label=label, repo=self.repo),
            ref=promoted_tag.commit.hexsha,
            message=message,
        )
