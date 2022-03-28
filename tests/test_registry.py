# pylint: disable=unused-variable
import datetime

from gto.registry import GitRegistry

from .utils import _check_dict

EXPECTED_REGISTRY_TAG_TAG_STATE = {
    "artifacts": {
        "features": {
            "name": "features",
            "commits": {
                "7891d6833470aff9fbbc0c1ceab7d7553c963883": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
                "8e258886c5a182c96ef040b74cf944160b8e7357": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
            },
            "versions": [],
            "labels": [],
        },
        "nn": {
            "name": "nn",
            "commits": {
                "7891d6833470aff9fbbc0c1ceab7d7553c963883": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
                "8e258886c5a182c96ef040b74cf944160b8e7357": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
            },
            "versions": [
                {
                    "artifact": "nn",
                    "name": "v0.0.1",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 37),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                }
            ],
            "labels": [
                {
                    "artifact": "nn",
                    "version": "v0.0.1",
                    "name": "staging",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                }
            ],
        },
        "rf": {
            "name": "rf",
            "commits": {
                "7891d6833470aff9fbbc0c1ceab7d7553c963883": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
                "8e258886c5a182c96ef040b74cf944160b8e7357": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
            },
            "versions": [
                {
                    "artifact": "rf",
                    "name": "v1.2.3",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 37),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
                {
                    "artifact": "rf",
                    "name": "v1.2.4",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
            ],
            "labels": [
                {
                    "artifact": "rf",
                    "version": "v1.2.3",
                    "name": "production",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
                {
                    "artifact": "rf",
                    "version": "v1.2.4",
                    "name": "staging",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 39),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
                {
                    "artifact": "rf",
                    "version": "v1.2.4",
                    "name": "production",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 40),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
                {
                    "artifact": "rf",
                    "version": "v1.2.3",
                    "name": "production",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 41),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
            ],
        },
    }
}


def iter_over(sequence):
    if isinstance(sequence, dict):
        return list(sequence.values())
    if isinstance(sequence, list):
        return sequence
    raise NotImplementedError


def test_registry_state_tag_tag(showcase):
    path, repo, write_file, first_commit, second_commit = showcase
    reg = GitRegistry.from_repo(repo)
    state = reg.state.dict()

    exclude = {
        "commits": [],
        "versions": ["author", "creation_date", "commit_hexsha"],
        "labels": ["author", "creation_date", "commit_hexsha"],
    }

    for name in ["features", "nn", "rf"]:

        for part in "commits", "versions", "labels":
            for appeared, expected in zip(
                iter_over(state["artifacts"][name][part]),
                iter_over(EXPECTED_REGISTRY_TAG_TAG_STATE["artifacts"][name][part]),
            ):
                _check_dict(appeared, expected, exclude[part])


EXPECTED_REGISTRY_COMMIT_BRANCH_STATE = {
    "artifacts": {
        "features": {
            "name": "features",
            "commits": {
                "7891d6833470aff9fbbc0c1ceab7d7553c963883": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
                "8e258886c5a182c96ef040b74cf944160b8e7357": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
            },
            "versions": [
                {
                    "artifact": "features",
                    "name": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 37),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
                {
                    "artifact": "features",
                    "name": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
            ],
            "labels": [
                {
                    "artifact": "features",
                    "version": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 37),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
                {
                    "artifact": "features",
                    "version": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
            ],
        },
        "nn": {
            "name": "nn",
            "commits": {
                "7891d6833470aff9fbbc0c1ceab7d7553c963883": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
                "8e258886c5a182c96ef040b74cf944160b8e7357": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
            },
            "versions": [
                {
                    "artifact": "nn",
                    "name": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 37),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
                {
                    "artifact": "nn",
                    "name": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
            ],
            "labels": [
                {
                    "artifact": "nn",
                    "version": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 37),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
                {
                    "artifact": "nn",
                    "version": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
            ],
        },
        "rf": {
            "name": "rf",
            "commits": {
                "7891d6833470aff9fbbc0c1ceab7d7553c963883": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
                "8e258886c5a182c96ef040b74cf944160b8e7357": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
            },
            "versions": [
                {
                    "artifact": "rf",
                    "name": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 37),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
                {
                    "artifact": "rf",
                    "name": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
            ],
            "labels": [
                {
                    "artifact": "rf",
                    "version": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 37),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "8e258886c5a182c96ef040b74cf944160b8e7357",
                    "deprecated_date": None,
                },
                {
                    "artifact": "rf",
                    "version": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 25, 20, 9, 38),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "7891d6833470aff9fbbc0c1ceab7d7553c963883",
                    "deprecated_date": None,
                },
            ],
        },
    }
}


def test_registry_state_commit_branch(showcase):
    from gto.config import CONFIG  # pylint: disable=import-outside-toplevel

    CONFIG.VERSION_BASE = "commit"
    CONFIG.ENV_BASE = "branch"

    path, repo, write_file, first_commit, second_commit = showcase
    reg = GitRegistry.from_repo(repo, CONFIG)
    state = reg.state.dict()

    exclude = {
        "commits": [],
        "versions": ["author", "creation_date", "commit_hexsha", "name"],
        "labels": ["author", "creation_date", "commit_hexsha", "version"],
    }

    for name in ["features", "nn", "rf"]:

        for part in "commits", "versions", "labels":
            for appeared, expected in zip(
                iter_over(state["artifacts"][name][part]),
                iter_over(
                    EXPECTED_REGISTRY_COMMIT_BRANCH_STATE["artifacts"][name][part]
                ),
            ):
                _check_dict(appeared, expected, exclude[part])
