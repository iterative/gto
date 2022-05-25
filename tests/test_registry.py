# pylint: disable=unused-variable
from gto.registry import GitRegistry

from .utils import _check_dict

EXPECTED_REGISTRY_TAG_TAG_STATE = {
    "artifacts": {
        "nn": {
            "versions": [
                {
                    "artifact": "nn",
                    "name": "v0.0.1",
                    "created_at": "2022-04-11T21:51:56",
                    "author": "Alexander Guschin",
                    "author_email": "1aguschin@gmail.com",
                    "commit_hexsha": "d1d973669cade722f2900e75379cee42fe6b0244",
                    "discovered": False,
                    "tag": "nn@v0.0.1",
                    "promotions": [
                        {
                            "artifact": "nn",
                            "version": "v0.0.1",
                            "stage": "staging",
                            "created_at": "2022-04-11T21:51:57",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "commit_hexsha": "d1d973669cade722f2900e75379cee42fe6b0244",
                            "tag": "nn#staging#1",
                        }
                    ],
                    "enrichments": [
                        {
                            "source": "gto",
                            "artifact": {
                                "type": "model",
                                "name": "nn",
                                "path": "models/neural-network.pkl",
                                "virtual": False,
                                "labels": [],
                                "description": "",
                            },
                        }
                    ],
                }
            ],
        },
        "rf": {
            "versions": [
                {
                    "artifact": "rf",
                    "name": "v1.2.3",
                    "created_at": "2022-04-11T21:51:56",
                    "author": "Alexander Guschin",
                    "author_email": "1aguschin@gmail.com",
                    "commit_hexsha": "d1d973669cade722f2900e75379cee42fe6b0244",
                    "discovered": False,
                    "tag": "rf@v1.2.3",
                    "promotions": [
                        {
                            "artifact": "rf",
                            "version": "v1.2.3",
                            "stage": "production",
                            "created_at": "2022-04-11T21:51:57",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "commit_hexsha": "d1d973669cade722f2900e75379cee42fe6b0244",
                            "tag": "rf#production#1",
                        },
                        {
                            "artifact": "rf",
                            "version": "v1.2.3",
                            "stage": "production",
                            "created_at": "2022-04-11T21:52:01",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "commit_hexsha": "d1d973669cade722f2900e75379cee42fe6b0244",
                            "tag": "rf#production#4",
                        },
                    ],
                    "enrichments": [
                        {
                            "source": "gto",
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                                "labels": [],
                                "description": "",
                            },
                        }
                    ],
                },
                {
                    "artifact": "rf",
                    "name": "v1.2.4",
                    "created_at": "2022-04-12T19:03:44",
                    "author": "Alexander Guschin",
                    "author_email": "1aguschin@gmail.com",
                    "commit_hexsha": "16b7b77f1219ea3c10ae5beeb8473fb49cbd8c13",
                    "discovered": False,
                    "tag": "rf@v1.2.4",
                    "promotions": [
                        {
                            "artifact": "rf",
                            "version": "v1.2.4",
                            "stage": "staging",
                            "created_at": "2022-04-11T21:51:58",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "commit_hexsha": "16b7b77f1219ea3c10ae5beeb8473fb49cbd8c13",
                            "tag": "rf#staging#2",
                        },
                        {
                            "artifact": "rf",
                            "version": "v1.2.4",
                            "stage": "production",
                            "created_at": "2022-04-11T21:51:59",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "commit_hexsha": "16b7b77f1219ea3c10ae5beeb8473fb49cbd8c13",
                            "tag": "rf#production#3",
                        },
                        {
                            "artifact": "rf",
                            "version": "v1.2.4",
                            "stage": "stagegeg",
                            "created_at": "2022-04-12T19:26:08",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "commit_hexsha": "16b7b77f1219ea3c10ae5beeb8473fb49cbd8c13",
                            "tag": "rf#stagegeg#5",
                        },
                    ],
                    "enrichments": [
                        {
                            "source": "gto",
                            "artifact": {
                                "type": "model",
                                "name": "rf",
                                "path": "models/random-forest.pkl",
                                "virtual": False,
                                "labels": [],
                                "description": "",
                            },
                        }
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
    for name in expected_state["artifacts"]:
        for part in ["versions"]:  # "commits"
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
    state = reg.get_state().dict()

    # TODO: update state
    exclude = {
        "commits": [],
        "versions": [
            "author",
            "author_email",
            "created_at",
            "commit_hexsha",
            "promotions",
            "enrichments",
            "message",
        ],
        "promotions": [
            "author",
            "author_email",
            "created_at",
            "commit_hexsha",
            "message",
        ],
    }

    _check_state(state, EXPECTED_REGISTRY_TAG_TAG_STATE, exclude)
