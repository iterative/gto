import logging
from datetime import datetime
from typing import FrozenSet, Iterable, Optional, Union

import git
from pydantic import BaseModel

from gto.index import Artifact

from .base import (
    BaseArtifact,
    BaseManager,
    BasePromotion,
    BaseRegistryState,
    BaseVersion,
)
from .constants import ACTION, NAME, NUMBER, STAGE, VERSION, Action
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
):
    if action == Action.REGISTER:
        return f"{name}{ActionSign[action]}{version}"

    if action == Action.PROMOTE:
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
        stage, number = stage.split("-")
        return {
            ACTION: Action.PROMOTE,
            NAME: name,
            STAGE: stage,
            NUMBER: int(number),
        }
    if raise_on_fail:
        raise ValueError(f"Unknown tag name: {name}")
    return {}


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


def version_from_tag(artifact: Artifact, tag: git.Tag) -> BaseVersion:
    mtag = parse_tag(tag)
    return BaseVersion(
        artifact=artifact,
        name=mtag.version,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
    )


def promotion_from_tag(artifact: BaseArtifact, tag: git.Tag) -> BasePromotion:
    mtag = parse_tag(tag)
    version = artifact.find_version(
        commit_hexsha=tag.commit.hexsha, raise_if_not_found=True
    )
    return BasePromotion(
        artifact=artifact.commits[tag.commit.hexsha],
        version=version.name,  # type: ignore
        stage=mtag.stage,
        creation_date=mtag.creation_date,
        author=tag.tag.tagger.name,
        commit_hexsha=tag.commit.hexsha,
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
    if mtag.action == Action.PROMOTE:
        artifact.add_promotion(promotion_from_tag(artifact, tag))
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
            for name in state.artifacts
            for version in state.artifacts[name].versions
            if name == art_name and version.name == version_name
        }


class TagStageManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.PROMOTE,))

    def promote(self, name, stage, ref, message):
        create_tag(
            self.repo,
            name_tag(Action.PROMOTE, name, stage=stage, repo=self.repo),
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
            for name in state.artifacts
            for promotion in state.artifacts[name].stages
            if name == art_name
            and promotion.commit_hexsha == tag.commit.hexsha
            and promotion.creation_date == datetime.fromtimestamp(tag.tag.tagged_date)
        }
