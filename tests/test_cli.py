# pylint: disable=unused-variable, redefined-outer-name
from typing import Callable, Optional, Tuple

import git
import pytest
from typer.main import get_command_from_info
from typer.testing import CliRunner

from gto.api import get_index
from gto.cli import app

from .utils import _check_obj


def _check_successful_cmd(cmd: str, args: list, expected_stdout: Optional[str]):
    runner = CliRunner()
    result = runner.invoke(app, [cmd] + args)
    assert result.exit_code == 0, (result.output, result.exception)
    if expected_stdout:
        if len(expected_stdout):
            assert len(result.output) > 0, "Output is empty, but should not be"
        assert result.output == expected_stdout


def _check_failing_cmd(cmd: str, args: list, expected_stderr: str):
    runner = CliRunner()
    result = runner.invoke(app, [cmd] + args)
    assert result.exit_code != 0, (result.output, result.exception)
    if expected_stderr:
        assert len(result.output) > 0, "Output is empty, but should not be"
    assert result.output == expected_stderr


@pytest.fixture
def app_cmd():
    return app.registered_commands


@pytest.fixture
def app_cli_cmd(app_cmd):
    return (get_command_from_info(c) for c in app_cmd)


def test_commands_help(app_cli_cmd):
    no_help = [cli_cmd.name for cli_cmd in app_cli_cmd if cli_cmd.help is None]
    assert not no_help, f"{no_help} cli command do not have help!"


def test_commands_args_help(app_cli_cmd):
    no_help = []
    for cmd in app_cli_cmd:
        no_help.extend(
            f"{cmd.name}:{arg.name}"
            for arg in cmd.params
            if arg.help is None or arg.help == ""
        )

    assert not no_help, f"{no_help} cli command args do not have help!"


def test_commands_examples(app_cli_cmd):
    no_examples = [cmd.name for cmd in app_cli_cmd if cmd.examples is None]
    assert not no_examples, f"{no_examples} cli command do not have examples!"


def test_show(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    _check_successful_cmd(
        "show",
        ["-r", repo.working_dir],
        "Nothing found in the current workspace\n",
    )
    _check_successful_cmd(
        "history",
        ["-r", repo.working_dir],
        "Nothing found in the current workspace\n",
    )


EXPECTED_DESCRIBE_OUTPUT = """{
    "type": "model",
    "path": "models/random-forest.pkl",
    "virtual": false
}
"""


# this is one function because showcase fixture takes some time to be created
def test_commands(showcase):
    path, repo, write_file, first_commit, second_commit = showcase
    _check_successful_cmd(
        "latest",
        ["-r", path, "rf"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "latest",
        ["-r", path, "rf", "--ref"],
        "rf@v1.2.4\n",
    )
    _check_successful_cmd(
        "which",
        ["-r", path, "rf", "production"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "which",
        ["-r", path, "rf", "production", "--all"],
        "v1.2.4\nv1.2.3\n",
    )
    _check_successful_cmd(
        "which",
        ["-r", path, "rf", "production", "--ref"],
        "rf#production#3\n",
    )
    _check_successful_cmd("describe", ["-r", path, "rf"], EXPECTED_DESCRIBE_OUTPUT)
    _check_successful_cmd(
        "describe", ["-r", path, "rf", "--path"], "models/random-forest.pkl\n"
    )
    # None because of random order - fix this
    _check_successful_cmd("stages", ["-r", path], None)
    # None because of output randomness and complexity
    _check_successful_cmd(
        "show",
        ["-r", path],
        None,
    )
    # None because of output randomness and complexity
    _check_successful_cmd(
        "history",
        ["-r", path],
        None,
    )


EXPECTED_DESCRIBE_OUTPUT_2 = """{
    "type": "new-type",
    "path": "new/path",
    "labels": [
        "another-label",
        "new-label",
        "some-label"
    ],
    "description": "new description"
}
"""


def test_annotate(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    name = "new-artifact"
    _check_successful_cmd(
        "annotate",
        [
            "-r",
            repo.working_dir,
            "--type",
            "new-type",
            name,
            "--path",
            "new/path",
            "--label",
            "some-label",
            "--label",
            "another-label",
            "--description",
            "some description",
        ],
        "",
    )
    _check_successful_cmd(
        "annotate",
        [
            "-r",
            repo.working_dir,
            name,
            "--label",
            "new-label",
            "--description",
            "new description",
        ],
        "",
    )
    artifact = get_index(repo.working_dir, file=True).get_index().state[name]
    _check_obj(
        artifact,
        dict(
            type="new-type",
            path="new/path",
            virtual=True,
            labels=["another-label", "new-label", "some-label"],
            description="new description",
        ),
        [],
    )
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Add new artifact")

    _check_successful_cmd(
        "describe", ["-r", repo.working_dir, name], EXPECTED_DESCRIBE_OUTPUT_2
    )
    _check_successful_cmd("remove", ["-r", repo.working_dir, name], "")
    write_file(name, "new-artifact update")
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Remove new artifact")

    _check_successful_cmd("describe", ["-r", repo.working_dir, name], "")


def test_register(repo_with_commit: Tuple[git.Repo, Callable]):
    repo, write_file = repo_with_commit

    _check_successful_cmd(
        "register",
        ["-r", repo.working_dir, "a1"],
        "Created git tag 'a1@v0.0.1' that registers a new version\n",
    )

    _check_successful_cmd(
        "register",
        ["-r", repo.working_dir, "a2", "--version", "v1.2.3"],
        "Created git tag 'a2@v1.2.3' that registers a new version\n",
    )

    _check_failing_cmd(
        "register",
        ["-r", repo.working_dir, "a3", "--version", "1.2.3"],
        "❌ Version '1.2.3' is not valid. Example of valid version: 'v1.0.0'\n",
    )


def test_promote(repo_with_commit: Tuple[git.Repo, Callable]):
    repo, write_file = repo_with_commit

    _check_successful_cmd(
        "promote",
        ["-r", repo.working_dir, "nn1", "prod", "HEAD"],
        "Created git tag 'nn1@v0.0.1' that registers a new version\n"
        "Created git tag 'nn1#prod#1' that promotes 'v0.0.1'\n",
    )

    # this check depends on the previous promotion
    _check_failing_cmd(
        "promote",
        ["-r", repo.working_dir, "nn1", "stage", "HEAD", "--version", "v1.0.0"],
        "❌ Can't register 'v1.0.0', since 'v0.0.1' is registered already at this ref\n",
    )

    _check_failing_cmd(
        "promote",
        ["-r", repo.working_dir, "nn2", "prod", "HEAD", "--version", "1.0.0"],
        "❌ Version '1.0.0' is not valid. Example of valid version: 'v1.0.0'\n",
    )
