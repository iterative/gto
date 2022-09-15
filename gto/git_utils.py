import inspect
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
        if isinstance(kwargs["repo"], str) and is_remote_repo(repo=kwargs["repo"]):
            with TemporaryDirectory() as tmp_dir:
                # noinspection PyTypeChecker
                git_clone(repo=kwargs["repo"], dir=tmp_dir)
                kwargs["repo"] = tmp_dir
                return f(**kwargs)
        else:
            return f(**kwargs)

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
    Repo.clone_from(url=repo, to_path=dir)


def is_remote_repo(repo: str) -> bool:
    if repo[0:8] == "https://" or repo[0:10] == "ssh://git@" or repo[0:4] == "git@":
        return True
    else:
        return False
