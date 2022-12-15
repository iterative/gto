# pylint: disable=unused-variable, too-many-locals
from gto.registry import GitRegistry

from .utils import check_obj

EXPECTED_REGISTRY_TAG_TAG_STATE = {
    "artifacts": {
        "rf": {
            "artifact": "rf",
            "versions": [
                {
                    "artifact": "rf",
                    "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                    "version": "v1.2.3",
                    "enrichments": [
                        {
                            "priority": 0,
                            "addition": True,
                            "artifact": "rf",
                            "created_at": "2022-08-04T16:56:57",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Add artifacts",
                            "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                            "version": "v1.2.3",
                            "enrichments": [
                                {
                                    "source": "gto",
                                    "artifact": {
                                        "type": "model",
                                        "path": "models/random-forest.pkl",
                                        "virtual": False,
                                        "labels": [],
                                        "description": "",
                                        "custom": None,
                                    },
                                }
                            ],
                            "committer": "Alexander Guschin",
                            "committer_email": "1aguschin@gmail.com",
                        }
                    ],
                    "registrations": [
                        {
                            "priority": 3,
                            "addition": True,
                            "artifact": "rf",
                            "created_at": "2022-08-04T16:56:57",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Registering artifact rf version v1.2.3",
                            "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                            "tag": "rf@v1.2.3",
                            "version": "v1.2.3",
                        }
                    ],
                    "deregistrations": [],
                    "stages": {
                        "production": {
                            "artifact": "rf",
                            "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                            "version": "v1.2.3",
                            "stage": "production",
                            "assignments": [
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "rf",
                                    "created_at": "2022-08-04T16:56:59",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage production to artifact rf version v1.2.3",
                                    "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                                    "tag": "rf#production#1",
                                    "version": "v1.2.3",
                                    "stage": "production",
                                },
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "rf",
                                    "created_at": "2022-08-04T16:57:02",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage production to artifact rf version v1.2.3",
                                    "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                                    "tag": "rf#production#4",
                                    "version": "v1.2.3",
                                    "stage": "production",
                                },
                            ],
                            "unassignments": [],
                        }
                    },
                },
                {
                    "artifact": "rf",
                    "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                    "version": "v1.2.4",
                    "enrichments": [
                        {
                            "priority": 0,
                            "addition": True,
                            "artifact": "rf",
                            "created_at": "2022-08-04T16:56:59",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Update model",
                            "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                            "version": "v1.2.4",
                            "enrichments": [
                                {
                                    "source": "gto",
                                    "artifact": {
                                        "type": "model",
                                        "path": "models/random-forest.pkl",
                                        "virtual": False,
                                        "labels": [],
                                        "description": "",
                                        "custom": None,
                                    },
                                }
                            ],
                            "committer": "Alexander Guschin",
                            "committer_email": "1aguschin@gmail.com",
                        }
                    ],
                    "registrations": [
                        {
                            "priority": 3,
                            "addition": True,
                            "artifact": "rf",
                            "created_at": "2022-08-04T16:56:59",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Registering artifact rf version v1.2.4",
                            "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                            "tag": "rf@v1.2.4",
                            "version": "v1.2.4",
                        }
                    ],
                    "deregistrations": [],
                    "stages": {
                        "staging": {
                            "artifact": "rf",
                            "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                            "version": "v1.2.4",
                            "stage": "staging",
                            "assignments": [
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "rf",
                                    "created_at": "2022-08-04T16:57:00",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage staging to artifact rf version v1.2.4",
                                    "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                                    "tag": "rf#staging#2",
                                    "version": "v1.2.4",
                                    "stage": "staging",
                                }
                            ],
                            "unassignments": [],
                        },
                        "production": {
                            "artifact": "rf",
                            "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                            "version": "v1.2.4",
                            "stage": "production",
                            "assignments": [
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "rf",
                                    "created_at": "2022-08-04T16:57:01",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage production to artifact rf version v1.2.4",
                                    "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                                    "tag": "rf#production#3",
                                    "version": "v1.2.4",
                                    "stage": "production",
                                }
                            ],
                            "unassignments": [],
                        },
                    },
                },
            ],
            "creations": [],
            "deprecations": [],
        },
        "nn": {
            "artifact": "nn",
            "versions": [
                {
                    "artifact": "nn",
                    "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                    "version": "v0.0.1",
                    "enrichments": [
                        {
                            "priority": 0,
                            "addition": True,
                            "artifact": "nn",
                            "created_at": "2022-08-04T16:56:57",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Add artifacts",
                            "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                            "version": "v0.0.1",
                            "enrichments": [
                                {
                                    "source": "gto",
                                    "artifact": {
                                        "type": "model",
                                        "path": "models/neural-network.pkl",
                                        "virtual": False,
                                        "labels": [],
                                        "description": "",
                                        "custom": None,
                                    },
                                }
                            ],
                            "committer": "Alexander Guschin",
                            "committer_email": "1aguschin@gmail.com",
                        }
                    ],
                    "registrations": [
                        {
                            "priority": 3,
                            "addition": True,
                            "artifact": "nn",
                            "created_at": "2022-08-04T16:56:58",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Registering artifact nn version v0.0.1",
                            "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                            "tag": "nn@v0.0.1",
                            "version": "v0.0.1",
                        }
                    ],
                    "deregistrations": [],
                    "stages": {
                        "staging": {
                            "artifact": "nn",
                            "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                            "version": "v0.0.1",
                            "stage": "staging",
                            "assignments": [
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "nn",
                                    "created_at": "2022-08-04T16:56:59",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage staging to artifact nn version v0.0.1",
                                    "commit_hexsha": "89de382074d472f8e6b8fd654490183c3c0fb497",
                                    "tag": "nn#staging#1",
                                    "version": "v0.0.1",
                                    "stage": "staging",
                                }
                            ],
                            "unassignments": [],
                        }
                    },
                },
                {
                    "artifact": "nn",
                    "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                    "version": "04d79900801d9aa7ec726169706280a32a25d198",
                    "enrichments": [
                        {
                            "priority": 0,
                            "addition": True,
                            "artifact": "nn",
                            "created_at": "2022-08-04T16:56:59",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Update model",
                            "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                            "version": "04d79900801d9aa7ec726169706280a32a25d198",
                            "enrichments": [
                                {
                                    "source": "gto",
                                    "artifact": {
                                        "type": "model",
                                        "path": "models/neural-network.pkl",
                                        "virtual": False,
                                        "labels": [],
                                        "description": "",
                                        "custom": None,
                                    },
                                }
                            ],
                            "committer": "Alexander Guschin",
                            "committer_email": "1aguschin@gmail.com",
                        }
                    ],
                    "registrations": [],
                    "deregistrations": [],
                    "stages": {},
                },
            ],
            "creations": [],
            "deprecations": [],
        },
        "features": {
            "artifact": "features",
            "versions": [
                {
                    "artifact": "features",
                    "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                    "version": "04d79900801d9aa7ec726169706280a32a25d198",
                    "enrichments": [
                        {
                            "priority": 0,
                            "addition": True,
                            "artifact": "features",
                            "created_at": "2022-08-04T16:56:59",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Update model",
                            "commit_hexsha": "04d79900801d9aa7ec726169706280a32a25d198",
                            "version": "04d79900801d9aa7ec726169706280a32a25d198",
                            "enrichments": [
                                {
                                    "source": "gto",
                                    "artifact": {
                                        "type": "dataset",
                                        "path": "datasets/features.csv",
                                        "virtual": True,
                                        "labels": [],
                                        "description": "",
                                        "custom": None,
                                    },
                                }
                            ],
                            "committer": "Alexander Guschin",
                            "committer_email": "1aguschin@gmail.com",
                        }
                    ],
                    "registrations": [],
                    "deregistrations": [],
                    "stages": {},
                }
            ],
            "creations": [],
            "deprecations": [],
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
    with GitRegistry.from_repo(repo) as reg:
        appeared_state = reg.get_state().dict()

    # TODO: update state
    exclude = {
        "commits": [],
        "versions": [
            "author",
            "author_email",
            "created_at",
            "commit_hexsha",
            "registrations",
            "deregistrations",
            "enrichments",
            "stages",
            "message",
            "version",
        ],
        "enrichments": [
            "author",
            "author_email",
            "created_at",
            "commit_hexsha",
            "message",
            "version",
            "committer",
            "committer_email",
        ],
        "registrations": [
            "author",
            "author_email",
            "created_at",
            "commit_hexsha",
            "message",
            "version",
        ],
        "deregistrations": [
            "author",
            "author_email",
            "created_at",
            "commit_hexsha",
            "message",
            "version",
        ],
        "stages": [
            "author",
            "author_email",
            "created_at",
            "commit_hexsha",
            "message",
            "version",
            "assignments",
            "unassignments",
        ],
    }

    expected_state = EXPECTED_REGISTRY_TAG_TAG_STATE
    for artifact in expected_state["artifacts"]:

        for appeared, expected in zip(
            iter_over(appeared_state["artifacts"][artifact]["versions"]),
            iter_over(expected_state["artifacts"][artifact]["versions"]),
        ):
            check_obj(appeared, expected, exclude["versions"])

            for key in ["enrichments", "registrations", "deregistrations"]:
                for a, e in zip(
                    iter_over(appeared[key]),
                    iter_over(expected[key]),
                ):
                    check_obj(a, e, exclude[key])

            for key in appeared["stages"]:
                check_obj(
                    appeared["stages"][key], expected["stages"][key], exclude["stages"]
                )
