from typing import List


def get_example_http_remote_repo() -> str:
    return "https://github.com/iterative/example-gto.git"


def get_example_ssh_remote_repo() -> str:
    return "git@github.com:iterative/example-gto.git"


def get_all_examples() -> List[str]:
    return [get_example_http_remote_repo(), get_example_ssh_remote_repo()]
