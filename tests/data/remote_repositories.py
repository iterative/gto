from typing import Iterable


def get_example_http_remote_repo() -> str:
    return "https://github.com/iterative/example-gto.git"


def get_example_ssh_remote_repo() -> str:
    return "ssh://git@github.com:iterative/example-gto.git"


def get_example_short_ssh_remote_repo() -> str:
    return "git@github.com:iterative/example-gto.git"


# TODO: include all examples, also the ssh ones
def get_all_examples() -> Iterable[str]:
    return [get_example_http_remote_repo()] #, get_example_ssh_remote_repo(), get_example_short_ssh_remote_repo()]