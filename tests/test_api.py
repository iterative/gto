# pylint: disable=unused-variable
"""TODO: add more tests for API"""
from typing import Callable, Tuple

import git
import pytest

import gto
from tests.utils import _check_obj


def test_empty_index(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    index = gto.api.get_index(repo.working_dir)
    assert len(index.artifact_centric_representation()) == 0


def test_empty_state(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    state = gto.api._get_state(repo.working_dir)  # pylint: disable=protected-access
    assert len(state.artifacts) == 0


def test_api_info_commands_empty_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    gto.api.show(repo.working_dir)
    gto.api.history(repo.working_dir)


@pytest.fixture
def repo_with_artifact(init_showcase_semver):
    repo: git.Repo
    repo, write_file = init_showcase_semver
    write_file("some-file", "file content")
    name = "new-artifact"
    repo.index.add(["some-file"])
    repo.index.commit("Added index")
    return repo, name, write_file


def test_register(repo_with_artifact):
    repo, name, write_file = repo_with_artifact
    vname1, vname2 = "v1.0.0", "v1.0.1"
    gto.api.register(repo.working_dir, name, "HEAD", vname1)
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname1
    write_file("some-file", "doesnt-matter")
    repo.index.add(["some-file"])
    repo.index.commit("Irrelevant action to create a git commit")
    gto.api.register(repo.working_dir, name, "HEAD")
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname2


def test_promote(repo_with_artifact):
    repo, name, write_file = repo_with_artifact
    stage = "staging"
    gto.api.promote(
        repo.working_dir, name, stage, promote_ref="HEAD", name_version="v0.0.1"
    )
    promotion = gto.api.find_promotion(repo.working_dir, name, stage)
    author = repo.commit().author.name
    _check_obj(
        promotion,
        dict(
            artifact=name,
            version="v0.0.1",
            stage=stage,
            author=author,
            commit_hexsha=repo.commit().hexsha,
        ),
        {
            "creation_date",
            "promotions",
            "tag",
            "details",
        },  # TODO add tag, details to check
    )
