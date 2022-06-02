import os
from typing import Callable, Tuple

import git
import pytest
from typer.testing import CliRunner

from gto.api import annotate, get_stages
from gto.cli import app
from gto.config import CONFIG_FILE_NAME
from gto.exceptions import UnknownType
from gto.index import init_index_manager
from gto.registry import GitRegistry

CONFIG_CONTENT = """
types: [model, dataset]
stages: [dev, prod]
"""


@pytest.fixture
def init_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo

    write_file(CONFIG_FILE_NAME, CONFIG_CONTENT)
    return repo


def test_config_load_index(init_repo):
    index = init_index_manager(init_repo)
    assert index.config.TYPES == ["model", "dataset"]


def test_config_load_registry(init_repo):
    registry = GitRegistry.from_repo(init_repo)
    assert registry.config.TYPES == ["model", "dataset"]


def test_adding_allowed_type(init_repo):
    annotate(init_repo, "name", type="model")


def test_adding_not_allowed_type(init_repo):
    with pytest.raises(UnknownType):
        annotate(init_repo, "name", type="unknown")


def test_stages(init_repo):
    assert get_stages(init_repo) == ["dev", "prod"]
    assert get_stages(init_repo, allowed=True) == ["dev", "prod"]
    assert get_stages(init_repo, used=True) == []


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
