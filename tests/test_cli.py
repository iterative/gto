# pylint: disable=unused-variable
from typing import Callable, Tuple

import git
import pytest
from typer.main import get_command_from_info
from typer.testing import CliRunner

from gto.api import get_index
from gto.cli import FormatTable, app
from .utils import _check_obj


def _check_successful_cmd(cmd: str, args: list, expected_stdout: str):
    runner = CliRunner()
    result = runner.invoke(app, [cmd] + args)
    assert result.exit_code == 0, (result.output, result.exception)
    if expected_stdout:
        assert len(result.output) > 0, "Output is empty, but should not be"
    assert result.output == expected_stdout


@pytest.fixture
def app_cmd():
    return app.registered_commands


@pytest.fixture
def app_cli_cmd(app_cmd):
    return (get_command_from_info(c) for c in app_cmd)


def test_commands_help(app_cli_cmd):
    no_help = []
    for cli_cmd in app_cli_cmd:
        if cli_cmd.help is None:
            no_help.append(cli_cmd.name)
    assert len(no_help) == 0, f"{no_help} cli commnads do not have help!"


def test_commands_args_help(app_cli_cmd):
    no_help = []
    for cmd in app_cli_cmd:
        for arg in cmd.params:
            if arg.help is None or arg.help == "":
                no_help.append(f"{cmd.name}:{arg.name}")
    assert len(no_help) == 0, f"{no_help} cli commnad args do not have help!"


def test_commands_examples(app_cli_cmd):
    no_examples = []
    for cmd in app_cli_cmd:
        if cmd.examples is None:
            no_examples.append(cmd.name)
    assert len(no_examples) == 0, f"{no_examples} cli commnads do not have examples!"


def test_show(empty_git_repo: Tuple[git.Repo, Callable]):
    FormatTable
    repo, write_file = empty_git_repo
    _check_successful_cmd(
        "show",
        ["-r", repo.working_dir],
        "No tracked artifacts detected in the current workspace\n",
    )


# this is one function because showcase fixture takes some time to be created
def test_commands(showcase):
    path, repo, write_file, first_commit, second_commit = showcase
    _check_successful_cmd(
        "latest",
        ["-r", path, "rf"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "which",
        ["-r", path, "rf", "production"],
        "v1.2.4\n",
    )


def test_add(empty_git_repo):
    repo, write_file = empty_git_repo
    _check_successful_cmd(
        "add",
        [
            "-r",
            repo.working_dir,
            "new-type",
            "new-artifact",
            "new/path",
            "--virtual",
            "--tag",
            "some-tag",
            "--tag",
            "another-tag",
            "--description",
            "some description",
        ],
        "",
    )
    artifact = get_index(repo.working_dir, file=True).get_index().state["new-artifact"]
    _check_obj(
        artifact,
        dict(
            name="new-artifact",
            type="new-type",
            path="new/path",
            virtual=True,
            tags=["some-tag", "another-tag"],
            description="some description",
        ),
        [],
    )
