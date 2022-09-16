import inspect
import logging
import re
from functools import wraps
from tempfile import TemporaryDirectory
from typing import Callable, Dict

from git import Repo


# TODO: make a new type out of Union[str, Repo]


def git_clone_if_repo_is_remote(f: Callable):
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        kwargs = _turn_args_into_kwargs(args, kwargs)

        # noinspection PyTypeChecker
        if isinstance(kwargs["repo"], str) and is_url_to_remote_repo(repo=kwargs["repo"]):
            with TemporaryDirectory() as tmp_dir:
                logging.debug(f"create temporary directory {tmp_dir}")
                # noinspection PyTypeChecker
                git_clone(repo=kwargs["repo"], dir=tmp_dir)
                kwargs["repo"] = tmp_dir
                result = f(**kwargs)
            logging.debug(f"temporary directory {tmp_dir} has been deleted")
        else:
            result = f(**kwargs)

        return result

    def _turn_args_into_kwargs(args: tuple, kwargs: Dict[str, object]) -> Dict[str, object]:
        kwargs_complement = {
            k: args[i]
            for i, k in enumerate(inspect.getfullargspec(f).args)
            if k not in kwargs.keys() and i < len(args)
        }
        kwargs.update(kwargs_complement)
        return kwargs

    return wrapped_f


def git_clone(repo: str, dir: str) -> None:
    logging.debug(f"clone {repo} in directory {dir}")
    Repo.clone_from(url=repo, to_path=dir)


def is_url_to_remote_repo(repo: str) -> bool:
    # taken from https://stackoverflow.com/a/22312124/19782654
    REGEX_REMOTE_GIT_REPO = r"((git|ssh|http(s)?)|(git@[\w\.]+))(:(//)?)([\w\.@\:/\-~]+)(\.git)(/)?"

    if re.fullmatch(REGEX_REMOTE_GIT_REPO, repo) is not None:
        logging.debug(f"{repo} recognized as remote git repo")
        return True
    else:
        logging.debug(f"{repo} NOT recognized as remote git repo")
        return False
