import os
import sys
from time import sleep
from typing import Callable, Tuple

import git
import pytest
from click.testing import Result
from typer.testing import CliRunner

import gto
from gto.cli import app
from gto.config import CONFIG_FILE_NAME


class Runner:
    def __init__(self):
        self._runner = CliRunner(mix_stderr=False)

    def invoke(self, *args, **kwargs) -> Result:
        return self._runner.invoke(app, *args, **kwargs)


@pytest.fixture
def runner() -> Runner:
    return Runner()


@pytest.fixture(autouse=True)
def set_recursion_limit() -> None:
    sys.setrecursionlimit(2000)


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
def repo_with_commit(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo

    write_file(
        "some-random-file",
        "some-random-text",
    )
    repo.index.add(["some-random-file"])
    repo.index.commit("Initial commit")

    return repo, write_file


@pytest.fixture
def init_showcase_semver(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo

    write_file(
        CONFIG_FILE_NAME,
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

    gto.api.annotate(
        path, "rf", type="model", path="models/random-forest.pkl", must_exist=True
    )
    gto.api.annotate(
        path, "nn", type="model", path="models/neural-network.pkl", must_exist=True
    )
    gto.api.annotate(path, "features", type="dataset", path="datasets/features.csv")

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

    gto.api.assign(path, "nn", "staging", version=nn_vname)
    gto.api.assign(path, "rf", "production", version=rf_vname)
    sleep(1)  # this is needed to ensure right order of assignments in later checks
    # the problem is git tags doesn't have miliseconds precision, so we need to wait a bit
    gto.api.assign(path, "rf", "staging", ref="HEAD")
    sleep(1)
    gto.api.assign(path, "rf", "production", ref=repo.head.ref.commit.hexsha)
    sleep(1)
    gto.api.assign(path, "rf", "production", version=rf_vname, force=True)
    return path, repo, write_file, first_commit, second_commit
