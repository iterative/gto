import inspect
import logging
from contextlib import contextmanager
from functools import wraps
from tempfile import TemporaryDirectory
from typing import Callable, Dict, List, Tuple

import git

from gto.commit_message_generator import generate_empty_commit_message
from gto.constants import remote_git_repo_regex
from gto.exceptions import GTOException, WrongArgs


def clone_on_remote_repo(f: Callable):
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        kwargs = _turn_args_into_kwargs(f, args, kwargs)

        if isinstance(kwargs["repo"], str) and is_url_of_remote_repo(
            repo=kwargs["repo"]
        ):
            try:
                with cloned_git_repo(repo=kwargs["repo"]) as tmp_dir:
                    kwargs["repo"] = tmp_dir
                    return f(**kwargs)
            except (NotADirectoryError, PermissionError) as e:
                raise e.__class__(
                    "Are you using windows with python < 3.9? "
                    "This may be the reason of this error: https://bugs.python.org/issue42796. "
                    "Consider upgrading python."
                ) from e

        return f(**kwargs)

    return wrapped_f


def set_push_on_remote_repo(f: Callable):
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        kwargs = _turn_args_into_kwargs(f, args, kwargs)

        if isinstance(kwargs["repo"], str) and is_url_of_remote_repo(
            repo=kwargs["repo"]
        ):
            kwargs["push"] = True

        return f(**kwargs)

    return wrapped_f


def commit_produced_changes_on_commit(
    message_generator: Callable[..., str] = generate_empty_commit_message
):
    """
    The function `message_generator` can use any argument that the decorated function has.

    Example: here we are using the argument b of the function f to generate the commit message

        def create_message(b: str) -> str:
            return "commit message with b={b}"

        @commit_produced_changes_on_commit(message_generator=create_message)
        def f(a: str, b: str, c: str):
            ...

    """

    def generate_commit_message(**kwargs) -> str:
        kwargs_for_message_generator = {
            k: kwargs.get(k, None)
            for k in inspect.getfullargspec(message_generator).args
        }
        return message_generator(**kwargs_for_message_generator)

    def wrap(f: Callable):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            kwargs = _turn_args_into_kwargs(f, args, kwargs)

            if kwargs.get("commit", False) is True:
                if "repo" in kwargs:
                    with stashed_changes(
                        repo_path=kwargs["repo"], include_untracked=True
                    ) as (stashed_tracked, stashed_untracked):
                        result = f(**kwargs)
                        if are_files_in_repo_changed(
                            repo_path=kwargs["repo"],
                            files=stashed_tracked + stashed_untracked,
                        ):
                            _reset_repo_to_head(repo_path=kwargs["repo"])
                            raise GTOException(
                                msg="The command would have changed files that were not committed, "
                                "automated committing is not possible.\n"
                                "Suggested action: Commit the changes and re-run this command."
                            )
                        git_add_and_commit_all_changes(
                            repo_path=kwargs["repo"],
                            message=generate_commit_message(**kwargs),
                        )
                else:
                    raise ValueError(
                        "Function decorated with commit_produced_changes_on_commit was called with "
                        "`commit=True` but `repo` was not provided."
                        "Argument `repo` is necessary."
                    )
            else:
                result = f(**kwargs)

            return result

        return wrapped_f

    return wrap


def push_on_push(f: Callable):
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        kwargs = _turn_args_into_kwargs(f, args, kwargs)
        if kwargs.get("push", False) is True:
            kwargs["commit"] = True
            result = f(**kwargs)
            if "repo" in kwargs:
                try:
                    git_push(repo_path=kwargs["repo"])
                except Exception as e:
                    raise GTOException(  # pylint: disable=raise-missing-from
                        "It was not possible to run `git push`. "
                        "The detailed error message was:\n"
                        f"{str(e)}"
                    )
            else:
                raise ValueError(
                    "Function decorated with push_on_push was called with "
                    "`push=True` but `repo` was not provided."
                    "Argument `repo` is necessary."
                )
        else:
            result = f(**kwargs)
        return result

    return wrapped_f


def are_files_in_repo_changed(repo_path: str, files: List[str]) -> bool:
    tracked, untracked = _get_repo_changed_tracked_and_untracked_files(
        repo_path=repo_path
    )
    return (
        len(set(files).intersection(tracked)) > 0
        or len(set(files).intersection(untracked)) > 0
    )


def is_url_of_remote_repo(repo: str) -> bool:
    if remote_git_repo_regex.fullmatch(repo) is not None:
        logging.debug("%s recognized as remote git repo", repo)
        return True

    logging.debug("%s NOT recognized as remote git repo", repo)
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
    repo_path: str, tag_name: str, delete: bool = False, remote_name: str = "origin"
) -> None:
    repo = git.Repo(path=repo_path)
    remote = repo.remote(name=remote_name)
    if not hasattr(remote, "url"):
        raise WrongArgs(
            f"provided repo_path={repo_path} does not appear to have a remote to push to"
        )
    logging.debug(
        "push %s tag %s from directory %s to remote %s with url %s",
        "--delete" if delete else "",
        tag_name,
        repo_path,
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


def git_push(repo_path: str) -> None:
    git.Repo(path=repo_path).git.push()


def git_add_and_commit_all_changes(repo_path: str, message: str) -> None:
    repo = git.Repo(path=repo_path)
    tracked, untracked = _get_repo_changed_tracked_and_untracked_files(
        repo_path=repo_path
    )
    if len(tracked) + len(untracked) > 0:
        logging.debug("Adding to the index the untracked files %s", untracked)
        logging.debug("Add and commit changes to files %s", tracked + untracked)
        repo.index.add(items=tracked + untracked)
        repo.index.commit(message=message)


@contextmanager
def stashed_changes(repo_path: str, include_untracked: bool = False):
    repo = git.Repo(path=repo_path)
    if len(repo.refs) == 0:
        raise RuntimeError(
            "Cannot stash because repository has no ref. Please create a first commit."
        )

    tracked, untracked = _get_repo_changed_tracked_and_untracked_files(
        repo_path=repo_path
    )

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


def _reset_repo_to_head(repo_path: str) -> None:
    repo = git.Repo(path=repo_path)
    repo.git.stash(["push", "--include-untracked"])
    repo.git.stash(["drop"])


def _get_repo_changed_tracked_and_untracked_files(
    repo_path: str,
) -> Tuple[List[str], List[str]]:
    repo = git.Repo(path=repo_path)
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
