"""TODO: add more tests for API"""
from typing import Callable, Tuple

import git
import pytest

import gto
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
    gto.api.audit_registration(repo.working_dir)
    gto.api.audit_promotion(repo.working_dir)
    gto.api.history(repo.working_dir)


def test_add_remove(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo  # pylint: disable=unused-variable
    name, type, path, virtual = "new-artifact", "new-type", "new/path", True
    gto.api.add(repo.working_dir, type, name, path, virtual=virtual)
    index = gto.api.get_index(repo.working_dir).get_index()
    assert name in index
    _check_obj(
        index.state[name],
        dict(name=name, type=type, path=path, virtual=virtual),
        [],
    )
    gto.api.remove(repo.working_dir, name)
    index = gto.api.get_index(repo.working_dir).get_index()
    assert name not in index


@pytest.fixture
def repo_with_artifact(init_showcase_numbers):
    repo: git.Repo
    repo, write_file = init_showcase_numbers  # pylint: disable=unused-variable
    name, type, path_, virtual = "new-artifact", "new-type", "new/path", True
    gto.api.add(repo.working_dir, type, name, path_, virtual=virtual)
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Added index")
    return repo, name


def test_register(repo_with_artifact):
    repo, name = repo_with_artifact
    vname1, vname2 = "v1", "v2"
    gto.api.register(repo.working_dir, name, "HEAD", vname1)
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname1
    gto.api.add(
        repo.working_dir,
        "something-irrelevant",
        "doesnt-matter",
        "anything",
        virtual=True,
    )
    repo.index.commit("Irrelevant action to create a git commit")
    gto.api.register(repo.working_dir, name, "HEAD")
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname2


def test_promote(repo_with_artifact):
    repo, name = repo_with_artifact
    stage = "staging"
    gto.api.promote(
        repo.working_dir, name, stage, promote_ref="HEAD", name_version="v1"
    )
    promotion = gto.api.find_promotion(repo.working_dir, name, stage)
    author = repo.commit().author.name
    _check_obj(
        promotion,
        dict(
            artifact=dict(type="new-type", name=name, path="new/path", virtual=True),
            version="v1",
            stage=stage,
            author=author,
            commit_hexsha=repo.commit().hexsha,
        ),
        {"creation_date", "promotions"},
    )
