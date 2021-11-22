from typing import List, Optional

import git
import pandas as pd

from .tag import DEMOTE, PROMOTE, REGISTER, UNREGISTER, find, name, parse


class Label:
    model: str
    version: str
    name: str
    unregistered_date: Optional[pd.Timestamp] = None

    def __init__(
        self, model, version, label, creation_date, author, commit_hexsha, tag_name
    ) -> None:
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
            mtag.creation_date,
            tag.tag.tagger.name,
            tag.commit.hexsha,
            tag.name,
        )


class Version:
    model: str
    name: str
    creation_date: str
    unregistered_date: Optional[pd.Timestamp] = None

    def __init__(
        self, model, version, creation_date, author, commit_hexsha, tag_name
    ) -> None:
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
            mtag.creation_date,
            tag.tag.tagger.name,
            tag.commit.hexsha,
            tag.name,
        )


class Model:
    name: str
    versions: List[Version]
    labels: List[Label]

    def __init__(self, name, versions, labels) -> None:
        self.name = name
        self._versions = versions
        self.labels = labels

    def index_tag(self, tag: git.Tag) -> None:
        mtag = ModelTag(tag)
        if mtag.action == REGISTER:
            self.versions.append(Version.from_tag(tag))
        if mtag.action == UNREGISTER:
            self.find_version(mtag.version).unregistered_date = mtag.creation_date
        if mtag.action == PROMOTE:
            self.labels.append(Label.from_tag(tag))
        if mtag.action == DEMOTE:
            if mtag.label not in self.latest_labels:
                raise ValueError(f"Active label '{mtag.label}' not found")
            self.latest_labels[mtag.label].unregistered_date = mtag.creation_date

    @property
    def unique_labels(self):
        return {l.name for l in self.labels}

    def __repr__(self) -> str:
        versions = ", ".join(f"'{v.name}'" for v in self.versions)
        labels = ", ".join(f"'{l}'" for l in self.unique_labels)
        return f"Model(versions=[{versions}], labels=[{labels}])"

    @property
    def latest_version(self) -> str:
        return sorted(
            filter(lambda x: x.unregistered_date is None, self.versions),
            key=lambda x: x.creation_date,
        )[-1].name

    @property
    def latest_labels(self) -> List[Label]:
        labels = {}
        for l in self.unique_labels:
            found = sorted(
                filter(
                    lambda x: x.name == l
                    and x.unregistered_date is None
                    and self.find_version(x.version) is not None,
                    self.labels,
                ),
                key=lambda x: x.creation_date,
            )
            labels[l] = found[-1] if found else None
        return labels

    @property
    def versions(self):
        return self._versions

    def find_version(
        self,
        name: str = None,
        commit_hexsha: str = None,
        raise_if_not_found=False,
        skip_unregistered=True,
    ) -> Optional[Version]:
        versions = [
            v
            for v in self.versions
            if (v.name == name if name else True)
            and (v.commit_hexsha == commit_hexsha if commit_hexsha else True)
            and (v.unregistered_date is None if skip_unregistered else True)
        ]
        if raise_if_not_found:
            assert len(versions) == 1, (
                f"{len(versions)} versions of model {self.name} found"
                + ", skipping unregistered"
                if skip_unregistered
                else ""
            )
            return versions[0]

        assert len(versions) <= 1, (
            f"{len(versions)} versions of model {self.name} found"
            + ", skipping unregistered"
            if skip_unregistered
            else ""
        )
        return versions[0] if versions else None


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


class Registry:
    repo: git.Repo
    models: List[Model]

    def __init__(self, repo: git.Repo = git.Repo(".")):
        self.repo = repo

    @property
    def models(self):
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        tags = [ModelTag(t) for t in find(repo=self.repo)]
        models = {}
        for t in tags:
            if t.model not in models:
                models[t.model] = Model(t.model, [], [])
            models[t.model].index_tag(t.tag)
        return [models[k] for k in models]

    def find_model(self, model, allow_new=False):
        models = [m for m in self.models if m.name == model]
        if allow_new and not models:
            return Model(model, [], [])
        assert len(models) == 1, f"Found {len(models)} models with name {model}"
        return models[0]

    @property
    def labels(self):
        tags = [
            parse(t.name)["label"]
            for t in find(repo=self.repo)
            if "label" in parse(t.name)
        ]
        return sorted(set(tags))

    def register(self, model, version):
        """Register model version"""
        found_version = self.find_model(model, allow_new=True).find_version(
            version, skip_unregistered=False
        )
        if found_version is not None:
            raise ValueError(
                f"Version '{version}' already was registered.\n"
                "Even if it was unregistered, you must use another name to avoid confusion."
            )
        found_version = self.find_model(model, allow_new=True).find_version(
            None, self.repo.active_branch.commit.hexsha, skip_unregistered=True
        )
        if found_version is not None:
            raise ValueError(
                f"The model {model} was already registered in this commit with version '{found_version.name}'\n"
            )
        self.repo.create_tag(
            name(REGISTER, model, version=version, repo=self.repo),
            message=f"Registering model {model} version {version}",
        )

    def unregister(self, model, version):
        """Unregister model version"""
        tags = find(action=REGISTER, model=model, version=version, repo=self.repo)
        if len(tags) != 1:
            raise ValueError(
                f"Found {len(tags)} tags for model {model} version {version}"
            )
        self.repo.create_tag(
            name(UNREGISTER, model, version=version, repo=self.repo),
            ref=tags[0].commit.hexsha,
            message=f"Unregistering model {model} version {version}",
        )

    # def unregister(self, model, version):
    #     """Unregister model version"""
    #     self.find_model(model)

    def promote(self, model, version, label):
        """Assign label to specific model version"""
        # check that version exists
        self.find_model(model).find_version(version, raise_if_not_found=True)
        version_hexsha = self.repo.tags[
            name(REGISTER, model, version=version)
        ].commit.hexsha
        self.repo.create_tag(
            name(PROMOTE, model, label=label, repo=self.repo),
            ref=version_hexsha,
            message=f"Promoting model {model} version {version} to label {label}",
        )

    def demote(self, model, label):
        """De-promote model from given label"""
        # TODO: check if label wasn't demoted already
        assert (
            self.find_model(model).latest_labels.get(label) is not None
        ), f"No active label '{label}' was found for model '{model}'"
        promoted_tag = find(action=PROMOTE, model=model, label=label, repo=self.repo)[
            -1
        ]
        self.repo.create_tag(
            name(DEMOTE, model, label=label, repo=self.repo),
            ref=promoted_tag.commit.hexsha,
            message=f"Demoting model {model} from label {label}",
        )

    def which(self, model, label, raise_if_not_found=True):
        """Return version of model with specific label active"""
        latest_labels = self.find_model(model).latest_labels
        if label in latest_labels:
            return latest_labels[label].version
        if raise_if_not_found:
            raise ValueError(f"Label {label} not found for model {model}")
