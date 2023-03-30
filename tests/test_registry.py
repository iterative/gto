# pylint: disable=unused-variable, too-many-locals
from gto.registry import GitRegistry

from .utils import check_obj

EXPECTED_REGISTRY_TAG_TAG_STATE = {
    "artifacts": {
        "nn": {
            "artifact": "nn",
            "versions": [
                {
                    "artifact": "nn",
                    "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
                    "version": "v0.0.1",
                    "registrations": [
                        {
                            "priority": 3,
                            "addition": True,
                            "artifact": "nn",
                            "created_at": "2023-03-30T17:29:52",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Registering artifact nn version v0.0.1",
                            "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
                            "tag": "nn@v0.0.1",
                            "version": "v0.0.1",
                        }
                    ],
                    "deregistrations": [],
                    "stages": {
                        "staging": {
                            "artifact": "nn",
                            "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
                            "version": "v0.0.1",
                            "stage": "staging",
                            "assignments": [
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "nn",
                                    "created_at": "2023-03-30T17:29:53",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage staging to artifact nn version v0.0.1",
                                    "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
                                    "tag": "nn#staging#1",
                                    "version": "v0.0.1",
                                    "stage": "staging",
                                }
                            ],
                            "unassignments": [],
                        }
                    },
                }
            ],
            "creations": [],
            "deprecations": [],
        },
        "rf": {
            "artifact": "rf",
            "versions": [
                {
                    "artifact": "rf",
                    "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
                    "version": "v1.2.3",
                    "registrations": [
                        {
                            "priority": 3,
                            "addition": True,
                            "artifact": "rf",
                            "created_at": "2023-03-30T17:29:52",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Registering artifact rf version v1.2.3",
                            "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
                            "tag": "rf@v1.2.3",
                            "version": "v1.2.3",
                        }
                    ],
                    "deregistrations": [],
                    "stages": {
                        "production": {
                            "artifact": "rf",
                            "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
                            "version": "v1.2.3",
                            "stage": "production",
                            "assignments": [
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "rf",
                                    "created_at": "2023-03-30T17:29:53",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage production to artifact rf version v1.2.3",
                                    "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
                                    "tag": "rf#production#1",
                                    "version": "v1.2.3",
                                    "stage": "production",
                                },
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "rf",
                                    "created_at": "2023-03-30T17:29:57",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage production to artifact rf version v1.2.3",
                                    "commit_hexsha": "94c0ffdbc1606c5afb90a94045f7e998f3c15758",
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
                    "commit_hexsha": "4878ce394d4b121c3af6be3b9779a46756411ddd",
                    "version": "v1.2.4",
                    "registrations": [
                        {
                            "priority": 3,
                            "addition": True,
                            "artifact": "rf",
                            "created_at": "2023-03-30T17:29:53",
                            "author": "Alexander Guschin",
                            "author_email": "1aguschin@gmail.com",
                            "message": "Registering artifact rf version v1.2.4",
                            "commit_hexsha": "4878ce394d4b121c3af6be3b9779a46756411ddd",
                            "tag": "rf@v1.2.4",
                            "version": "v1.2.4",
                        }
                    ],
                    "deregistrations": [],
                    "stages": {
                        "staging": {
                            "artifact": "rf",
                            "commit_hexsha": "4878ce394d4b121c3af6be3b9779a46756411ddd",
                            "version": "v1.2.4",
                            "stage": "staging",
                            "assignments": [
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "rf",
                                    "created_at": "2023-03-30T17:29:54",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage staging to artifact rf version v1.2.4",
                                    "commit_hexsha": "4878ce394d4b121c3af6be3b9779a46756411ddd",
                                    "tag": "rf#staging#2",
                                    "version": "v1.2.4",
                                    "stage": "staging",
                                }
                            ],
                            "unassignments": [],
                        },
                        "production": {
                            "artifact": "rf",
                            "commit_hexsha": "4878ce394d4b121c3af6be3b9779a46756411ddd",
                            "version": "v1.2.4",
                            "stage": "production",
                            "assignments": [
                                {
                                    "priority": 5,
                                    "addition": True,
                                    "artifact": "rf",
                                    "created_at": "2023-03-30T17:29:55",
                                    "author": "Alexander Guschin",
                                    "author_email": "1aguschin@gmail.com",
                                    "message": "Assigning stage production to artifact rf version v1.2.4",
                                    "commit_hexsha": "4878ce394d4b121c3af6be3b9779a46756411ddd",
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
            "stages",
            "message",
            "version",
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

            for key in ["registrations", "deregistrations"]:
                for a, e in zip(
                    iter_over(appeared[key]),
                    iter_over(expected[key]),
                ):
                    check_obj(a, e, exclude[key])

            for key in appeared["stages"]:
                check_obj(
                    appeared["stages"][key], expected["stages"][key], exclude["stages"]
                )
