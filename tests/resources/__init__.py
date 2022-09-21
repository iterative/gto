import json
from pathlib import Path

SAMPLE_HTTP_REMOTE_REPO = "https://github.com/iterative/example-gto.git"
SAMPLE_HTTP_REMOTE_REPO_WITHOUT_DOT_GIT_SUFFIX = (
    "https://github.com/iterative/example-gto"
)
SAMPLE_REMOTE_REPO_URL = r"https://github.com/iterative/example-gto-frozen.git"


def get_sample_remote_repo_expected_registry() -> dict:
    with open(
        Path(__file__).parent / "sample_remote_repo_expected_registry.json",
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def get_sample_remote_repo_expected_history_churn() -> dict:
    with open(
        Path(__file__).parent / "sample_remote_repo_expected_history_churn.json",
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)
