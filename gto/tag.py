import datetime
import os
import re
from enum import Enum
from typing import FrozenSet, Iterable, Optional, Union

from scmrepo.exceptions import RevError
from scmrepo.git import Git, GitTag

from ._pydantic import BaseModel
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
    name_to_tag,
    tag_re,
    tag_to_name,
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
    scm: Optional[Git] = None,
    simple: bool = False,
):
    if action not in TagTemplates:
        raise UnknownAction(action=action)

    tag = TagTemplates[action].format(
        artifact=name_to_tag(artifact), version=version, stage=stage
    )
    if simple:
        return tag
    if scm is None:
        raise MissingArg(arg="scm")
    counter = 0
    for t in scm.list_tags():
        parsed = parse_name(t, raise_on_fail=False)  # type: ignore
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
        parsed = {NAME: tag_to_name(match["artifact"])}
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
    created_at: datetime.datetime
    tag: GitTag

    class Config:
        arbitrary_types_allowed = True


def parse_tag(tag: GitTag):
    return Tag(
        tag=tag,
        created_at=tag.tag_datetime,
        **parse_name(tag.name),
    )


def find(
    action: Optional[Union[Action, FrozenSet[Action]]] = None,
    name: Optional[str] = None,
    version: Optional[str] = None,
    stage: Optional[str] = None,
    scm: Optional[Git] = None,
    sort: str = "by_time",
    tags: Optional[Iterable[GitTag]] = None,
):
    if isinstance(action, Action):
        action = frozenset([action])
    if scm is None:
        raise MissingArg(arg="scm")
    result = []
    tag_names = [t.name for t in tags] if tags else scm.list_tags()
    for t in tag_names:
        try:
            parsed = parse_name(t)
        except InvalidTagName:
            continue
        if (  # pylint: disable=too-many-boolean-expressions
            parsed
            and (not action or parsed[ACTION] in action)
            and (not name or parsed.get(NAME) == name)
            and (not version or parsed.get(VERSION) == version)
            and (not stage or parsed.get(STAGE) == stage)
        ):
            tag = scm.get_tag(t)
            # remove lightweight tags
            if isinstance(tag, GitTag):
                result.append(tag)
    if sort == "by_time":
        return sorted(result, key=lambda t: t.tag_time)
    raise NotImplementedError(f"Unknown sort: {sort}")


def create_tag(  # pylint: disable=too-many-branches
    scm: Git,
    name: str,
    rev: str,
    message: str,
    tagger: Optional[str] = None,
    tagger_email: Optional[str] = None,
):
    try:
        rev = scm.resolve_rev(rev)
    except RevError as e:
        raise RefNotFound(ref=rev) from e
    if scm.get_tag(name):
        raise TagExists(name=name)

    if tagger:
        orig_name: Optional[str] = os.environ.get("GIT_COMMITTER_NAME")
        os.environ["GIT_COMMITTER_NAME"] = tagger
    else:
        orig_name = None
    if tagger_email:
        orig_email: Optional[str] = os.environ.get("GIT_COMMITTER_EMAIL")
        os.environ["GIT_COMMITTER_EMAIL"] = tagger_email
    else:
        orig_email = None
    try:
        scm.tag(name, target=rev, annotated=True, message=message)
    finally:
        if tagger:
            if orig_name:
                os.environ["GIT_COMMITTER_NAME"] = orig_name
            else:
                del os.environ["GIT_COMMITTER_NAME"]
        if tagger_email:
            if orig_email:
                os.environ["GIT_COMMITTER_EMAIL"] = orig_email
            else:
                del os.environ["GIT_COMMITTER_EMAIL"]


def delete_tag(scm: Git, name: str):
    ref = f"refs/tags/{name}"
    if not scm.get_ref(ref):
        raise TagNotFound(name=name)
    scm.remove_ref(ref)


def index_tag(artifact: Artifact, tag: GitTag) -> Artifact:
    event: Union[Deprecation, Registration, Deregistration, Assignment, Unassignment]
    mtag = parse_tag(tag)
    if mtag.action == Action.REGISTER:
        event = Registration(
            artifact=mtag.name,
            version=mtag.version,
            created_at=mtag.created_at,
            author=tag.tagger_name,
            author_email=tag.tagger_email,
            message=tag.message.strip(),
            commit_hexsha=tag.target,
            tag=tag.name,
        )
    elif mtag.action == Action.DEREGISTER:
        event = Deregistration(
            artifact=mtag.name,
            version=mtag.version,
            created_at=mtag.created_at,
            author=tag.tagger_name,
            author_email=tag.tagger_email,
            message=tag.message.strip(),
            commit_hexsha=tag.target,
            tag=tag.name,
        )
    elif mtag.action in (Action.ASSIGN, Action.UNASSIGN):
        version = artifact.find_version(
            commit_hexsha=tag.target, create_new=True
        ).version  # type: ignore
        if mtag.action == Action.ASSIGN:
            event = Assignment(
                artifact=mtag.name,
                version=version,
                stage=mtag.stage,
                created_at=mtag.created_at,
                author=tag.tagger_name,
                author_email=tag.tagger_email,
                message=tag.message.strip(),
                commit_hexsha=tag.target,
                tag=tag.name,
            )
        else:
            event = Unassignment(
                artifact=mtag.name,
                version=version,
                stage=mtag.stage,
                created_at=mtag.created_at,
                author=tag.tagger_name,
                author_email=tag.tagger_email,
                message=tag.message.strip(),
                commit_hexsha=tag.target,
                tag=tag.name,
            )
    elif mtag.action == Action.DEPRECATE:
        event = Deprecation(
            artifact=mtag.name,
            created_at=mtag.created_at,
            author=tag.tagger_name,
            author_email=tag.tagger_email,
            message=tag.message.strip(),
            commit_hexsha=tag.target,
            tag=tag.name,
        )
    artifact.add_event(event)
    return artifact


class TagManager(BaseManager):  # pylint: disable=abstract-method
    def update_state(self, state: BaseRegistryState) -> BaseRegistryState:
        # tags are sorted and then indexed by timestamp
        # this is important to check that history is not broken
        for tag in find(scm=self.scm, action=self.actions):
            state.update_artifact(
                index_tag(
                    state.find_artifact(parse_name(tag.name)["name"], create_new=True),
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
        rev,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        tag = name_tag(
            Action.DEPRECATE,
            name,
            scm=self.scm,
            simple=simple,
        )
        create_tag(
            self.scm,
            tag,
            rev=rev,
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
        rev,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        tag = name_tag(
            Action.REGISTER, name, version=version, scm=self.scm, simple=simple
        )
        create_tag(
            self.scm,
            tag,
            rev=rev,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )
        return tag

    def deregister(
        self,
        name,
        version,
        rev,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        tag = name_tag(
            Action.DEREGISTER, name, version=version, scm=self.scm, simple=simple
        )
        create_tag(
            self.scm,
            tag,
            rev=rev,
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
        rev,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> str:
        tag = name_tag(Action.ASSIGN, name, stage=stage, scm=self.scm, simple=simple)
        create_tag(
            self.scm,
            tag,
            rev=rev,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )
        return tag

    def unassign(
        self,
        name,
        stage,
        rev,
        message,
        simple,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> str:
        tag = name_tag(Action.UNASSIGN, name, stage=stage, scm=self.scm, simple=simple)
        create_tag(
            self.scm,
            tag,
            rev=rev,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )
        return tag
