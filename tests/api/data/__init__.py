import json
from pathlib import Path

SAMPLE_REMOTE_REPO_URL = r"https://github.com/iterative/example-gto-frozen.git"


def get_sample_remote_repo_expected_registry() -> dict:
    with open(
        Path(__file__).parent / "sample_remote_repo_expected_registry.json",
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)
