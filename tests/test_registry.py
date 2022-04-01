# pylint: disable=unused-variable
import datetime

from gto.registry import GitRegistry

from .utils import _check_dict

EXPECTED_REGISTRY_TAG_TAG_STATE = {
    "artifacts": {
        "features": {
            "name": "features",
            "commits": {
                "c6232f2ff38f2efe9768ab58b279e500085c0b0a": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                    "tags": [],
                    "description": "",
                },
                "1570672b226558a3614c1a7f21295553102a2869": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                    "tags": [],
                    "description": "",
                },
            },
            "versions": [],
        },
        "nn": {
            "name": "nn",
            "commits": {
                "c6232f2ff38f2efe9768ab58b279e500085c0b0a": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                    "tags": [],
                    "description": "",
                },
                "1570672b226558a3614c1a7f21295553102a2869": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                    "tags": [],
                    "description": "",
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                        "tags": [],
                        "description": "",
                    },
                    "name": "v0.0.1",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 47, 59),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "nn",
                                "path": "models/neural-network.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "v0.0.1",
                            "stage": "staging",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                        }
                    ],
                }
            ],
        },
        "rf": {
            "name": "rf",
            "commits": {
                "c6232f2ff38f2efe9768ab58b279e500085c0b0a": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                    "tags": [],
                    "description": "",
                },
                "1570672b226558a3614c1a7f21295553102a2869": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                    "tags": [],
                    "description": "",
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                        "tags": [],
                        "description": "",
                    },
                    "name": "v1.2.3",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 47, 59),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "v1.2.3",
                            "stage": "production",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                        },
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "v1.2.3",
                            "stage": "production",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 48, 3),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                        },
                    ],
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                        "tags": [],
                        "description": "",
                    },
                    "name": "v1.2.4",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "v1.2.4",
                            "stage": "staging",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 48, 1),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                        },
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "v1.2.4",
                            "stage": "production",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 48, 2),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
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
                "1570672b226558a3614c1a7f21295553102a2869": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                    "tags": [],
                    "description": "",
                },
                "c6232f2ff38f2efe9768ab58b279e500085c0b0a": {
                    "type": "dataset",
                    "name": "features",
                    "path": "datasets/features.csv",
                    "virtual": True,
                    "tags": [],
                    "description": "",
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "dataset",
                        "name": "features",
                        "path": "datasets/features.csv",
                        "virtual": True,
                        "tags": [],
                        "description": "",
                    },
                    "name": "1570672b226558a3614c1a7f21295553102a2869",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 47, 59),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "dataset",
                                "name": "features",
                                "path": "datasets/features.csv",
                                "virtual": True,
                                "tags": [],
                                "description": "",
                            },
                            "version": "1570672b226558a3614c1a7f21295553102a2869",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 47, 59),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                        }
                    ],
                },
                {
                    "artifact": {
                        "type": "dataset",
                        "name": "features",
                        "path": "datasets/features.csv",
                        "virtual": True,
                        "tags": [],
                        "description": "",
                    },
                    "name": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "dataset",
                                "name": "features",
                                "path": "datasets/features.csv",
                                "virtual": True,
                                "tags": [],
                                "description": "",
                            },
                            "version": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                        }
                    ],
                },
            ],
        },
        "nn": {
            "name": "nn",
            "commits": {
                "1570672b226558a3614c1a7f21295553102a2869": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                    "tags": [],
                    "description": "",
                },
                "c6232f2ff38f2efe9768ab58b279e500085c0b0a": {
                    "type": "model",
                    "name": "nn",
                    "path": "models/neural-network.pkl",
                    "virtual": False,
                    "tags": [],
                    "description": "",
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                        "tags": [],
                        "description": "",
                    },
                    "name": "1570672b226558a3614c1a7f21295553102a2869",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 47, 59),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "nn",
                                "path": "models/neural-network.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "1570672b226558a3614c1a7f21295553102a2869",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 47, 59),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                        }
                    ],
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "nn",
                        "path": "models/neural-network.pkl",
                        "virtual": False,
                        "tags": [],
                        "description": "",
                    },
                    "name": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "nn",
                                "path": "models/neural-network.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                        }
                    ],
                },
            ],
        },
        "rf": {
            "name": "rf",
            "commits": {
                "1570672b226558a3614c1a7f21295553102a2869": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                    "tags": [],
                    "description": "",
                },
                "c6232f2ff38f2efe9768ab58b279e500085c0b0a": {
                    "type": "model",
                    "name": "rf",
                    "path": "models/random-forest.pkl",
                    "virtual": False,
                    "tags": [],
                    "description": "",
                },
            },
            "versions": [
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                        "tags": [],
                        "description": "",
                    },
                    "name": "1570672b226558a3614c1a7f21295553102a2869",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 47, 59),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "1570672b226558a3614c1a7f21295553102a2869",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 47, 59),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "1570672b226558a3614c1a7f21295553102a2869",
                        }
                    ],
                },
                {
                    "artifact": {
                        "type": "model",
                        "name": "rf",
                        "path": "models/random-forest.pkl",
                        "virtual": False,
                        "tags": [],
                        "description": "",
                    },
                    "name": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                    "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                    "author": "Alexander Guschin",
                    "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                    "promotions": [
                        {
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                                "tags": [],
                                "description": "",
                            },
                            "version": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
                            "stage": "master",
                            "creation_date": datetime.datetime(2022, 4, 1, 17, 48),
                            "author": "Alexander Guschin",
                            "commit_hexsha": "c6232f2ff38f2efe9768ab58b279e500085c0b0a",
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
    CONFIG.STAGE_BASE = "branch"

    path, repo, write_file, first_commit, second_commit = showcase
    reg = GitRegistry.from_repo(repo, CONFIG)
    state = reg.state.dict()

    exclude = {
        "commits": [],
        "versions": ["author", "creation_date", "commit_hexsha", "name", "promotions"],
        "promotions": ["author", "creation_date", "commit_hexsha", "version"],
    }

    _check_state(state, EXPECTED_REGISTRY_COMMIT_BRANCH_STATE, exclude)
