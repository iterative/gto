import inspect
import logging
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import Callable, Dict, List, Tuple, Union

import git
from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from gto.config import RegistryConfig
from gto.constants import remote_git_repo_regex
from gto.exceptions import GTOException, NoRepo, WrongArgs
from gto.ui import echo


class RemoteRepoMixin:
    @classmethod
    def from_local_repo(cls, repo: Union[str, git.Repo], config: RegistryConfig = None):
        raise NotImplementedError()

    @classmethod
    @contextmanager
    def from_repo(
        cls, repo: Union[str, git.Repo], config: RegistryConfig = None, branch=None
    ):
        if isinstance(repo, str) and is_url_of_remote_repo(repo_path=repo):
            try:
                with cloned_git_repo(repo=repo) as tmp_dir:
                    repo = read_repo(tmp_dir)
                    repo.git.checkout(branch)
                    yield cls.from_local_repo(repo=repo, config=config)
            except (NotADirectoryError, PermissionError) as e:
                raise e.__class__(
                    "Are you using windows with python < 3.9? "
                    "This may be the reason of this error: https://bugs.python.org/issue42796. "
                    "Consider upgrading python."
                ) from e
        else:
            if branch:
                raise WrongArgs("branch can only be set for remote repos")
            yield cls.from_local_repo(repo=repo, config=config)

    def _call_commit_push(
        self,
        func,
        commit=False,
        commit_message=None,
        push=False,
        stdout=False,
        **kwargs,
    ):
        if not (commit or push):
            return func(**kwargs, stdout=stdout)
        with stashed_changes(repo=self.repo, include_untracked=True) as (
            stashed_tracked,
            stashed_untracked,
        ):
            result = func(**kwargs, stdout=stdout)
            if are_files_in_repo_changed(
                repo=self.repo,
                files=stashed_tracked + stashed_untracked,
            ):
                _reset_repo_to_head(repo=self.repo)
                raise GTOException(
                    msg="The command would have changed files that were not committed, "
                    "automated committing is not possible.\n"
                    "Suggested action: Commit the changes and re-run this command."
                )
            git_add_and_commit_all_changes(
                repo=self.repo,
                message=commit_message,
            )
            if push:
                git_push(repo=self.repo)
            if stdout:
                echo(
                    "Running `git commit`"
                    if not push
                    else "Running `git commit` and `git push`"
                    "\nSuccessfully pushed a new commit to remote."
                )
        return result


def are_files_in_repo_changed(repo: Union[str, git.Repo], files: List[str]) -> bool:
    tracked, untracked = _get_repo_changed_tracked_and_untracked_files(repo=repo)
    return (
        len(set(files).intersection(tracked)) > 0
        or len(set(files).intersection(untracked)) > 0
    )


def is_url_of_remote_repo(repo_path: str) -> bool:
    if (
        isinstance(repo_path, str)
        and remote_git_repo_regex.fullmatch(repo_path) is not None
    ):
        logging.debug("%s recognized as remote git repo", repo_path)
        return True

    logging.debug("%s NOT recognized as remote git repo", repo_path)
    return False


@contextmanager
def cloned_git_repo(repo: str):
    tmp_dir = TemporaryDirectory()
    logging.debug("create temporary directory %s", tmp_dir)
    git_clone(repo=repo, dir=tmp_dir.name)
    yield tmp_dir.name
    logging.debug("delete temporary directory %s", tmp_dir)
    tmp_dir.cleanup()


def git_clone(repo: str, dir: str) -> None:
    logging.debug("clone %s in directory %s", repo, dir)
    git.Repo.clone_from(url=repo, to_path=dir)


def git_push_tag(
    repo: Union[str, git.Repo],
    tag_name: str,
    delete: bool = False,
    remote_name: str = "origin",
) -> None:
    repo = read_repo(repo)
    remote = repo.remote(name=remote_name)
    if not hasattr(remote, "url"):
        raise WrongArgs(
            f"provided repo={repo} does not appear to have a remote to push to"
        )
    logging.debug(
        "push %s tag %s from directory %s to remote %s with url %s",
        "--delete" if delete else "",
        tag_name,
        repo.working_dir,
        remote_name,
        remote.url,
    )
    remote_push_args = [tag_name]
    if delete:
        remote_push_args = ["--delete"] + remote_push_args
    push_info = remote.push(remote_push_args)
    if push_info.error is not None:
        raise GTOException(
            msg=f"The command `git push {remote_name} {' '.join(remote_push_args)}` failed. "
            f"Make sure your local repository is in sync with the remote."
        )


def git_push(repo: Union[str, git.Repo]) -> None:
    read_repo(repo).git.push()


def git_add_and_commit_all_changes(repo: Union[str, git.Repo], message: str) -> None:
    repo = read_repo(repo)
    tracked, untracked = _get_repo_changed_tracked_and_untracked_files(repo=repo)
    if len(tracked) + len(untracked) > 0:
        logging.debug("Adding to the index the untracked files %s", untracked)
        logging.debug("Add and commit changes to files %s", tracked + untracked)
        repo.index.add(items=tracked + untracked)
        repo.index.commit(message=message)


def read_repo(repo: Union[str, git.Repo], search_parent_directories=False) -> git.Repo:
    if isinstance(repo, Repo):
        return repo
    try:
        return git.Repo(repo, search_parent_directories=search_parent_directories)
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        raise NoRepo(repo) from e


@contextmanager
def stashed_changes(repo: Union[str, git.Repo], include_untracked: bool = False):
    repo = read_repo(repo)
    if len(repo.refs) == 0:
        raise RuntimeError(
            "Cannot stash because repository has no ref. Please create a first commit."
        )

    tracked, untracked = _get_repo_changed_tracked_and_untracked_files(repo=repo)

    stash_arguments = ["push"]
    if include_untracked:
        stash_arguments += ["--include-untracked"]
    else:
        untracked = []

    try:
        if len(tracked + untracked) > 0:
            repo.git.stash(stash_arguments)
        yield tracked, untracked
    finally:
        if len(tracked + untracked) > 0:
            repo.git.stash("pop")


def _reset_repo_to_head(repo: Union[str, git.Repo]) -> None:
    repo = read_repo(repo)
    repo.git.stash(["push", "--include-untracked"])
    repo.git.stash(["drop"])


def _get_repo_changed_tracked_and_untracked_files(
    repo: Union[str, git.Repo],
) -> Tuple[List[str], List[str]]:
    repo = read_repo(repo)
    return [item.a_path for item in repo.index.diff(None)], repo.untracked_files


def _turn_args_into_kwargs(
    f: Callable, args: tuple, kwargs: Dict[str, object]
) -> Dict[str, object]:
    kwargs_complement = {
        k: args[i]
        for i, k in enumerate(inspect.signature(f).parameters.keys())
        if i < len(args)
    }
    kwargs.update(kwargs_complement)
    return kwargs
