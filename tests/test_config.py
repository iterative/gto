import pytest
from pytest_test_utils import TmpDir
from scmrepo.git import Git
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


@pytest.fixture(name="init_repo")
def _init_repo(tmp_dir: TmpDir, scm: Git) -> TmpDir:
    tmp_dir.gen(CONFIG_FILE_NAME, CONFIG_CONTENT)
    scm.add([CONFIG_FILE_NAME])
    scm.commit("Initial commit")
    return tmp_dir


def test_config_load_index(init_repo: TmpDir):
    with RepoIndexManager.from_url(init_repo) as index:
        assert index.config.TYPES == ["model", "dataset"]


def test_config_load_registry(init_repo: TmpDir):
    with GitRegistry.from_url(init_repo) as reg:
        assert reg.config.TYPES == ["model", "dataset"]


def test_stages(init_repo: TmpDir):
    assert get_stages(init_repo) == ["dev", "prod"]
    assert get_stages(init_repo, allowed=True) == ["dev", "prod"]
    assert get_stages(init_repo, used=True) == []


def test_register_incorrect_name(init_repo: TmpDir):
    with pytest.raises(ValidationError):
        register(init_repo, DISALLOWED_STRING, ref="HEAD")


def test_register_incorrect_version(init_repo: TmpDir):
    with pytest.raises(InvalidVersion):
        register(init_repo, "model", ref="HEAD", version="###")


def test_assign_incorrect_name(init_repo: TmpDir):
    with pytest.raises(ValidationError):
        assign(init_repo, DISALLOWED_STRING, ref="HEAD", stage="dev")


def test_assign_incorrect_stage(init_repo: TmpDir):
    with pytest.raises(ValidationError):
        assign(init_repo, ALLOWED_STRING, ref="HEAD", stage=DISALLOWED_STRING)


@pytest.mark.usefixtures("scm")
def test_config_is_not_needed(tmp_dir: TmpDir):
    tmp_dir.gen(
        CONFIG_FILE_NAME,
        "WRONG_CONFIG",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


@pytest.fixture(name="init_repo_prohibit")
def _init_repo_prohibit(tmp_dir: TmpDir, scm: Git) -> TmpDir:
    tmp_dir.gen(CONFIG_FILE_NAME, PROHIBIT_CONFIG_CONTENT)
    scm.add(CONFIG_FILE_NAME)
    scm.commit("Initial commit")
    return tmp_dir


def test_prohibit_config_assign_incorrect_stage(init_repo_prohibit: TmpDir):
    with pytest.raises(UnknownStage):
        assign(init_repo_prohibit, ALLOWED_STRING, ref="HEAD", stage="dev")
