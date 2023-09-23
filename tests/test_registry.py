# pylint: disable=too-many-locals
from typing import Dict, List

import pytest
from pytest_mock import MockFixture
from pytest_test_utils import TmpDir
from scmrepo.git import Git

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


@pytest.mark.usefixtures("showcase")
def test_registry_state_tag_tag(tmp_dir: TmpDir):
    with GitRegistry.from_url(tmp_dir) as reg:
        appeared_state = reg.get_state().dict()

    # TODO: update state
    exclude: Dict[str, List[str]] = {
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


def test_from_url_sets_cloned_property(tmp_dir: TmpDir, scm: Git, mocker: MockFixture):
    with GitRegistry.from_url(tmp_dir) as reg:
        assert reg.cloned is False

    with GitRegistry.from_url(scm) as reg:
        assert reg.cloned is False

    cloned_git_repo_mock = mocker.patch("gto.git_utils.cloned_git_repo")
    cloned_git_repo_mock.return_value.__enter__.return_value = scm

    with GitRegistry.from_url("https://github.com/iterative/gto") as reg:
        assert reg.cloned is True


# Some method parameters (model names, versions, revs, etc) depend and set by
# the `showcase` fixture setup in the conftest.py.
@pytest.mark.parametrize(
    "method,args,kwargs",
    [
        ("register", ["new_model", "HEAD"], {}),
        ("deregister", ["nn"], {"version": "v0.0.1"}),
        ("assign", ["nn", "new_stage"], {"version": "v0.0.1"}),
        ("unassign", ["nn", "staging"], {"version": "v0.0.1"}),
        ("deprecate", ["nn"], {}),
    ],
)
@pytest.mark.usefixtures("showcase")
def test_tag_is_pushed_if_cloned_is_set(
    tmp_dir: TmpDir,
    mocker: MockFixture,
    method,
    args,
    kwargs,
):
    with GitRegistry.from_url(tmp_dir) as reg:
        # imitate that we are doing actions on the remote repo
        assert reg.cloned is False
        reg.cloned = True

        # check that it attempts to push tag to a remote repo, even if
        # push=False is set in a call. `cloned` overrides it in this case
        git_push_tag_mock = mocker.patch("gto.registry.git_push_tag")
        kwargs["push"] = False
        getattr(reg, method)(*args, **kwargs)
        git_push_tag_mock.assert_called_once()
