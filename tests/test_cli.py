# pylint: disable=unused-variable
from typing import Callable, Tuple

import git
from click.testing import CliRunner

from gto.cli import latest, show, which


def _check_successful_cmd(cmd: Callable, args: list, expected_stdout: str):
    runner = CliRunner()
    result = runner.invoke(cmd, args)
    assert result.exit_code == 0, (result.output, result.exception)
    assert len(result.output) > 0, "Output is empty, but should not be"
    assert result.output == expected_stdout


def test_show(empty_git_repo: Tuple[git.Repo, Callable]):
    repo, write_file = empty_git_repo
    _check_successful_cmd(
        show,
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
        "v1.2.3\n",
    )
