# pylint: disable=unused-variable
from typing import Callable, Tuple

import git
from click.testing import CliRunner

from gto.api import get_index
from gto.cli import add, latest, show_registry, which

from .utils import _check_obj


def _check_successful_cmd(cmd: Callable, args: list, expected_stdout: str):
    runner = CliRunner()
    result = runner.invoke(cmd, args)
    assert result.exit_code == 0, (result.output, result.exception)
    if expected_stdout:
        assert len(result.output) > 0, "Output is empty, but should not be"
    assert result.output == expected_stdout


def test_show(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    _check_successful_cmd(
        show_registry,
        ["-r", repo.working_dir],
        "No tracked artifacts detected in the current workspace\n",
    )


# this is one function because showcase fixture takes some time to be created
def test_commands(showcase):
    path, repo, write_file, first_commit, second_commit = showcase
    _check_successful_cmd(
        latest,
        ["-r", path, "rf"],
        "v1.2.4\n",
    )
    _check_successful_cmd(
        which,
        ["-r", path, "rf", "production"],
        "v1.2.4\n",
    )


def test_add(empty_git_repo):
    repo, write_file = empty_git_repo
    _check_successful_cmd(
        add,
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
