from typing import List, Optional

import git
import pandas as pd

from tag import parse, find, REGISTER, UNREGISTER, PROMOTE, DEMOTE, name


class Label:
    model: str
    version: str
    name: str
    def __init__(self, model, version, label, creation_date, author, commit_hexsha, tag_name) -> None:
        self.model = model
        self.version = version
        self.name = label
        self.creation_date = creation_date
        self.author = author
        self.commit_hexsha = commit_hexsha
        self.tag_name = tag_name

    def __repr__(self) -> str:
        return f"Label('{self.model}', '{self.version}', '{self.name}')"

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
                f"Found {len(version_candidates)} tags for model {mtag.model} version {mtag.version}\n"
                "   How to know which version was registered by this tag if there are multiple versions?\n"
                "   Take the latest version which existed before registration?\n"
                "   Still can be confusing"
            )
        version = ModelTag(version_candidates[0]).version
        return cls(
            mtag.model,
            version,
            mtag.label, 
            pd.Timestamp(tag.tag.tagged_date * 10 ** 9),
            tag.tag.tagger.name,
            tag.commit.hexsha[:7],
            tag.name,
        )


class Version:
    model: str
    name: str
    creation_date: str

    def __init__(self, model, version, creation_date, author, commit_hexsha, tag_name) -> None:
        self.model = model
        self.name = version
        self.creation_date = creation_date
        self.author = author
        self.commit_hexsha = commit_hexsha
        self.tag_name = tag_name

    def __repr__(self) -> str:
        return f"Version('{self.model}', '{self.name}')"

    @classmethod
    def from_tag(cls, tag):
        mtag = ModelTag(tag)
        return cls(
            mtag.model,
            mtag.version,
            pd.Timestamp(tag.tag.tagged_date * 10 ** 9),
            tag.tag.tagger.name,
            tag.commit.hexsha[:7],
            tag.name,
        )


class Model:
    name: str
    versions: List[Version]
    labels: List[Label]
    def __init__(self, name, versions, labels) -> None:
        self.name = name
        self.versions = versions
        self.labels = labels
        
    @property
    def unique_labels(self):
        return {l.name for l in self.labels}

    def __repr__(self) -> str:
        versions = ", ".join(f"'{v.name}'" for v in self.versions)
        labels = ", ".join(f"'{l}'" for l in self.unique_labels)
        return f"Model(versions=[{versions}], labels=[{labels}])"

    @property
    def latest_version(self) -> str:
        return self.versions[-1].name

    @property
    def latest_labels(self) -> List[Label]:
        return {
            l: sorted(filter(lambda x: x.name == l, self.labels), key=lambda x: x.creation_date)[-1]
            for l in self.unique_labels
        }



class ModelTag:
    model: str
    version: Optional[str]
    label: Optional[str]
    tag: git.Tag
    def __init__(self, tag) -> None:
        parsed = parse(tag.name)
        self.model = parsed["model"]
        self.version = parsed.get("version")
        self.label = parsed.get("label")
        self.tag = tag


class Registry:
    repo: git.Repo
    models: List[Model]
    def __init__(self, repo: git.Repo = git.Repo(".")):
        self.repo = repo
    
    @property
    def models(self):
        tags = [ModelTag(t) for t in find(repo=self.repo)]
        models = {}
        for t in tags:
            if t.model not in models:
                models[t.model] = Model(t.model, [], [])
            if t.version is not None:
                models[t.model].versions += [Version.from_tag(t.tag)]
            if t.label is not None:
                models[t.model].labels += [Label.from_tag(t.tag)]
        return [models[k] for k in models]

    @property
    def labels(self):
        tags = [parse(t.name)["label"] for t in find(repo=self.repo) if "label" in parse(t.name)]
        return sorted(set(tags))

    def register(self, model, version):
        """Register model version"""
        self.repo.create_tag(
            name(REGISTER, model, version=version, repo=self.repo),
            message=f"Registering model {model} version {version}",
        )

    def unregister(self, model, version):
        """Unregister model version"""
        tags = find(action=REGISTER, model=model, version=version, repo=self.repo)
        if len(tags) != 1:
            raise ValueError(f"Found {len(tags)} tags for model {model} version {version}")
        self.repo.create_tag(
            name(UNREGISTER, model, version=version, repo=self.repo),
            ref=tags[0].commit.hexsha,
            message=f"Unregistering model {model} version {version}",
        )

    def promote(self, model, version, label):
        """Assign label to specific model version"""
        version_hexsha = self.repo.tags[
            name(REGISTER, model, version=version)
        ].commit.hexsha
        self.repo.create_tag(
            name(PROMOTE, model, label=label, repo=self.repo),
            ref=version_hexsha,
            message=f"Promoting model {model} version {version} to label {label}",
        )

    def which(self, model, label):
        """Return version of model with specific label active"""
        tags = find(action=PROMOTE, model=model, label=label, repo=self.repo)
        version_sha = tags[-1].commit.hexsha

        # if this commit has been tagged several times (model-v1, model-v2)
        # you may have several tags with different versions
        # so when you PROMOTE model, you won't know which version you've promoted
        # v1 or v2
        tags = find(action=REGISTER, model=model, repo=self.repo)
        tags = [t for t in tags if t.commit.hexsha == version_sha]
        return parse(tags[-1].name)["version"]

    def demote(self, model, label):
        """De-promote model from given label"""
        # TODO: check if label wasn't demoted already
        promoted_tag = find(action=PROMOTE, model=model, label=label, repo=self.repo)[-1]
        self.repo.create_tag(
            name(DEMOTE, model, label=label, repo=self.repo),
            rev=promoted_tag.commit.hexsha,
            message=f"Demoting model {model} from label {label}",
        )
