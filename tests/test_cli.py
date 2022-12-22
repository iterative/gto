# pylint: disable=unused-variable, redefined-outer-name
from typing import Callable, Optional, Tuple
from unittest import mock

import git
import pytest
import typer
from packaging import version
from typer.main import get_command_from_info

from gto.cli import app
from gto.exceptions import GTOException
from gto.index import RepoIndexManager
from tests.conftest import Runner

from .utils import check_obj


def _check_output_contains(output: str, search_value: str) -> bool:
    return search_value in output


def _check_output_exact_match(output: str, search_value: str) -> bool:
    return search_value == output


def _check_successful_cmd(
    cmd: str,
    args: list,
    expected_stdout: Optional[str],
    search_func: Optional[Callable] = _check_output_exact_match,
):
    runner = Runner()
    result = runner.invoke([cmd] + args)
    assert result.exit_code == 0, (result.stdout, result.stderr, result.exception)
    if expected_stdout is not None:
        if len(expected_stdout):
            assert len(result.stdout) > 0, "Output is empty, but should not be"
        assert search_func(result.stdout, expected_stdout)


def _check_failing_cmd(
    cmd: str,
    args: list,
    expected_stderr: str,
    search_func: Optional[Callable] = _check_output_exact_match,
):
    runner = Runner()
    result = runner.invoke([cmd] + args)
    assert result.exit_code != 0, (result.stdout, result.stderr, result.exception)
    if expected_stderr is not None:
        assert len(result.stderr) > 0, "Output is empty, but should not be"
    assert search_func(result.stderr, expected_stderr)


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
        "show",
        ["-r", path, "rf@greatest", "--version"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", path, "rf@latest", "--ref"],
        "rf@v1.2.4\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", path, "rf#production", "--version"],
        "v1.2.3\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", path, "rf#production", "--vs", "-1", "--version"],
        "v1.2.4\nv1.2.3\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", path, "rf#staging", "--vs", "-1", "--version"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", path, "rf#production", "--ref"],
        "rf@v1.2.3\n",
    )
    _check_successful_cmd("describe", ["-r", path, "artifactnotexist"], "")
    _check_successful_cmd("describe", ["-r", path, "rf#stagenotexist"], "")
    _check_successful_cmd("describe", ["-r", path, "rf"], EXPECTED_DESCRIBE_OUTPUT)
    _check_successful_cmd(
        "describe", ["-r", path, "rf#production"], EXPECTED_DESCRIBE_OUTPUT
    )
    _check_successful_cmd(
        "describe", ["-r", path, "rf@latest"], EXPECTED_DESCRIBE_OUTPUT
    )
    _check_successful_cmd(
        "describe", ["-r", path, "rf@v1.2.3"], EXPECTED_DESCRIBE_OUTPUT
    )
    _check_successful_cmd(
        "describe", ["-r", path, "rf", "--path"], "models/random-forest.pkl\n"
    )
    _check_successful_cmd("describe", ["-r", path, "rf", "--type"], "model\n")
    _check_successful_cmd("describe", ["-r", path, "rf", "--description"], "")
    _check_successful_cmd("describe", ["-r", path, "rf", "--custom"], "")
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
    _check_successful_cmd(
        "doctor",
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
        "Updated `artifacts.yaml`",
        _check_output_contains,
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
        "Updated `artifacts.yaml`",
        _check_output_contains,
    )
    with RepoIndexManager.from_repo(repo.working_dir) as index:
        artifact = index.get_index().state[name]  # pylint: disable=protected-access
    check_obj(
        artifact.dict(exclude_defaults=True),
        dict(
            type="new-type",
            path="new/path",
            labels=["another-label", "new-label", "some-label"],
            description="new description",
        ),
    )
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Add new artifact")

    _check_successful_cmd(
        "describe", ["-r", repo.working_dir, name], EXPECTED_DESCRIBE_OUTPUT_2
    )
    _check_successful_cmd(
        "remove",
        ["-r", repo.working_dir, name],
        "Updated `artifacts.yaml`",
        _check_output_contains,
    )
    write_file(name, "new-artifact update")
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Remove new artifact")

    _check_successful_cmd(
        "describe", ["-r", repo.working_dir, "this-artifact-doesnt-exist"], ""
    )


def test_register(repo_with_commit: Tuple[git.Repo, Callable]):
    repo, write_file = repo_with_commit

    _check_successful_cmd(
        "register",
        ["-r", repo.working_dir, "a1"],
        "Created git tag 'a1@v0.0.1' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin a1@v0.0.1\n",
    )

    _check_successful_cmd(
        "register",
        ["-r", repo.working_dir, "a2", "--version", "v1.2.3"],
        "Created git tag 'a2@v1.2.3' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin a2@v1.2.3\n",
    )

    _check_successful_cmd(
        "deprecate",
        ["-r", repo.working_dir, "a2", "v1.2.3"],
        "Created git tag 'a2@v1.2.3!' that deregisters version\n"
        "To push the changes upstream, run:\n"
        "    git push origin a2@v1.2.3!\n",
    )

    _check_successful_cmd(
        "register",
        ["-r", repo.working_dir, "a2", "--simple", "false"],
        "Created git tag 'a2@v1.2.3#1' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin a2@v1.2.3#1\n",
    )

    _check_failing_cmd(
        "register",
        ["-r", repo.working_dir, "a3", "--version", "1.2.3"],
        "❌ Supplied version '1.2.3' cannot be parsed\n",
    )


def test_assign(repo_with_commit: Tuple[git.Repo, Callable]):
    repo, write_file = repo_with_commit

    _check_successful_cmd(
        "register",
        ["-r", repo.working_dir, "nn1"],
        "Created git tag 'nn1@v0.0.1' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin nn1@v0.0.1\n",
    )
    # this check depends on the previous one
    _check_successful_cmd(
        "assign",
        ["-r", repo.working_dir, "nn1", "HEAD", "--stage", "prod"],
        "Created git tag 'nn1#prod#1' that assigns stage to version 'v0.0.1'\n"
        "To push the changes upstream, run:\n"
        "    git push origin nn1#prod#1\n",
    )
    # this check depends on the previous assignment
    _check_failing_cmd(
        "assign",
        [
            "-r",
            repo.working_dir,
            "nn1",
            "HEAD",
            "--version",
            "v1.0.0",
            "--stage",
            "stage",
        ],
        "❌ Can't register 'v1.0.0', since 'v0.0.1' is registered already at this ref\n",
    )

    _check_failing_cmd(
        "assign",
        [
            "-r",
            repo.working_dir,
            "nn2",
            "HEAD",
            "--version",
            "1.0.0",
            "--stage",
            "prod",
        ],
        "❌ Version '1.0.0' is not valid. Example of valid version: 'v1.0.0'\n",
    )

    _check_successful_cmd(
        "assign",
        ["-r", repo.working_dir, "nn2", "HEAD", "--stage", "prod"],
        "Created git tag 'nn2@v0.0.1' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin nn2@v0.0.1\n"
        "Created git tag 'nn2#prod#1' that assigns stage to version 'v0.0.1'\n"
        "To push the changes upstream, run:\n"
        "    git push origin nn2#prod#1\n",
    )


GTO_EXCEPTION_MESSAGE = "Test GTOException Message"


def test_stderr_gto_exception():
    # patch gto show to throw gto exception.
    with mock.patch("gto.api.show", side_effect=GTOException(GTO_EXCEPTION_MESSAGE)):
        _check_failing_cmd("show", [], GTO_EXCEPTION_MESSAGE, _check_output_contains)


EXCEPTION_MESSAGE = "Test Exception Message"


def test_stderr_exception():
    # patch gto show to throw exception.
    with mock.patch("gto.api.show", side_effect=Exception(EXCEPTION_MESSAGE)):
        _check_failing_cmd("show", [], EXCEPTION_MESSAGE, _check_output_contains)
