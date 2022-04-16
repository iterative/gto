import logging
from datetime import datetime
from enum import Enum
from typing import FrozenSet, Iterable, Optional, Union

import git
from pydantic import BaseModel

from .base import (
    BaseArtifact,
    BaseManager,
    BasePromotion,
    BaseRegistryState,
    BaseVersion,
)
from .constants import ACTION, NAME, NUMBER, STAGE, TAG, VERSION, Action
from .exceptions import MissingArg, RefNotFound, UnknownAction

ActionSign = {
    Action.REGISTER: "@",
    Action.PROMOTE: "#",
}


def name_tag(
    action: Action,
    name: str,
    version: Optional[str] = None,
    stage: Optional[str] = None,
    repo: Optional[git.Repo] = None,
    simple: bool = False,
):
    if action == Action.REGISTER:
        return f"{name}{ActionSign[action]}{version}"

    if action == Action.PROMOTE:
        if simple:
            return f"{name}{ActionSign[action]}{stage}"
        if repo is None:
            raise MissingArg(arg="repo")
        numbers = []
        for tag in repo.tags:
            parsed = parse_name(tag.name)
            if parsed[ACTION] in (Action.PROMOTE,):
                numbers.append(parsed[NUMBER])
        new_number = max(numbers) + 1 if numbers else 1
        return f"{name}{ActionSign[action]}{stage}-{new_number}"
    raise UnknownAction(action=action)


def parse_name(name: str, raise_on_fail: bool = True):

    if ActionSign[Action.REGISTER] in name:
        name, version = name.split(ActionSign[Action.REGISTER])
        return {
            ACTION: Action.REGISTER,
            NAME: name,
            VERSION: version,
        }

    if ActionSign[Action.PROMOTE] in name:
        name, stage = name.split(ActionSign[Action.PROMOTE])
        result = {
            ACTION: Action.PROMOTE,
            NAME: name,
            STAGE: stage,
        }
        if "-" not in stage:
            return result
        stage, number = stage.split("-")
        result[STAGE] = stage
        result[NUMBER] = int(number)
        return result
    if raise_on_fail:
        raise ValueError(f"Unknown tag name: {name}")
    return {}


class NAME_REFERENCE(Enum):
    TAG = TAG
    NAME = NAME


def parse_name_reference(name: str):
    parsed = parse_name(name, raise_on_fail=False)
    if not parsed:
        return NAME_REFERENCE.NAME, name
    return NAME_REFERENCE.TAG, parsed


class Tag(BaseModel):
    action: Action
    name: str
    version: Optional[str]
    stage: Optional[str]
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
    stage: Optional[str] = None,
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
    if stage:
        tags = [t for t in tags if parse_name(t.name).get(STAGE) == stage]
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
        artifact=mtag.name,
        name=mtag.version,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
        tag=tag.name,
    )


def promotion_from_tag(
    artifact: BaseArtifact, tag: git.Tag, version_required: bool
) -> BasePromotion:
    mtag = parse_tag(tag)
    if version_required:
        version = artifact.find_version(
            commit_hexsha=tag.commit.hexsha, raise_if_not_found=True
        ).name  # type: ignore
    else:
        version = artifact.find_version(commit_hexsha=tag.commit.hexsha)
        if version:
            version = version.name  # type: ignore
        else:
            artifact.add_version(
                BaseVersion(
                    artifact=mtag.name,
                    name=tag.commit.hexsha,
                    creation_date=mtag.creation_date,
                    author=tag.tag.tagger.name,
                    commit_hexsha=tag.commit.hexsha,
                )
            )
            version = tag.commit.hexsha
    return BasePromotion(
        artifact=mtag.name,
        version=version,
        stage=mtag.stage,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
        tag=tag.name,
    )


def index_tag(
    artifact: BaseArtifact, tag: git.Tag, version_required: bool
) -> BaseArtifact:
    mtag = parse_tag(tag)
    if mtag.action == Action.REGISTER:
        artifact.add_version(version_from_tag(tag))
    if mtag.action == Action.PROMOTE:
        artifact.add_promotion(promotion_from_tag(artifact, tag, version_required))
    return artifact


class TagManager(BaseManager):  # pylint: disable=abstract-method
    def update_state(self, state: BaseRegistryState) -> BaseRegistryState:
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        tags = [parse_tag(t) for t in find(repo=self.repo, action=self.actions)]
        for tag in tags:
            state.update_artifact(
                index_tag(
                    state.find_artifact(tag.name, create_new=True),
                    tag.tag,
                    version_required=False,
                )
            )
        return state


class TagVersionManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.REGISTER,))

    def register(self, name, version, ref, message):
        create_tag(
            self.repo,
            name_tag(Action.REGISTER, name, version=version, repo=self.repo),
            ref=ref,
            message=message,
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
            for name, artifact in state.get_artifacts().items()
            for version in artifact.versions
            if name == art_name and version.name == version_name
        }


class TagStageManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE,))

    def promote(self, name, stage, ref, message, simple):
        create_tag(
            self.repo,
            name_tag(Action.PROMOTE, name, stage=stage, repo=self.repo, simple=simple),
            ref=ref,
            message=message,
        )

    def check_ref(self, ref: str, state: BaseRegistryState):
        try:
            tag = self.repo.tags[ref]
            _ = parse_name(ref)[STAGE]
            art_name = parse_name(ref)[NAME]
        except (KeyError, ValueError, IndexError):
            logging.warning(
                "Provided ref doesn't exist or it is not a tag that promotes to an stage"
            )
            return {}
        return {
            name: promotion
            for name, artifact in state.get_artifacts().items()
            for promotion in artifact.stages
            if name == art_name
            and promotion.commit_hexsha == tag.commit.hexsha
            and promotion.creation_date == datetime.fromtimestamp(tag.tag.tagged_date)
        }
