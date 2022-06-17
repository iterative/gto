"""TODO: add more tests for API"""
import os
from contextlib import contextmanager
from typing import Callable, Tuple

import git
import pytest

import gto
from gto.exceptions import PathIsUsed, WrongArgs
from gto.versions import SemVer
from tests.utils import _check_obj


def test_empty_index(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo  # pylint: disable=unused-variable
    index = gto.api.get_index(repo.working_dir)
    assert len(index.artifact_centric_representation()) == 0


def test_empty_state(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo  # pylint: disable=unused-variable
    state = gto.api._get_state(repo.working_dir)  # pylint: disable=protected-access
    assert len(state.artifacts) == 0


def test_api_info_commands_empty_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo  # pylint: disable=unused-variable
    gto.api.show(repo.working_dir)
    gto.api.history(repo.working_dir)


def test_add_remove(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo  # pylint: disable=unused-variable
    name, type, path, must_exist = "new-artifact", "new-type", "new/path", False
    gto.api.annotate(
        repo.working_dir, name, type=type, path=path, must_exist=must_exist
    )
    with pytest.raises(PathIsUsed):
        gto.api.annotate(repo.working_dir, "other-name", path=path)
    index = gto.api.get_index(repo.working_dir).get_index()
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
    index = gto.api.get_index(repo.working_dir).get_index()
    assert name not in index


@pytest.fixture
def repo_with_artifact(init_showcase_semver):
    repo: git.Repo
    repo, write_file = init_showcase_semver  # pylint: disable=unused-variable
    name, type, path, must_exist = "new-artifact", "new-type", "new/path", False
    gto.api.annotate(
        repo.working_dir, name, type=type, path=path, must_exist=must_exist
    )
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Added index")
    return repo, name


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


def test_promote(repo_with_artifact: Tuple[git.Repo, str]):
    repo, name = repo_with_artifact
    stage = "staging"
    repo.create_tag("v1.0.0")
    repo.create_tag("wrong-tag-unrelated")
    message = "some msg"
    author = "GTO"
    author_email = "gto@iterative.ai"
    gto.api.promote(
        repo.working_dir,
        name,
        stage,
        promote_ref="HEAD",
        name_version="v0.0.1",
        message=message,
        author=author,
        author_email=author_email,
    )
    promotion = gto.api.find_versions_in_stage(repo.working_dir, name, stage)
    _check_obj(
        promotion,
        dict(
            artifact=name,
            version="v0.0.1",
            stage=stage,
            author=author,
            author_email=author_email,
            message=message,
            commit_hexsha=repo.commit().hexsha,
        ),
        {"created_at", "promotions", "tag"},
    )


def test_promote_skip_registration(repo_with_artifact):
    repo, name = repo_with_artifact
    stage = "staging"
    with pytest.raises(WrongArgs):
        gto.api.promote(
            repo.working_dir,
            name,
            stage,
            promote_ref="HEAD",
            name_version="v0.0.1",
            skip_registration=True,
        )
    gto.api.promote(
        repo.working_dir, name, stage, promote_ref="HEAD", skip_registration=True
    )
    promotion = gto.api.find_versions_in_stage(repo.working_dir, name, stage)
    assert not SemVer.is_valid(promotion.version)


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


def test_check_ref(repo_with_artifact: Tuple[git.Repo, Callable]):
    repo, name = repo_with_artifact  # pylint: disable=unused-variable

    NAME = "model"
    VERSION = "v1.2.3"
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
        gto.api.register(repo, name=NAME, ref="HEAD", version=VERSION)

    info = gto.api.check_ref(repo, f"{NAME}@{VERSION}")["version"][NAME]
    _check_obj(
        info,
        {
            "artifact": NAME,
            "name": VERSION,
            "author": GIT_COMMITTER_NAME,
            "author_email": GIT_COMMITTER_EMAIL,
            "discovered": False,
            "tag": f"{NAME}@{VERSION}",
            "promotions": [],
            "enrichments": [],
        },
        skip_keys={"commit_hexsha", "created_at", "message"},
    )
