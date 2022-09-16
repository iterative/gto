import json
from pathlib import Path


def get_sample_remote_repo_url() -> str:
    return r"https://github.com/iterative/example-gto-frozen.git"


def get_sample_remote_repo_expected_registry() -> dict:
    with open(Path(__file__).parent / "sample_remote_repo_expected_registry.json", "r") as f:
        return json.load(f)
