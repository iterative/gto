# pylint: disable=unused-variable
import datetime

from gto.registry import GitRegistry

from .utils import _check_dict

EXPECTED_REGISTRY_TAG_TAG_STATE = {
    "artifacts": {
        "features": {
            "name": "features",
            "commits": {
                "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
                "12b413c033ffc49b6bc8dc782999563504c9767e": {
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
                "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
                "12b413c033ffc49b6bc8dc782999563504c9767e": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                    },
                    "name": "v0.0.1",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                }
            ],
            "labels": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                    },
                    "version": "v0.0.1",
                    "name": "staging",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                }
            ],
        },
        "rf": {
            "name": "rf",
            "commits": {
                "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
                "12b413c033ffc49b6bc8dc782999563504c9767e": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "name": "v1.2.3",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "name": "v1.2.4",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "deprecated_date": None,
                },
            ],
            "labels": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "version": "v1.2.3",
                    "name": "production",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "version": "v1.2.4",
                    "name": "staging",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 50),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "version": "v1.2.4",
                    "name": "production",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 52),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "version": "v1.2.3",
                    "name": "production",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 53),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
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
                "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
                "12b413c033ffc49b6bc8dc782999563504c9767e": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "dataset",
                        "name": "features",
                        "path": "datasets/features.csv",
                        "virtual": True,
                    },
                    "name": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "dataset",
                        "name": "features",
                        "path": "datasets/features.csv",
                        "virtual": True,
                    },
                    "name": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "deprecated_date": None,
                },
            ],
            "labels": [
                {
                    "artifact": {
                        "type": "dataset",
                        "name": "features",
                        "path": "datasets/features.csv",
                        "virtual": True,
                    },
                    "version": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "dataset",
                        "name": "features",
                        "path": "datasets/features.csv",
                        "virtual": True,
                    },
                    "version": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "deprecated_date": None,
                },
            ],
        },
        "nn": {
            "name": "nn",
            "commits": {
                "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
                "12b413c033ffc49b6bc8dc782999563504c9767e": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                    },
                    "name": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                    },
                    "name": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "deprecated_date": None,
                },
            ],
            "labels": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                    },
                    "version": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                    },
                    "version": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "deprecated_date": None,
                },
            ],
        },
        "rf": {
            "name": "rf",
            "commits": {
                "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
                "12b413c033ffc49b6bc8dc782999563504c9767e": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "name": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "name": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "deprecated_date": None,
                },
            ],
            "labels": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "version": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "3508dc2c848f1ea46f6d0f02c298db95ee7a84fd",
                    "deprecated_date": None,
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "version": "12b413c033ffc49b6bc8dc782999563504c9767e",
                    "name": "master",
                    "creation_date": datetime.datetime(2022, 3, 28, 18, 54, 49),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "12b413c033ffc49b6bc8dc782999563504c9767e",
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
