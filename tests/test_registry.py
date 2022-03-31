# pylint: disable=unused-variable
import datetime

from gto.registry import GitRegistry

from .utils import _check_dict

EXPECTED_REGISTRY_TAG_TAG_STATE = {
    "artifacts": {
        "features": {
            "name": "features",
            "commits": {
                "ebd7f363cc0a012d9fe9bd22289051a0d9383204": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
                "4015b096b8cb7c4d820bb5346922957a1ec8ff06": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
            },
            "versions": [],
        },
        "nn": {
            "name": "nn",
            "commits": {
                "ebd7f363cc0a012d9fe9bd22289051a0d9383204": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
                "4015b096b8cb7c4d820bb5346922957a1ec8ff06": {
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
                    "creation_date": datetime.datetime(2022, 3, 31, 13, 33, 33),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "ebd7f363cc0a012d9fe9bd22289051a0d9383204",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "nn",
                                "path": "models/neural-network.pkl",
                                "virtual": False,
                            },
                            "version": "v0.0.1",
                            "stage": "staging",
                            "creation_date": datetime.datetime(2022, 3, 31, 13, 33, 34),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "ebd7f363cc0a012d9fe9bd22289051a0d9383204",
                            "deprecated_date": None,
                        }
                    ],
                }
            ],
        },
        "rf": {
            "name": "rf",
            "commits": {
                "ebd7f363cc0a012d9fe9bd22289051a0d9383204": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
                "4015b096b8cb7c4d820bb5346922957a1ec8ff06": {
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
                    "creation_date": datetime.datetime(2022, 3, 31, 13, 33, 33),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "ebd7f363cc0a012d9fe9bd22289051a0d9383204",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                            },
                            "version": "v1.2.3",
                            "stage": "production",
                            "creation_date": datetime.datetime(2022, 3, 31, 13, 33, 34),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "ebd7f363cc0a012d9fe9bd22289051a0d9383204",
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
                            "stage": "production",
                            "creation_date": datetime.datetime(2022, 3, 31, 13, 33, 38),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "ebd7f363cc0a012d9fe9bd22289051a0d9383204",
                            "deprecated_date": None,
                        },
                    ],
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "name": "v1.2.4",
                    "creation_date": datetime.datetime(2022, 3, 31, 13, 33, 34),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "4015b096b8cb7c4d820bb5346922957a1ec8ff06",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                            },
                            "version": "v1.2.4",
                            "stage": "staging",
                            "creation_date": datetime.datetime(2022, 3, 31, 13, 33, 35),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "4015b096b8cb7c4d820bb5346922957a1ec8ff06",
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
                            "stage": "production",
                            "creation_date": datetime.datetime(2022, 3, 31, 13, 33, 36),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "4015b096b8cb7c4d820bb5346922957a1ec8ff06",
                            "deprecated_date": None,
                        },
                    ],
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


def _check_state(appread_state, expected_state, exclude):

    for name in ["features", "nn", "rf"]:
        for part in ["commits", "versions"]:
            for appeared, expected in zip(
                iter_over(appread_state["artifacts"][name][part]),
                iter_over(expected_state["artifacts"][name][part]),
            ):
                _check_dict(appeared, expected, exclude[part])
        for appeared, expected in zip(
            appread_state["artifacts"][name]["versions"],
            expected_state["artifacts"][name]["versions"],
        ):
            for a, e in zip(appeared["promotions"], expected["promotions"]):
                _check_dict(a, e, exclude["promotions"])


def test_registry_state_tag_tag(showcase):
    path, repo, write_file, first_commit, second_commit = showcase
    reg = GitRegistry.from_repo(repo)
    state = reg.state.dict()

    exclude = {
        "commits": [],
        "versions": ["author", "creation_date", "commit_hexsha", "promotions"],
        "promotions": ["author", "creation_date", "commit_hexsha"],
    }

    _check_state(state, EXPECTED_REGISTRY_TAG_TAG_STATE, exclude)


EXPECTED_REGISTRY_COMMIT_BRANCH_STATE = {
    "artifacts": {
        "features": {
            "name": "features",
            "commits": {
                "958010f569f53bf61fdef9eeffd8c89c33352177": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                },
                "98ef927423e1630f56d9fd2563a75c49db7092e7": {
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
                    "name": "958010f569f53bf61fdef9eeffd8c89c33352177",
                    "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 10),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "958010f569f53bf61fdef9eeffd8c89c33352177",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "dataset",
                                "name": "features",
                                "path": "datasets/features.csv",
                                "virtual": True,
                            },
                            "version": "958010f569f53bf61fdef9eeffd8c89c33352177",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 10),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "958010f569f53bf61fdef9eeffd8c89c33352177",
                            "deprecated_date": None,
                        }
                    ],
                },
                {
                    "artifact": {
                        "type": "dataset",
                        "name": "features",
                        "path": "datasets/features.csv",
                        "virtual": True,
                    },
                    "name": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                    "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 11),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "dataset",
                                "name": "features",
                                "path": "datasets/features.csv",
                                "virtual": True,
                            },
                            "version": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 11),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                            "deprecated_date": None,
                        }
                    ],
                },
            ],
        },
        "nn": {
            "name": "nn",
            "commits": {
                "958010f569f53bf61fdef9eeffd8c89c33352177": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                },
                "98ef927423e1630f56d9fd2563a75c49db7092e7": {
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
                    "name": "958010f569f53bf61fdef9eeffd8c89c33352177",
                    "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 10),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "958010f569f53bf61fdef9eeffd8c89c33352177",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "nn",
                                "path": "models/neural-network.pkl",
                                "virtual": False,
                            },
                            "version": "958010f569f53bf61fdef9eeffd8c89c33352177",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 10),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "958010f569f53bf61fdef9eeffd8c89c33352177",
                            "deprecated_date": None,
                        }
                    ],
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                    },
                    "name": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                    "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 11),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "nn",
                                "path": "models/neural-network.pkl",
                                "virtual": False,
                            },
                            "version": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 11),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                            "deprecated_date": None,
                        }
                    ],
                },
            ],
        },
        "rf": {
            "name": "rf",
            "commits": {
                "958010f569f53bf61fdef9eeffd8c89c33352177": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                },
                "98ef927423e1630f56d9fd2563a75c49db7092e7": {
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
                    "name": "958010f569f53bf61fdef9eeffd8c89c33352177",
                    "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 10),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "958010f569f53bf61fdef9eeffd8c89c33352177",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                            },
                            "version": "958010f569f53bf61fdef9eeffd8c89c33352177",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 10),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "958010f569f53bf61fdef9eeffd8c89c33352177",
                            "deprecated_date": None,
                        }
                    ],
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                    },
                    "name": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                    "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 11),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                    "deprecated_date": None,
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                            },
                            "version": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 3, 31, 14, 31, 11),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "98ef927423e1630f56d9fd2563a75c49db7092e7",
                            "deprecated_date": None,
                        }
                    ],
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
        "versions": ["author", "creation_date", "commit_hexsha", "name", "promotions"],
        "promotions": ["author", "creation_date", "commit_hexsha", "version"],
    }

    _check_state(state, EXPECTED_REGISTRY_COMMIT_BRANCH_STATE, exclude)
