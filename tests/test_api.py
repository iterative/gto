"""TODO: add more tests for API"""
from time import sleep
from typing import Any, Dict, Set

import pytest

import gto
from tests.utils import _check_dict


def test_empty_index(empty_git_repo):
    index = gto.api.get_index(empty_git_repo.working_dir)
    assert len(index.object_centric_representation()) == 0


def test_empty_state(empty_git_repo):
    state = gto.api.get_state(empty_git_repo.working_dir)
    assert len(state.objects) == 0


@pytest.fixture
def repo_with_artifact(init_showcase):
    path, repo, write_file = init_showcase
    name, type, path_ = "new-artifact", "new-type", "new/path"
    gto.api.add(path, name, type, path_)
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Added index")
    return repo, name


def test_add_remove(empty_git_repo):
    name, type, path = "new-artifact", "new-type", "new/path"
    gto.api.add(empty_git_repo.working_dir, name, type, path)
    index = gto.api.get_index(empty_git_repo.working_dir).get_index()
    assert name in index
    _check_dict(index.state[name], dict(name=name, type=type, path=path), {})
    gto.api.remove(empty_git_repo.working_dir, name)
    index = gto.api.get_index(empty_git_repo.working_dir).get_index()
    assert name not in index


def test_promote(repo_with_artifact):
    repo, name = repo_with_artifact
    env = "staging"
    gto.api.promote(repo.working_dir, name, env, promote_ref="HEAD", name_version="v1")
    label = gto.api.find_active_label(repo.working_dir, name, env)
    author = repo.commit().author.name
    _check_dict(
        label,
        dict(
            object=name,
            version="v1",
            name=env,
            author=author,
            commit_hexsha=repo.commit().hexsha,
        ),
        {"creation_date", "unregistered_date"},
    )
