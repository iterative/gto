"""TODO: add more tests for API"""
from time import sleep
from typing import Callable, Tuple

import git
import pytest

import gto
from tests.utils import _check_dict


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
    name, type, path, external = "new-artifact", "new-type", "new/path", True
    gto.api.add(repo.working_dir, type, name, path, external=external)
    index = gto.api.get_index(repo.working_dir).get_index()
    assert name in index
    _check_dict(
        index.state[name],
        dict(name=name, type=type, path=path, external=external),
        set(),
    )
    gto.api.remove(repo.working_dir, name)
    index = gto.api.get_index(repo.working_dir).get_index()
    assert name not in index


@pytest.fixture
def repo_with_artifact(init_showcase_numbers):
    repo: git.Repo
    repo, write_file = init_showcase_numbers  # pylint: disable=unused-variable
    name, type, path_, external = "new-artifact", "new-type", "new/path", True
    gto.api.add(repo.working_dir, type, name, path_, external=external)
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
        external=True,
    )
    repo.index.commit("Irrelevant action to create a git commit")
    gto.api.register(repo.working_dir, name, "HEAD")
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname2


def test_promote(repo_with_artifact):
    repo, name = repo_with_artifact
    env = "staging"
    gto.api.promote(repo.working_dir, name, env, promote_ref="HEAD", name_version="v1")
    label = gto.api.find_active_label(repo.working_dir, name, env)
    author = repo.commit().author.name
    _check_dict(
        label,
        dict(
            artifact=name,
            version="v1",
            name=env,
            author=author,
            commit_hexsha=repo.commit().hexsha,
        ),
        {"creation_date", "deprecated_date"},
    )


def test_deprecate_show_audit(showcase):
    """Test that show/audit don't break after deprecating"""
    (
        path,
        repo,
        write_file,  # pylint: disable=unused-variable
        first_commit,  # pylint: disable=unused-variable
        second_commit,  # pylint: disable=unused-variable
    ) = showcase

    gto.api.show(path)
    gto.api.audit_registration(path)
    gto.api.audit_promotion(path)

    gto.api.deprecate(path, "rf", "v1.2.3")
    gto.api.show(path)
    gto.api.audit_registration(path)
    gto.api.audit_promotion(path)

    gto.api.deprecate(repo, "nn", "v0.0.1")
    gto.api.show(repo)
    gto.api.audit_registration(repo)
    gto.api.audit_promotion(repo)

    gto.api.deprecate(repo, "rf", "v1.2.4")
    gto.api.show(repo)
    gto.api.audit_registration(repo)
    gto.api.audit_promotion(repo)

    assert gto.api.find_latest_version(repo, "nn") is None
    assert (
        gto.api.find_latest_version(repo, "nn", include_deprecated=True).name
        == "v0.0.1"
    )


def test_twice_deprecated(repo_with_artifact):
    repo, name = repo_with_artifact
    gto.api.promote(repo, name, "prod", promote_ref="HEAD")
    sleep(1)
    gto.api.deprecate(repo, name, "v1")
    sleep(1)
    gto.api.promote(repo, name, "prod", promote_ref="HEAD")
    sleep(1)
    gto.api.deprecate(repo, name, "v2")
    gto.api.show(repo)
