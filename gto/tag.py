from datetime import datetime
from enum import Enum
from typing import FrozenSet, Iterable, Optional, Union

import git
from pydantic import BaseModel

from gto.config import assert_name_is_valid, check_name_is_valid
from gto.versions import SemVer

from .base import (
    Artifact,
    Assignment,
    BaseManager,
    BaseRegistryState,
    Registration,
)
from .constants import ACTION, NAME, NUMBER, STAGE, TAG, VERSION, Action
from .exceptions import (
    InvalidTagName,
    InvalidVersion,
    MissingArg,
    RefNotFound,
    TagExists,
    TagNotFound,
    UnknownAction,
)

ActionSign = {
    Action.REGISTER: "@",
    Action.ASSIGN: "#",
    Action.UNASSIGN: "!",
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

    if action in (Action.ASSIGN, Action.UNASSIGN):
        if simple:
            tag = f"{name}{ActionSign[Action.ASSIGN]}{stage}"
            if action == Action.UNASSIGN:
                tag += ActionSign[Action.UNASSIGN]
            return tag
        if repo is None:
            raise MissingArg(arg="repo")
        numbers = []
        for tag in repo.tags:
            parsed = parse_name(tag.name, raise_on_fail=False)  # type: ignore
            if (
                parsed
                and (parsed[NAME] == name)
                and (parsed[ACTION] == Action.ASSIGN)
                and (NUMBER in parsed)
            ):
                numbers.append(parsed[NUMBER])
        new_number = max(numbers) + 1 if numbers else 1
        tag = f"{name}{ActionSign[Action.ASSIGN]}{stage}{ActionSign[Action.ASSIGN]}{new_number}"
        if action == Action.UNASSIGN:
            tag += ActionSign[Action.UNASSIGN]
        return tag
    raise UnknownAction(action=action)


def _parse_register(name: str, raise_on_fail: bool = True):
    sign = len(name) - name[::-1].index(ActionSign[Action.REGISTER])
    name, version = name[: sign - 1], name[sign:]
    if check_name_is_valid(name) and SemVer.is_valid(version):
        return {
            ACTION: Action.REGISTER,
            NAME: name,
            VERSION: version,
        }
    if raise_on_fail:
        assert_name_is_valid(name)
        if not SemVer.is_valid(version):
            raise InvalidVersion(
                f"Version format should be v1.0.0, cannot parse {version}"
            )
    return {}


def _parse_assign(name: str, raise_on_fail: bool = True):
    parsed = name.split(ActionSign[Action.ASSIGN])
    unassign = False
    if parsed[-1][-1] == "!":
        unassign = True
        parsed[-1] = parsed[-1][:-1]
    if (
        check_name_is_valid(parsed[0])
        and check_name_is_valid(parsed[1])
        and (parsed[2].isdigit() if len(parsed) == 3 else True)
    ):
        if len(parsed) == 2:
            return {
                ACTION: Action.UNASSIGN if unassign else Action.ASSIGN,
                NAME: parsed[0],
                STAGE: parsed[1],
            }
        if len(parsed) == 3:
            return {
                ACTION: Action.UNASSIGN if unassign else Action.ASSIGN,
                NAME: parsed[0],
                STAGE: parsed[1],
                NUMBER: int(parsed[2]),
            }
    if raise_on_fail:
        assert_name_is_valid(parsed[0])
        assert_name_is_valid(parsed[1])
        if not parsed[2].isdigit():
            raise InvalidTagName(name)
    return {}


def parse_name(name: str, raise_on_fail: bool = True):

    if ActionSign[Action.REGISTER] in name:
        return _parse_register(name, raise_on_fail=raise_on_fail)

    if ActionSign[Action.ASSIGN] in name:
        return _parse_assign(name, raise_on_fail=raise_on_fail)

    if raise_on_fail:
        raise InvalidTagName(name)
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
        tags = [
            t
            for t in repo.tags
            if parse_name(t.name, raise_on_fail=False) and t.tag is not None
        ]
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


def registration_from_tag(tag: git.Tag) -> Registration:
    mtag = parse_tag(tag)
    return Registration(
        artifact=mtag.name,
        version=mtag.version,
        created_at=mtag.created_at,
        author=tag.tag.tagger.name,
        author_email=tag.tag.tagger.email,
        message=tag.tag.message,
        commit_hexsha=tag.commit.hexsha,
        tag=tag.name,
    )


def assignment_from_tag(artifact: Artifact, tag: git.Tag) -> Assignment:
    mtag = parse_tag(tag)
    version = artifact.find_version(
        commit_hexsha=tag.commit.hexsha, create_new=True
    ).version  # type: ignore
    return Assignment(
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


def index_tag(artifact: Artifact, tag: git.TagReference) -> Artifact:
    mtag = parse_name(tag.tag.tag)
    if mtag["action"] == Action.REGISTER:
        artifact.add_event(registration_from_tag(tag))
    if mtag["action"] == Action.ASSIGN:
        artifact.add_event(assignment_from_tag(artifact, tag))
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


class TagVersionManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.REGISTER,))

    def register(
        self,
        name,
        version,
        ref,
        message,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ):
        create_tag(
            self.repo,
            name_tag(Action.REGISTER, name, version=version, repo=self.repo),
            ref=ref,
            message=message,
            tagger=author,
            tagger_email=author_email,
        )

    def check_ref(self, ref: str, state: BaseRegistryState):
        try:
            _ = self.repo.tags[ref]
            art_name = parse_name(ref)[NAME]
            version_name = parse_name(ref)[VERSION]
        except (KeyError, ValueError, IndexError):
            # logging.warning(
            #     "Provided ref doesn't exist or it is not a tag that registers a version"
            # )
            return {}
        return {
            name: version
            for name, artifact in state.get_artifacts().items()
            for version in artifact.versions
            if name == art_name and version.version == version_name
        }


class TagStageManager(TagManager):
    actions: FrozenSet[Action] = frozenset((Action.ASSIGN,))

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
        delete,
        author: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> str:
        if delete:
            return delete_tag(
                self.repo, name_tag(Action.UNASSIGN, name, stage=stage, repo=self.repo)
            )
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

    def check_ref(self, ref: str, state: BaseRegistryState):
        try:
            tag = self.repo.tags[ref]
            _ = parse_name(ref)[STAGE]
            art_name = parse_name(ref)[NAME]
        except (KeyError, ValueError, IndexError):
            return {}
        return {
            name: assignment
            for name, artifact in state.get_artifacts().items()
            for assignment in artifact.assignments + artifact.unassignments
            if name == art_name and assignment.tag == tag.name
        }
