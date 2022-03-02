import os
from time import sleep

import git
import pytest

import gto
from gto.config import CONFIG_FILE


@pytest.fixture
def empty_git_repo(tmp_path):
    return git.Repo.init(tmp_path)


@pytest.fixture
def init_showcase(empty_git_repo):
    path = empty_git_repo.working_dir

    def write_file(name, content):
        fullpath = os.path.join(path, name)
        os.makedirs(os.path.dirname(fullpath), exist_ok=True)
        with open(fullpath, "w", encoding="utf8") as file:
            file.write(content)

    write_file(CONFIG_FILE, "env_base: tag")

    return path, empty_git_repo, write_file


@pytest.fixture
def showcase(init_showcase):  # pylint: disable=too-many-locals, too-many-statements
    path, repo, write_file = init_showcase  # pylint: disable=unused-variable

    write_file("models/random-forest.pkl", "1st version")
    write_file("models/neural-network.pkl", "1st version")

    gto.api.add(path, "rf", "model", "models/random-forest.pkl")
    gto.api.add(path, "nn", "model", "models/neural-network.pkl")
    gto.api.add(path, "features", "dataset", "datasets/features.csv")

    repo.index.add(["artifacts.yaml", "models"])
    first_commit = repo.index.commit("Create models")

    gto.api.register(path, "rf", "HEAD", "v1")
    gto.api.register(path, "nn", "HEAD", "v1")

    write_file("models/random-forest.pkl", "2nd version")

    second_commit = repo.index.commit("Update model")

    gto.api.register(path, "rf", "HEAD", "v2")  # TODO: remove "v2"

    gto.api.promote(path, "nn", "staging", promote_version="v1")
    gto.api.promote(path, "rf", "production", promote_version="v1")
    sleep(1)  # this is needed to ensure right order of labels in later checks
    # the problem is git tags doesn't have miliseconds precision, so we need to wait a bit
    gto.api.promote(path, "rf", "staging", promote_ref="HEAD")
    sleep(1)
    gto.api.promote(path, "rf", "production", promote_ref=repo.head.ref.commit.hexsha)
    sleep(1)
    gto.api.promote(path, "rf", "production", promote_version="v1")
    return path, repo, write_file, first_commit, second_commit
