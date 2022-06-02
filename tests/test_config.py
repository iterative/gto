import os
from typing import Callable, Tuple

import git
import pytest
from typer.testing import CliRunner

from gto.api import annotate, promote, register
from gto.cli import app
from gto.config import CONFIG_FILE_NAME, check_name_is_valid
from gto.exceptions import UnknownType, ValidationError
from gto.index import init_index_manager
from gto.registry import GitRegistry


@pytest.fixture
def init_repo(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo

    write_file(
        CONFIG_FILE_NAME,
        "type_allowed: [model, dataset]",
    )
    return repo


def test_config_load_index(init_repo):
    index = init_index_manager(init_repo)
    assert index.config.TYPE_ALLOWED == ["model", "dataset"]


def test_config_load_registry(init_repo):
    registry = GitRegistry.from_repo(init_repo)
    assert registry.config.TYPE_ALLOWED == ["model", "dataset"]


def test_adding_allowed_type(init_repo):
    annotate(init_repo, "name", type="model")


def test_adding_not_allowed_type(init_repo):
    with pytest.raises(UnknownType):
        annotate(init_repo, "name", type="unknown")


def test_correct_name(init_repo):
    annotate(init_repo, "model")


def test_incorrect_name(init_repo):
    with pytest.raises(ValidationError):
        annotate(init_repo, "###")


def test_incorrect_type(init_repo):
    with pytest.raises(ValidationError):
        annotate(init_repo, "model", type="###")


def test_register_incorrect_name(init_repo):
    with pytest.raises(ValidationError):
        register(init_repo, "###", ref="HEAD")


# def test_register_incorrect_version(init_repo):
#     with pytest.raises(ValidationError):
#         register(init_repo, "model", ref="HEAD", version="###")


def test_promote_incorrect_name(init_repo):
    with pytest.raises(ValidationError):
        promote(init_repo, "###", promote_ref="HEAD", stage="dev")


def test_promote_incorrect_stage(init_repo):
    with pytest.raises(ValidationError):
        promote(init_repo, "model", promote_ref="HEAD", stage="###")


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


@pytest.mark.parametrize(
    "name",
    [
        "nn",
        "m1",
        "model-prod",
        "model-prod-v1",
        "namespace/model",
    ],
)
def test_check_name_is_valid(name):
    assert check_name_is_valid(name)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "m",
        "1",
        "m/",
        "/m",
        "1nn",
        "###",
        "@@@",
        "-model",
        "model-",
        "model@1",
        "model#1",
        "@namespace/model",
    ],
)
def test_check_name_is_invalid(name):
    assert not check_name_is_valid(name)
