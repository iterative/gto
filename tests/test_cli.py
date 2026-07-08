# pylint: disable=unused-variable, redefined-outer-name
from time import sleep
from typing import Callable, Optional, Tuple
from unittest import mock

import click
import pytest
from click.exceptions import Abort
from pytest_test_utils import TmpDir

from gto.cli import GtoCommand, _extract_examples, app
from gto.exceptions import GTOException
from tests.conftest import Runner


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
def app_cli_cmd():
    return list(app.commands.values())


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


def test_show(empty_git_repo: str):
    _check_successful_cmd(
        "show",
        ["-r", empty_git_repo],
        "Nothing found in the current workspace\n",
    )
    _check_successful_cmd(
        "history",
        ["-r", empty_git_repo],
        "Nothing found in the current workspace\n",
    )


EXPECTED_DESCRIBE_OUTPUT = """{
    "type": "model",
    "path": "models/random-forest.pkl",
    "virtual": false
}
"""


# this is one function because showcase fixture takes some time to be created
def test_commands(tmp_dir: TmpDir, showcase: Tuple[str, str]):
    first_commit, second_commit = showcase
    _check_successful_cmd(
        "show",
        ["-r", tmp_dir, "rf@greatest", "--version"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", tmp_dir, "rf@latest", "--ref"],
        "rf@v1.2.4\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", tmp_dir, "rf#production", "--version"],
        "v1.2.3\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", tmp_dir, "rf#production", "--vs", "-1", "--version"],
        "v1.2.4\nv1.2.3\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", tmp_dir, "rf#staging", "--vs", "-1", "--version"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "show",
        ["-r", tmp_dir, "rf#production", "--ref"],
        "rf@v1.2.3\n",
    )
    # None because of random order - fix this
    _check_successful_cmd("stages", ["-r", tmp_dir], None)
    # None because of output randomness and complexity
    _check_successful_cmd(
        "show",
        ["-r", tmp_dir],
        None,
    )
    # None because of output randomness and complexity
    _check_successful_cmd(
        "history",
        ["-r", tmp_dir],
        None,
    )
    # check-ref
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "rf#production#3", "--name"],
        "rf\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "refs/tags/rf#production#3", "--name"],
        "rf\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "rf#production#3", "--stage"],
        "production\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "rf#production#3", "--version"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "rf@v1.2.4", "--version"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "rf@v1.2.4", "--event"],
        "registration\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "rf@v1.2.4"],
        '✅  Version "v1.2.4" of artifact "rf" was registered\n',
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "rf#production#3", "--event"],
        "assignment\n",
    )
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "rf#production#3"],
        '✅  Stage "production" was assigned to version "v1.2.4" of artifact "rf"\n',
    )
    # TODO: make unsuccessful
    _check_successful_cmd(
        "check-ref",
        ["-r", tmp_dir, "this-tag-does-not-exist"],
        "",
    )
    _check_successful_cmd(
        "parse-tag",
        ["dvclive/dsd=nn@v0.0.1"],
        "dvclive/dsd:nn",
        _check_output_contains,
    )
    _check_successful_cmd(
        "doctor",
        ["-r", tmp_dir],
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


def test_register(repo_with_commit: str):
    _check_successful_cmd(
        "register",
        ["-r", repo_with_commit, "a1"],
        "Created git tag 'a1@v0.0.1' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin a1@v0.0.1\n",
    )

    _check_successful_cmd(
        "deprecate",
        ["-r", repo_with_commit, "a1", "v0.0.1", "--delete"],
        "Deleted git tag 'a1@v0.0.1'\n"
        "To push the changes upstream, run:\n"
        "    git push --delete origin a1@v0.0.1\n",
    )

    _check_successful_cmd(
        "register",
        ["-r", repo_with_commit, "a2", "--version", "v1.2.3"],
        "Created git tag 'a2@v1.2.3' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin a2@v1.2.3\n",
    )

    _check_successful_cmd(
        "deprecate",
        ["-r", repo_with_commit, "a2", "v1.2.3"],
        "Created git tag 'a2@v1.2.3!' that deregisters version\n"
        "To push the changes upstream, run:\n"
        "    git push origin a2@v1.2.3!\n",
    )

    _check_successful_cmd(
        "register",
        ["-r", repo_with_commit, "a2", "--simple", "false"],
        "Created git tag 'a2@v1.2.3#1' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin a2@v1.2.3#1\n",
    )

    _check_failing_cmd(
        "register",
        ["-r", repo_with_commit, "a3", "--version", "1.2.3"],
        "❌ Supplied version '1.2.3' cannot be parsed\n",
    )

    _check_successful_cmd(
        "register",
        ["-r", repo_with_commit, "classification/dvclive:models/nn"],
        "classification/dvclive=models/nn@v0.0.1",
        search_func=_check_output_contains,
    )


def test_assign(repo_with_commit: str):
    _check_successful_cmd(
        "register",
        ["-r", repo_with_commit, "nn1"],
        "Created git tag 'nn1@v0.0.1' that registers version\n"
        "To push the changes upstream, run:\n"
        "    git push origin nn1@v0.0.1\n",
    )
    # this check depends on the previous one
    _check_successful_cmd(
        "assign",
        ["-r", repo_with_commit, "nn1", "HEAD", "--stage", "prod"],
        "Created git tag 'nn1#prod#1' that assigns stage to version 'v0.0.1'\n"
        "To push the changes upstream, run:\n"
        "    git push origin nn1#prod#1\n",
    )
    # this check depends on the previous assignment
    _check_failing_cmd(
        "assign",
        [
            "-r",
            repo_with_commit,
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
            repo_with_commit,
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
        ["-r", repo_with_commit, "nn2", "HEAD", "--stage", "prod"],
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


def test_version_flag():
    result = Runner().invoke(["--version"])
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "GTO Version" in result.stdout


def test_verbose_flag():
    result = Runner().invoke(["--verbose"])
    assert result.exit_code == 0, (result.stdout, result.stderr)


def test_subcommand_help_shows_arguments():
    result = Runner().invoke(["register", "-h"])
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "Arguments:" in result.stdout
    assert "Artifact name" in result.stdout
    assert "--bump-major" in result.stdout


def test_extract_examples():
    assert _extract_examples(None) == (None, None)
    examples, help_ = _extract_examples("Do a thing.\n\nExamples:\n  gto show\n")
    assert examples is not None and "gto show" in examples
    assert help_ == "Do a thing.\n\n"


def test_examples_rendered_in_help():
    cmd = GtoCommand(
        name="x",
        help="Do a thing.\n\nExamples:\n  gto x\n",
        callback=lambda: None,
    )
    help_text = cmd.get_help(click.Context(cmd, info_name="x"))
    assert "Examples" in help_text
    assert "gto x" in help_text


def test_promote_alias(repo_with_commit: str):
    _check_successful_cmd("register", ["-r", repo_with_commit, "m1"], None)
    _check_successful_cmd(
        "promote", ["-r", repo_with_commit, "m1", "--stage", "prod"], None
    )


def test_bad_simple_value(repo_with_commit: str):
    _check_failing_cmd(
        "register",
        ["-r", repo_with_commit, "m1", "--simple", "bogus"],
        "Only one of ['auto', 'true', 'false'] is allowed",
        _check_output_contains,
    )


def test_bad_sort_value(empty_git_repo: str):
    _check_failing_cmd(
        "show",
        ["-r", empty_git_repo, "--sort", "bogus"],
        "Only one of ['timestamp', 'semver'] is allowed",
        _check_output_contains,
    )


def test_traceback_flag_propagates_gto_exception():
    with mock.patch("gto.api.show", side_effect=GTOException("boom")):
        result = Runner().invoke(["--traceback", "show"])
    assert result.exit_code == 1
    assert isinstance(result.exception, GTOException)
    assert "boom" not in result.stderr  # no pretty message, raw traceback instead


def test_traceback_flag_propagates_unexpected_exception():
    with mock.patch("gto.api.show", side_effect=ValueError("boom")):
        result = Runner().invoke(["--tb", "show"])
    assert result.exit_code == 1
    assert isinstance(result.exception, ValueError)


def test_click_exceptions_pass_through():
    with mock.patch("gto.api.show", side_effect=Abort()):
        result = Runner().invoke(["show"])
    assert result.exit_code == 1
    assert "Aborted" in result.output


def test_assign_version_without_ref(repo_with_commit: str):
    _check_successful_cmd("register", ["-r", repo_with_commit, "m2"], None)
    _check_successful_cmd(
        "assign",
        ["-r", repo_with_commit, "m2", "--stage", "prod", "--version", "v0.0.1"],
        None,
    )
    # neither REF nor --version: assigns at HEAD
    _check_successful_cmd(
        "assign", ["-r", repo_with_commit, "m2", "--stage", "dev"], None
    )


def test_deprecate_unassign_and_artifact(repo_with_commit: str):
    _check_successful_cmd("register", ["-r", repo_with_commit, "m3"], None)
    _check_successful_cmd(
        "assign", ["-r", repo_with_commit, "m3", "--stage", "prod"], None
    )
    sleep(1)
    _check_successful_cmd(
        "deprecate", ["-r", repo_with_commit, "m3", "v0.0.1", "prod"], None
    )
    sleep(1)
    _check_successful_cmd("deprecate", ["-r", repo_with_commit, "m3"], None)


def test_parse_tag_key():
    _check_successful_cmd("parse-tag", ["m1@v0.0.1", "--key", "version"], '"v0.0.1"\n')


def test_check_ref_json(repo_with_commit: str):
    _check_successful_cmd("register", ["-r", repo_with_commit, "m4"], None)
    _check_successful_cmd(
        "check-ref",
        ["-r", repo_with_commit, "m4@v0.0.1", "--json"],
        '"artifact": "m4"',
        _check_output_contains,
    )


def test_check_ref_multiple_events():
    with mock.patch("gto.api.check_ref", return_value=[1, 2]):
        _check_failing_cmd(
            "check-ref",
            ["-r", ".", "some-ref"],
            "not supported",
            _check_output_contains,
        )


def test_show_json_empty(empty_git_repo: str):
    _check_successful_cmd("show", ["-r", empty_git_repo, "--json"], "{}\n")


def test_show_ref_flag_not_applicable(repo_with_commit: str):
    _check_successful_cmd("register", ["-r", repo_with_commit, "m5"], None)
    _check_failing_cmd(
        "show",
        ["-r", repo_with_commit, "--ref"],
        "Cannot apply --ref",
        _check_output_contains,
    )


def test_history_json_empty(repo_with_commit: str):
    _check_successful_cmd("history", ["-r", repo_with_commit, "--json"], "[]\n")


def test_stages_json_empty(empty_git_repo: str):
    _check_successful_cmd("stages", ["-r", empty_git_repo, "--json"], "[]\n")


def test_print_state(repo_with_commit: str):
    _check_successful_cmd(
        "print-state", ["-r", repo_with_commit], '"artifacts"', _check_output_contains
    )


def test_doctor_wrong_config(tmp_dir: TmpDir, scm):  # pylint: disable=unused-argument
    tmp_dir.gen(".gto", "WRONG_CONFIG")
    _check_failing_cmd(
        "doctor", ["-r", str(tmp_dir)], "Wrong config file", _check_output_contains
    )


def test_unknown_command():
    result = Runner().invoke(["no-such-command"])
    assert result.exit_code == 2
    assert "No such command" in result.stderr
