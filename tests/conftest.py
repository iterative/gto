import os
from time import sleep
from typing import Callable, Tuple

import git
import pytest

import gto
from gto.config import CONFIG_FILE


@pytest.fixture
def empty_git_repo(tmp_path):
    repo = git.Repo.init(tmp_path)

    def write_file(name, content):
        fullpath = os.path.join(tmp_path, name)
        os.makedirs(os.path.dirname(fullpath), exist_ok=True)
        with open(fullpath, "w", encoding="utf8") as file:
            file.write(content)

    return repo, write_file


@pytest.fixture
def init_showcase_semver(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo

    write_file(
        CONFIG_FILE,
        "",
    )

    return repo, write_file


@pytest.fixture
def showcase(
    init_showcase_semver,
):  # pylint: disable=too-many-locals, too-many-statements
    repo: git.Repo
    repo, write_file = init_showcase_semver
    path = repo.working_dir

    write_file("models/random-forest.pkl", "1st version")
    write_file("models/neural-network.pkl", "1st version")
    repo.index.add(["models"])
    repo.index.commit("Create models")

    gto.api.add(path, "model", "rf", "models/random-forest.pkl")
    gto.api.add(path, "model", "nn", "models/neural-network.pkl")
    gto.api.add(path, "dataset", "features", "datasets/features.csv", virtual=True)

    repo.index.add(["artifacts.yaml"])
    first_commit = repo.index.commit("Add artifacts")

    nn_vname = "v0.0.1"
    rf_vname = "v1.2.3"
    gto.api.register(path, "rf", "HEAD", rf_vname)
    gto.api.register(path, "nn", "HEAD")
    sleep(1)

    write_file("models/random-forest.pkl", "2nd version")

    second_commit = repo.index.commit("Update model")

    # bump version automatically
    gto.api.register(path, "rf", "HEAD")

    gto.api.promote(path, "nn", "staging", promote_version=nn_vname)
    gto.api.promote(path, "rf", "production", promote_version=rf_vname)
    sleep(1)  # this is needed to ensure right order of promotions in later checks
    # the problem is git tags doesn't have miliseconds precision, so we need to wait a bit
    gto.api.promote(path, "rf", "staging", promote_ref="HEAD")
    sleep(1)
    gto.api.promote(path, "rf", "production", promote_ref=repo.head.ref.commit.hexsha)
    sleep(1)
    gto.api.promote(path, "rf", "production", promote_version=rf_vname)
    return path, repo, write_file, first_commit, second_commit
