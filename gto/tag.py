import re
from datetime import datetime
from enum import Enum
from typing import FrozenSet, Iterable, Optional, Union

import git
from pydantic import BaseModel

from .base import (
    Artifact,
    Assignment,
    BaseManager,
    BaseRegistryState,
    Deprecation,
    Deregistration,
    Registration,
    Unassignment,
)
from .constants import (
    ACTION,
    COUNTER,
    NAME,
    STAGE,
    TAG,
    VERSION,
    Action,
    tag_re,
)
from .exceptions import (
    InvalidTagName,
    MissingArg,
    NotImplementedInGTO,
    RefNotFound,
    TagExists,
    TagNotFound,
    UnknownAction,
)

COUNT_DELIMITER = "#"

TagTemplates = {
    # Action.CREATE: "{artifact}@",
    Action.DEPRECATE: "{artifact}@deprecated",
    Action.REGISTER: "{artifact}@{version}",
    Action.DEREGISTER: "{artifact}@{version}!",
    Action.ASSIGN: "{artifact}#{stage}",
    Action.UNASSIGN: "{artifact}#{stage}!",
}


def name_tag(
    action: Action,
    artifact: str,
    version: Optional[str] = None,
    stage: Optional[str] = None,
    repo: Optional[git.Repo] = None,
    simple: bool = False,
):
    if action not in TagTemplates:
        raise UnknownAction(action=action)

    tag = TagTemplates[action].format(artifact=artifact, version=version, stage=stage)
    if simple:
        return tag
    if repo is None:
        raise MissingArg(arg="repo")
    counter = 0
    for t in repo.tags:
        parsed = parse_name(t.name, raise_on_fail=False)  # type: ignore
        if (
            parsed
            and parsed[NAME] == artifact
            and COUNTER in parsed
            and parsed[COUNTER] > counter
        ):
            counter = parsed[COUNTER]
    return f"{tag}{COUNT_DELIMITER}{counter+1}"


def parse_name(name: str, raise_on_fail: bool = True):

    match = re.search(tag_re, name)
    if raise_on_fail and not match:
        raise InvalidTagName(name)
    if match:
        parsed = {NAME: match["artifact"]}
        if match["deprecated"]:
            parsed[ACTION] = Action.DEPRECATE
        if match[VERSION]:
            parsed[VERSION] = match[VERSION]
            parsed[ACTION] = (
                Action.DEREGISTER if match["cancel"] == "!" else Action.REGISTER
            )
        if match[STAGE]:
            parsed[STAGE] = match[STAGE]
            parsed[ACTION] = (
                Action.UNASSIGN if match["cancel"] == "!" else Action.ASSIGN
            )
        if match[COUNTER]:
            parsed[COUNTER] = int(match[COUNTER])
        return parsed
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
    created_at: datetime
    tag: git.Tag

    class Config:
        arbitrary_types_allowed = True


def parse_tag(tag: git.Tag):
    return Tag(
        tag=tag,
        created_at=datetime.fromtimestamp(tag.tag.tagged_date),
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
    # remove lightweight tags - better to do later so the function is faster
    tags = [t for t in tags if t.tag is not None]
    if sort == "by_time":
        tags = sorted(tags, key=lambda t: t.tag.tagged_date)
    else:
        raise NotImplementedError(f"Unknown sort: {sort}")
    return tags


def create_tag(
    repo: git.Repo,
    name: str,
    ref: str,
    message: str,
    tagger: str = None,
    tagger_email: str = None,
):
    try:
        repo.commit(ref)
    except (ValueError, git.BadName) as e:
        raise RefNotFound(ref=ref) from e
    if name in repo.refs:
        raise TagExists(name=name)

    env = {}
    if tagger:
        env["GIT_COMMITTER_NAME"] = tagger
    if tagger_email:
        env["GIT_COMMITTER_EMAIL"] = tagger_email

    repo.git.tag(["-a", name, "-m", message, ref], env=env)


def delete_tag(repo: git.Repo, name: str):
    try:
        repo.delete_tag(name)
    except git.BadName as e:
        raise TagNotFound(name=name) from e


def index_tag(artifact: Artifact, tag: git.TagReference) -> Artifact:
    event: Union[Deprecation, Registration, Deregistration, Assignment, Unassignment]
    mtag = parse_tag(tag)
    if mtag.action == Action.REGISTER:
        event = Registration(
            artifact=mtag.name,
            version=mtag.version,
            created_at=mtag.created_at,
            author=tag.tag.tagger.name,
            author_email=tag.tag.tagger.email,
            message=tag.tag.message,
            commit_hexsha=tag.commit.hexsha,
            tag=tag.name,
        )
    elif mtag.action == Action.DEREGISTER:
        event = Deregistration(
            artifact=mtag.name,
            version=mtag.version,
            created_at=mtag.created_at,
            author=tag.tag.tagger.name,
            author_email=tag.tag.tagger.email,
            message=tag.tag.message,
            commit_hexsha=tag.commit.hexsha,
            tag=tag.name,
        )
    elif mtag.action in (Action.ASSIGN, Action.UNASSIGN):
        version = artifact.find_version(
            commit_hexsha=tag.commit.hexsha, create_new=True
        ).version  # type: ignore
        if mtag.action == Action.ASSIGN:
            event = Assignment(
                artifact=mtag.name,
                version=version,
                stage=mtag.stage,
                created_at=mtag.created_at,
                author=tag.tag.tagger.name,
                author_email=tag.tag.tagger.email,
                message=tag.tag.message,
                commit_hexsha=tag.commit.hexsha,
                tag=tag.name,
            )
        else:
            event = Unassignment(
                artifact=mtag.name,
                version=version,
                stage=mtag.stage,
                created_at=mtag.created_at,
                author=tag.tag.tagger.name,
                author_email=tag.tag.tagger.email,
                message=tag.tag.message,
                commit_hexsha=tag.commit.hexsha,
                tag=tag.name,
            )
    elif mtag.action == Action.DEPRECATE:
        event = Deprecation(
            artifact=mtag.name,
            created_at=mtag.created_at,
            author=tag.tag.tagger.name,
            author_email=tag.tag.tagger.email,
            message=tag.tag.message,
            commit_hexsha=tag.commit.hexsha,
            tag=tag.name,
        )
    artifact.add_event(event)
    return artifact


class TagManager(BaseManager):  # pylint: disable=abstract-method
    def update_state(self, state: BaseRegistryState) -> BaseRegistryState:
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        for tag in find(repo=self.repo, action=self.actions):
            state.update_artifact(
                index_tag(
                    state.find_artifact(
                        parse_name(tag.tag.tag)["name"], create_new=True
                    ),
                    tag,
                )
            )
        return state


class TagArtifactManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.CREATE, Action.DEPRECATE))

    def create(self):  # pylint: disable=no-self-use
        raise NotImplementedInGTO(
            "If you want to create artifact, register a version or assign a stage for it"
        )

    def deprecate(
        self,
        name,
        ref,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        tag = name_tag(
            Action.DEPRECATE,
            name,
            repo=self.repo,
            simple=simple,
        )
        create_tag(
            self.repo,
            tag,
            ref=ref,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )
        return tag


class TagVersionManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.REGISTER, Action.DEREGISTER))

    def register(
        self,
        name,
        version,
        ref,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        tag = name_tag(
            Action.REGISTER, name, version=version, repo=self.repo, simple=simple
        )
        create_tag(
            self.repo,
            tag,
            ref=ref,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )
        return tag

    def deregister(
        self,
        name,
        version,
        ref,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        tag = name_tag(
            Action.DEREGISTER, name, version=version, repo=self.repo, simple=simple
        )
        create_tag(
            self.repo,
            tag,
            ref=ref,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )
        return tag


class TagStageManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.ASSIGN, Action.UNASSIGN))

    def assign(
        self,
        name,
        stage,
        ref,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> str:
        tag = name_tag(Action.ASSIGN, name, stage=stage, repo=self.repo, simple=simple)
        create_tag(
            self.repo,
            tag,
            ref=ref,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )
        return tag

    def unassign(
        self,
        name,
        stage,
        ref,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> str:
        tag = name_tag(
            Action.UNASSIGN, name, stage=stage, repo=self.repo, simple=simple
        )
        create_tag(
            self.repo,
            tag,
            ref=ref,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )
        return tag
