# pylint: disable=redefined-outer-name
import sys
from time import sleep
from typing import Tuple

import pytest
from click.testing import Result
from pytest_test_utils import TmpDir
from scmrepo.git import Git
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


@pytest.fixture
def scm(tmp_dir: TmpDir) -> Git:
    scm_instance = Git.init(tmp_dir)
    try:
        yield scm_instance
    finally:
        scm_instance.close()


@pytest.fixture(autouse=True)
def set_recursion_limit() -> None:
    sys.setrecursionlimit(2000)


@pytest.fixture
def empty_git_repo(scm: Git) -> str:
    return scm.root_dir


@pytest.fixture
def repo_with_commit(tmp_dir: TmpDir, scm: Git) -> str:
    tmp_dir.gen(
        "some-tracked-file",
        "some-random-text",
    )
    scm.add("some-tracked-file")
    scm.commit("Initial commit")
    return str(tmp_dir)


@pytest.fixture
def init_showcase_semver(tmp_dir: TmpDir, request: pytest.FixtureRequest):
    request.getfixturevalue("scm")
    tmp_dir.gen(CONFIG_FILE_NAME, "")


artifacts_yaml = """
rf:
  type: model
  path: models/random-forest.pkl
  virtual: false
nn:
  type: model
  path: models/neural-network.pkl
  virtual: false
features:
  type: dataset
  path: datasets/features.csv
"""


@pytest.fixture
def showcase(
    tmp_dir: TmpDir, scm: Git, request: pytest.FixtureRequest
) -> Tuple[str, str]:  # pylint: disable=too-many-locals, too-many-statements
    request.getfixturevalue("init_showcase_semver")
    tmp_dir.gen(
        {
            "models/random-forest.pkl": "1st version",
            "models/neural-network.pkl": "1st version",
        }
    )
    scm.add(["models"])
    scm.commit("Create models")

    tmp_dir.gen("artifacts.yaml", artifacts_yaml)
    scm.add(["artifacts.yaml"])
    scm.commit("Add artifacts")
    first_commit = scm.get_rev()

    nn_vname = "v0.0.1"
    rf_vname = "v1.2.3"
    gto.api.register(tmp_dir, "rf", "HEAD", rf_vname)
    gto.api.register(tmp_dir, "nn", "HEAD")
    sleep(1)

    tmp_dir.gen("models/random-forest.pkl", "2nd version")

    scm.commit("Update model")
    second_commit = scm.get_rev()

    # bump version automatically
    gto.api.register(tmp_dir, "rf", "HEAD")

    gto.api.assign(tmp_dir, "nn", "staging", version=nn_vname)
    gto.api.assign(tmp_dir, "rf", "production", version=rf_vname)
    sleep(1)  # this is needed to ensure right order of assignments in later checks
    # the problem is git tags doesn't have miliseconds precision, so we need to wait a bit
    gto.api.assign(tmp_dir, "rf", "staging", ref="HEAD")
    sleep(1)
    gto.api.assign(tmp_dir, "rf", "production", ref=scm.get_rev())
    sleep(1)
    gto.api.assign(tmp_dir, "rf", "production", version=rf_vname, force=True)
    return first_commit, second_commit
