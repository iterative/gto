import os
from typing import Callable, Tuple

import git
import pytest
from typer.testing import CliRunner

from gto.api import assign, get_stages, register
from gto.cli import app
from gto.config import CONFIG_FILE_NAME
from gto.exceptions import InvalidVersion, UnknownStage, ValidationError
from gto.index import RepoIndexManager
from gto.registry import GitRegistry

CONFIG_CONTENT = """
types: [model, dataset]
stages: [dev, prod]
"""

PROHIBIT_CONFIG_CONTENT = """
types: []
stages: []
"""

ALLOWED_STRING = "model"
DISALLOWED_STRING = "###"


@pytest.fixture
def init_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo

    write_file(CONFIG_FILE_NAME, CONFIG_CONTENT)
    repo.index.add([CONFIG_FILE_NAME])
    repo.index.commit("Initial commit")
    return repo


def test_config_load_index(init_repo):
    with RepoIndexManager.from_repo(init_repo) as index:
        assert index.config.TYPES == ["model", "dataset"]


def test_config_load_registry(init_repo):
    with GitRegistry.from_repo(repo=init_repo) as reg:
        assert reg.config.TYPES == ["model", "dataset"]


def test_stages(init_repo):
    assert get_stages(init_repo) == ["dev", "prod"]
    assert get_stages(init_repo, allowed=True) == ["dev", "prod"]
    assert get_stages(init_repo, used=True) == []


def test_register_incorrect_name(init_repo):
    with pytest.raises(ValidationError):
        register(init_repo, DISALLOWED_STRING, ref="HEAD")


def test_register_incorrect_version(init_repo):
    with pytest.raises(InvalidVersion):
        register(init_repo, "model", ref="HEAD", version="###")


def test_assign_incorrect_name(init_repo):
    with pytest.raises(ValidationError):
        assign(init_repo, DISALLOWED_STRING, ref="HEAD", stage="dev")


def test_assign_incorrect_stage(init_repo):
    with pytest.raises(ValidationError):
        assign(init_repo, ALLOWED_STRING, ref="HEAD", stage=DISALLOWED_STRING)


def test_config_is_not_needed(empty_git_repo: Tuple[git.Repo, Callable], request):
    repo, write_file = empty_git_repo

    write_file(
        CONFIG_FILE_NAME,
        "WRONG_CONFIG",
    )
    os.chdir(repo.working_dir)
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    os.chdir(request.config.invocation_dir)
    assert result.exit_code == 0


@pytest.fixture
def init_repo_prohibit(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo

    write_file(CONFIG_FILE_NAME, PROHIBIT_CONFIG_CONTENT)
    repo.index.add(CONFIG_FILE_NAME)
    repo.index.commit("Initial commit")
    return repo


def test_prohibit_config_assign_incorrect_stage(init_repo_prohibit):
    with pytest.raises(UnknownStage):
        assign(init_repo_prohibit, ALLOWED_STRING, ref="HEAD", stage="dev")
