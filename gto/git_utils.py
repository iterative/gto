import inspect
import logging
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Dict, List, Sequence, Tuple

from git import Repo

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


def auto_push_on_remote_repo(f: Callable):
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        kwargs = _turn_args_into_kwargs(f, args, kwargs)

        if isinstance(kwargs["repo"], str) and is_url_of_remote_repo(
            repo=kwargs["repo"]
        ):
            kwargs["auto_push"] = True
            return clone_on_remote_repo(f)(**kwargs)

        return f(**kwargs)

    return wrapped_f


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
    Repo.clone_from(url=repo, to_path=dir)


def git_push_tag(
    repo_path: str, tag_name: str, delete: bool = False, remote_name: str = "origin"
) -> None:
    repo = Repo(path=repo_path)
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


def git_commit_specific_files(
    repo_path: str, files: Sequence[str], message: str
) -> None:
    repo = Repo(path=repo_path)
    changed_tracked_files = {
        (Path(repo_path) / item.a_path).as_posix() for item in repo.index.diff(None)
    }
    all_tracked_files = {
        (Path(repo_path) / f[0]).as_posix() for f in repo.index.entries
    }
    untracked_files_to_commit = {f for f in files if f not in all_tracked_files}
    files_to_commit = changed_tracked_files.intersection(files).union(
        untracked_files_to_commit
    )
    if len(files_to_commit) > 0:
        logging.debug("Adding and committing the files %s", files_to_commit)
        repo.index.add(items=tuple(files_to_commit))
        repo.index.commit(message=message)


@contextmanager
def stashed_changes(repo_path: str, include_untracked: bool = False):
    tracked, untracked = _get_repo_changed_tracked_and_untracked_files(
        repo_path=repo_path
    )

    repo = Repo(path=repo_path)
    stash_arguments = ["push"]
    if include_untracked:
        stash_arguments += ["--include-untracked"]
    else:
        untracked = []
    repo.git.stash(stash_arguments)

    yield tracked, untracked

    if len(tracked) > 0 or len(untracked) > 0:
        repo.git.stash("pop")


def _get_repo_changed_tracked_and_untracked_files(
    repo_path: str,
) -> Tuple[List[str], List[str]]:
    repo = Repo(path=repo_path)
    return [
        (Path(repo_path) / item.a_path).as_posix() for item in repo.index.diff(None)
    ], [(Path(repo_path) / f).as_posix() for f in repo.untracked_files]


def _turn_args_into_kwargs(
    f: Callable, args: tuple, kwargs: Dict[str, object]
) -> Dict[str, object]:
    kwargs_complement = {
        k: args[i]
        for i, k in enumerate(inspect.getfullargspec(f).args)
        if i < len(args)
    }
    kwargs.update(kwargs_complement)
    return kwargs
