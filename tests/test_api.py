# pylint: disable=unused-variable, protected-access
"""TODO: add more tests for API"""
import os
from contextlib import contextmanager
from typing import Callable, Tuple

import git
import pytest

import gto
from gto.constants import STAGE, VERSION, Action
from gto.exceptions import PathIsUsed, WrongArgs
from gto.tag import find
from gto.versions import SemVer
from tests.utils import _check_obj


def test_empty_index(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    index = gto.api._get_index(repo.working_dir)
    assert len(index.artifact_centric_representation()) == 0


def test_empty_state(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    state = gto.api._get_state(repo.working_dir)
    assert len(state.artifacts) == 0


def test_api_info_commands_empty_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    gto.api.show(repo.working_dir)
    gto.api.history(repo.working_dir)


def test_add_remove(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    name, type, path, must_exist = "new-artifact", "new-type", "new/path", False
    gto.api.annotate(
        repo.working_dir, name, type=type, path=path, must_exist=must_exist
    )
    with pytest.raises(PathIsUsed):
        gto.api.annotate(repo.working_dir, "other-name", path=path)
    index = gto.api._get_index(repo.working_dir).get_index()
    assert name in index
    _check_obj(
        index.state[name],
        dict(
            type=type,
            path=path,
            virtual=not must_exist,
            labels=[],
            description="",
        ),
        [],
    )
    gto.api.remove(repo.working_dir, name)
    index = gto.api._get_index(repo.working_dir).get_index()
    assert name not in index


@pytest.fixture
def repo_with_artifact(init_showcase_semver):
    repo: git.Repo
    repo, write_file = init_showcase_semver
    name, type, path, must_exist = "new-artifact", "new-type", "new/path", False
    gto.api.annotate(
        repo.working_dir, name, type=type, path=path, must_exist=must_exist
    )
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Added index")
    gto.api.annotate(
        repo.working_dir, name, type=type, path="path", must_exist=must_exist
    )
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Added index")
    return repo, name


def test_api_info_commands_repo_with_artifact(
    repo_with_artifact: Tuple[git.Repo, Callable]
):
    repo, write_file = repo_with_artifact
    gto.api.show(repo.working_dir)
    gto.api.show(repo.working_dir, "new-artifact")
    gto.api.history(repo.working_dir)


def test_register(repo_with_artifact):
    repo, name = repo_with_artifact
    vname1, vname2 = "v1.0.0", "v1.0.1"
    gto.api.register(repo.working_dir, name, "HEAD", vname1)
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname1
    gto.api.annotate(
        repo.working_dir,
        "something-irrelevant",
        "doesnt-matter",
        "anything",
        must_exist=False,
    )
    repo.index.commit("Irrelevant action to create a git commit")
    message = "Some message"
    author = "GTO"
    author_email = "gto@iterative.ai"
    gto.api.register(
        repo.working_dir,
        name,
        "HEAD",
        message=message,
        author=author,
        author_email=author_email,
    )
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname2
    assert latest.message == message
    assert latest.author == author
    assert latest.author_email == author_email


def test_assign(repo_with_artifact: Tuple[git.Repo, str]):
    repo, name = repo_with_artifact
    stage = "staging"
    repo.create_tag("v1.0.0")
    repo.create_tag("wrong-tag-unrelated")
    message = "some msg"
    author = "GTO"
    author_email = "gto@iterative.ai"
    gto.api.assign(
        repo.working_dir,
        name,
        stage,
        ref="HEAD",
        name_version="v0.0.1",
        message=message,
        author=author,
        author_email=author_email,
    )
    assignment = gto.api.find_versions_in_stage(repo.working_dir, name, stage)
    _check_obj(
        assignment,
        dict(
            artifact=name,
            version="v0.0.1",
            stage=stage,
            author=author,
            author_email=author_email,
            message=message,
            commit_hexsha=repo.commit().hexsha,
        ),
        {"created_at", "assignments", "tag"},
    )


def test_assign_skip_registration(repo_with_artifact: Tuple[git.Repo, str]):
    repo, name = repo_with_artifact
    stage = "staging"
    with pytest.raises(WrongArgs):
        gto.api.assign(
            repo.working_dir,
            name,
            stage,
            ref="HEAD",
            name_version="v0.0.1",
            skip_registration=True,
        )
    gto.api.assign(repo.working_dir, name, stage, ref="HEAD", skip_registration=True)
    assignment = gto.api.find_versions_in_stage(repo.working_dir, name, stage)
    assert not SemVer.is_valid(assignment.version)


def test_assign_force_is_needed(repo_with_artifact: Tuple[git.Repo, str]):
    repo, name = repo_with_artifact
    gto.api.assign(repo, name, "staging", ref="HEAD")
    gto.api.assign(repo, name, "staging", ref="HEAD^1")
    with pytest.raises(WrongArgs):
        gto.api.assign(repo, name, "staging", ref="HEAD")
    with pytest.raises(WrongArgs):
        gto.api.assign(repo, name, "staging", ref="HEAD^1")
    gto.api.assign(repo, name, "staging", ref="HEAD", force=True)
    gto.api.assign(repo, name, "staging", ref="HEAD^1", force=True)


@contextmanager
def environ(**overrides):
    old = {name: os.environ[name] for name in overrides if name in os.environ}
    to_del = set(overrides) - set(old)
    try:
        os.environ.update(overrides)
        yield
    finally:
        os.environ.update(old)
        for name in to_del:
            os.environ.pop(name, None)


def test_check_ref_detailed(repo_with_artifact: Tuple[git.Repo, Callable]):
    repo, name = repo_with_artifact

    NAME = "model"
    SEMVER = "v1.2.3"
    GIT_AUTHOR_NAME = "Alexander Guschin"
    GIT_AUTHOR_EMAIL = "aguschin@iterative.ai"
    GIT_COMMITTER_NAME = "Oliwav"
    GIT_COMMITTER_EMAIL = "oliwav@iterative.ai"

    with environ(
        GIT_AUTHOR_NAME=GIT_AUTHOR_NAME,
        GIT_AUTHOR_EMAIL=GIT_AUTHOR_EMAIL,
        GIT_COMMITTER_NAME=GIT_COMMITTER_NAME,
        GIT_COMMITTER_EMAIL=GIT_COMMITTER_EMAIL,
    ):
        gto.api.register(repo, name=NAME, ref="HEAD", version=SEMVER)

    info = gto.api.check_ref(repo, f"{NAME}@{SEMVER}")[VERSION][NAME]
    _check_obj(
        info,
        {
            "artifact": NAME,
            "name": SEMVER,
            "author": GIT_COMMITTER_NAME,
            "author_email": GIT_COMMITTER_EMAIL,
            "discovered": False,
            "tag": f"{NAME}@{SEMVER}",
            "assignments": [],
            "enrichments": [],
        },
        skip_keys={"commit_hexsha", "created_at", "message"},
    )


def test_check_ref_multiple_showcase(showcase):
    repo: git.Repo
    (
        path,
        repo,
        write_file,
        first_commit,
        second_commit,
    ) = showcase

    tags = find(repo=repo, action=Action.REGISTER)
    for tag in tags:
        info = list(gto.api.check_ref(repo, tag.name)[VERSION].values())[0]
        assert info.tag == tag.name

    tags = find(repo=repo, action=Action.ASSIGN)
    for tag in tags:
        info = list(gto.api.check_ref(repo, tag.name)[STAGE].values())[0]
        assert info.tag == tag.name


def test_check_ref_catch_the_bug(repo_with_artifact: Tuple[git.Repo, Callable]):
    repo, name = repo_with_artifact
    NAME = "artifact"
    gto.api.register(repo, NAME, "HEAD")
    assignment1 = gto.api.assign(repo, NAME, "staging", ref="HEAD")
    assignment2 = gto.api.assign(repo, NAME, "prod", ref="HEAD")
    assignment3 = gto.api.assign(repo, NAME, "dev", ref="HEAD")
    for assignment, tag in zip(
        [assignment1, assignment2, assignment3],
        [f"{NAME}#staging#1", f"{NAME}#prod#2", f"{NAME}#dev#3"],
    ):
        info = gto.api.check_ref(repo, tag)[STAGE][NAME]
        assert info.tag == assignment.tag == tag


def test_is_not_gto_repo(empty_git_repo):
    repo, _ = empty_git_repo
    assert not gto.api._is_gto_repo(repo.working_dir)


def test_is_gto_repo_because_of_config(init_showcase_semver):
    repo, _ = init_showcase_semver
    assert gto.api._is_gto_repo(repo.working_dir)


def test_is_gto_repo_because_of_registered_artifact(repo_with_commit):
    repo, _ = repo_with_commit
    gto.api.register(repo, "model", "HEAD", "v1.0.0")
    assert gto.api._is_gto_repo(repo)


def test_is_gto_repo_because_of_artifacts_yaml(empty_git_repo):
    repo, write_file = empty_git_repo
    write_file("artifacts.yaml", "{}")
    assert gto.api._is_gto_repo(repo)
