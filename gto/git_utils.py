import inspect
import logging
from functools import wraps
from tempfile import TemporaryDirectory
from typing import Callable, Dict

from git import Repo

# TODO: make a new type out of Union[str, Repo]
from gto.constants import remote_git_repo_regex


def git_clone_if_repo_is_remote(f: Callable):
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        kwargs = _turn_args_into_kwargs(args, kwargs)

        # noinspection PyTypeChecker
        if isinstance(kwargs["repo"], str) and is_url_to_remote_repo(
            repo=kwargs["repo"]
        ):
            try:
                with TemporaryDirectory() as tmp_dir:
                    logging.debug("create temporary directory %s", tmp_dir)
                    # noinspection PyTypeChecker
                    git_clone(repo=kwargs["repo"], dir=tmp_dir)
                    kwargs["repo"] = tmp_dir
                    result = f(**kwargs)
            except (NotADirectoryError, PermissionError) as e:
                raise e.__class__(
                    "Are you using windows with python < 3.9? "
                    "This may be the reason of this error: https://bugs.python.org/issue42796. "
                    "Consider upgrading python."
                ) from e
            logging.debug("temporary directory %s has been deleted", tmp_dir)
        else:
            result = f(**kwargs)

        return result

    def _turn_args_into_kwargs(
        args: tuple, kwargs: Dict[str, object]
    ) -> Dict[str, object]:
        kwargs_complement = {
            k: args[i]
            for i, k in enumerate(inspect.getfullargspec(f).args)
            if k not in kwargs.keys() and i < len(args)
        }
        kwargs.update(kwargs_complement)
        return kwargs

    return wrapped_f


def git_clone(repo: str, dir: str) -> None:
    logging.debug("clone %s in directory %s", repo, dir)
    Repo.clone_from(url=repo, to_path=dir)


def is_url_to_remote_repo(repo: str) -> bool:
    if remote_git_repo_regex.fullmatch(repo) is not None:
        logging.debug("%s recognized as remote git repo", repo)
        return True

    logging.debug("%s NOT recognized as remote git repo", repo)
    return False
