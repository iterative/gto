# pylint: disable=unused-variable, redefined-outer-name
from typing import Callable, Optional, Tuple

import git
import pytest
import typer
from packaging import version
from typer.main import get_command_from_info
from typer.testing import CliRunner

from gto.api import _get_index
from gto.cli import app

from .utils import check_obj


def _check_successful_cmd(cmd: str, args: list, expected_stdout: Optional[str]):
    runner = CliRunner()
    result = runner.invoke(app, [cmd] + args)
    assert result.exit_code == 0, (result.output, result.exception)
    if expected_stdout is not None:
        if len(expected_stdout):
            assert len(result.output) > 0, "Output is empty, but should not be"
        assert result.output == expected_stdout


def _check_failing_cmd(cmd: str, args: list, expected_stderr: str):
    runner = CliRunner()
    result = runner.invoke(app, [cmd] + args)
    assert result.exit_code != 0, (result.output, result.exception)
    if expected_stderr is not None:
        assert len(result.output) > 0, "Output is empty, but should not be"
    assert result.output == expected_stderr


@pytest.fixture
def app_cmd():
    return app.registered_commands


@pytest.fixture
def app_cli_cmd(app_cmd):
    if version.parse(typer.__version__) < version.parse("0.6.0"):
        return (
            get_command_from_info(c) for c in app_cmd  # pylint: disable=missing-kwoa
        )
    return (
        get_command_from_info(  # pylint: disable=unexpected-keyword-arg
            c,
            pretty_exceptions_short=False,
            rich_markup_mode="rich",
        )
        for c in app_cmd
    )


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
        ["-r", path, "rf", "production", "--vs", "-1"],
        "v1.2.4\nv1.2.3\n",
    )
    _check_successful_cmd(
        "which",
        ["-r", path, "rf", "staging", "--vs", "-1"],
        "v1.2.4\n",
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
    # check-ref
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "rf#production#3", "--name"],
        "rf\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "rf#production#3", "--stage"],
        "production\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "rf#production#3", "--version"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "rf@v1.2.4", "--version"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "rf@v1.2.4", "--event"],
        "registration\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "rf@v1.2.4"],
        '✅  Version "v1.2.4" of artifact "rf" was registered\n',
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "rf#production#3", "--event"],
        "assignment\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "rf#production#3"],
        '✅  Stage "production" was assigned to version "v1.2.4" of artifact "rf"\n',
    )
    # TODO: make unsuccessful
    _check_successful_cmd(
        "check-ref",
        ["-r", path, "this-tag-does-not-exist"],
        "",
    )


def test_tag_untag(repo_with_commit: Tuple[git.Repo, Callable]):
    repo, write_file = repo_with_commit
    _check_successful_cmd(
        "tag",
        ["-r", repo.working_dir, "x1"],
        "Created git tag 'x1@v0.0.1'\n",
    )
    _check_successful_cmd(
        "untag",
        ["-r", repo.working_dir, "x1"],
        "Created git tag 'x1@v0.0.1!'\n",
    )

    _check_successful_cmd(
        "tag",
        ["-r", repo.working_dir, "x2", "HEAD"],
        "Created git tag 'x2@v0.0.1'\n",
    )
    _check_successful_cmd(
        "untag",
        ["-r", repo.working_dir, "x2", "HEAD"],
        "Created git tag 'x2@v0.0.1!'\n",
    )

    _check_successful_cmd(
        "tag",
        ["-r", repo.working_dir, "x3", repo.commit().hexsha],
        "Created git tag 'x3@v0.0.1'\n",
    )
    _check_successful_cmd(
        "tag",
        ["-r", repo.working_dir, "x3", repo.commit().hexsha, "--stage", "prod"],
        "Created git tag 'x3#prod#1'\n",
    )
    _check_successful_cmd(
        "tag",
        ["-r", repo.working_dir, "x3", "--version", "v0.0.1", "--stage", "dev"],
        "Created git tag 'x3#dev#2'\n",
    )
    _check_successful_cmd(
        "untag",
        ["-r", repo.working_dir, "x3", repo.commit().hexsha, "--stage", "prod"],
        "Created git tag 'x3#prod!#3'\n",
    )
    _check_successful_cmd(
        "untag",
        ["-r", repo.working_dir, "x3", "--version", "v0.0.1", "--stage", "dev"],
        "Created git tag 'x3#dev!#4'\n",
    )
    _check_successful_cmd(
        "untag",
        ["-r", repo.working_dir, "x3", repo.commit().hexsha],
        "Created git tag 'x3@v0.0.1!'\n",
    )

    _check_successful_cmd(
        "tag",
        ["-r", repo.working_dir, "x4", repo.commit().hexsha, "--version", "v1.0.0"],
        "Created git tag 'x4@v1.0.0'\n",
    )
    _check_successful_cmd(
        "untag",
        ["-r", repo.working_dir, "x4", "--version", "v1.0.0"],
        "Created git tag 'x4@v1.0.0!'\n",
    )

    _check_failing_cmd(
        "tag",
        [
            "-r",
            repo.working_dir,
            "x4",
            repo.commit().hexsha,
            "--version",
            "v1.0.0",
            "--stage",
            "prod",
        ],
        "❌ One and only one of (version, ref) must be specified.\n",
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
    artifact = (
        _get_index(repo.working_dir, file=True).get_index().state[name]
    )  # pylint: disable=protected-access
    check_obj(
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
        "Created git tag 'a1@v0.0.1'\n",
    )

    _check_successful_cmd(
        "register",
        ["-r", repo.working_dir, "a2", "--version", "v1.2.3"],
        "Created git tag 'a2@v1.2.3'\n",
    )

    _check_failing_cmd(
        "register",
        ["-r", repo.working_dir, "a3", "--version", "1.2.3"],
        "❌ Cannot parse tag name 'a3@1.2.3'\n",
    )


def test_assign(repo_with_commit: Tuple[git.Repo, Callable]):
    repo, write_file = repo_with_commit

    _check_successful_cmd(
        "assign",
        ["-r", repo.working_dir, "nn1", "prod", "HEAD"],
        "Created git tag 'nn1@v0.0.1'\n" "Created git tag 'nn1#prod#1'\n",
    )

    # this check depends on the previous assignment
    _check_failing_cmd(
        "assign",
        ["-r", repo.working_dir, "nn1", "stage", "HEAD", "--version", "v1.0.0"],
        "❌ Can't register 'v1.0.0', since 'v0.0.1' is registered already at this ref\n",
    )

    _check_failing_cmd(
        "assign",
        ["-r", repo.working_dir, "nn2", "prod", "HEAD", "--version", "1.0.0"],
        "❌ Version '1.0.0' is not valid. Example of valid version: 'v1.0.0'\n",
    )
