"""TODO: break this file into multiple test/files"""
# pylint: disable=unused-variable, too-many-locals, too-many-statements
import gto
from gto.base import (
    Artifact,
    Assignment,
    Commit,
    Deregistration,
    Registration,
    Unassignment,
    Version,
    VStage,
)
from tests.utils import check_obj


def test_api(showcase):
    (
        path,
        repo,
        write_file,
        first_commit,
        second_commit,
    ) = showcase

    gto.api.show(repo)
    gto.api.history(repo)
    for name in "nn", "rf", "features":
        gto.api.show(repo, name)
        gto.api.history(repo, name)

    artifacts = gto.api._get_state(path).artifacts  # pylint: disable=protected-access
    assert set(artifacts.keys()) == {"nn", "rf", "features"}
    # assert isinstance(artifacts["features"], BaseArtifact)
    # _check_obj(
    #     artifacts["features"],
    #     dict(name="features", versions=[]),
    #     ["commits"],
    # )
    nn_artifact = artifacts["nn"]
    assert isinstance(nn_artifact, Artifact)
    assert nn_artifact.artifact == "nn"
    assert len(nn_artifact.versions) == 2
    nn_version = nn_artifact.versions[0]
    assert isinstance(nn_version, Version)
    author = repo.commit().author.name
    author_email = repo.commit().author.email

    skip_keys_registration = {
        "created_at",
        "activated_at",
        "registrations",
        "deregistrations",
        "enrichments",
        "tag",
        "message",
        "stages",
    }
    skip_keys_assignment = {
        "created_at",
        "message",
        "assignments",
        "unassignments",
        "activated_at",
        "priority",
        "addition",
        "event",
    }

    check_obj(
        nn_version.dict_state(),
        dict(
            artifact="nn",
            version="v0.0.1",
            author=author,
            author_email=author_email,
            commit_hexsha=first_commit.hexsha,
            discovered=False,
            is_active=True,
            ref="nn@v0.0.1",
        ),
        skip_keys=skip_keys_registration,
    )
    nn_vstages = nn_artifact.get_vstages()
    assert len(nn_vstages) == 1
    assert isinstance(nn_vstages["staging"][0], VStage)
    check_obj(
        nn_vstages["staging"][0].dict_state(),
        dict(
            artifact="nn",
            version="v0.0.1",
            stage="staging",
            is_active=True,
            ref="nn#staging#1",
            author=author,
            author_email=author_email,
            commit_hexsha=first_commit.hexsha,
        ),
        skip_keys=skip_keys_assignment,
    )

    rf_artifact = artifacts["rf"]
    assert isinstance(rf_artifact, Artifact)
    assert rf_artifact.artifact == "rf"

    assert len(rf_artifact.versions) == 2
    assert all(isinstance(v, Version) for v in rf_artifact.versions)
    rf_ver1, rf_ver2 = rf_artifact.versions
    check_obj(
        rf_ver1.dict_state(),
        dict(
            artifact="rf",
            version="v1.2.3",
            is_active=True,
            ref="rf@v1.2.3",
            author=author,
            author_email=author_email,
            commit_hexsha=first_commit.hexsha,
            discovered=False,
        ),
        skip_keys=skip_keys_registration,
    )
    check_obj(
        rf_ver2.dict_state(),
        dict(
            artifact="rf",
            version="v1.2.4",
            is_active=True,
            ref="rf@v1.2.4",
            author=author,
            author_email=author_email,
            commit_hexsha=second_commit.hexsha,
            discovered=False,
        ),
        skip_keys=skip_keys_registration,
    )

    assert len(rf_artifact.get_events()) == 8
    assert all(
        isinstance(p, (Assignment, Unassignment, Registration, Deregistration, Commit))
        for p in rf_artifact.get_events()
    )
    assert all(
        isinstance(p, (Registration, Deregistration))
        for p in rf_ver1.get_events(indirect=False) + rf_ver2.get_events(indirect=False)
    )
    assert all(
        isinstance(p, (Assignment, Unassignment, Commit))
        for p in rf_ver1.get_events(direct=False) + rf_ver2.get_events(direct=False)
    )
    rf_a4, rf_a1, rf_c1 = rf_ver1.get_events(
        direct=False
    )  # pylint: disable=unused-variable
    rf_a3, rf_a2, rf_c2 = rf_ver2.get_events(
        direct=False
    )  # pylint: disable=unused-variable

    check_obj(
        rf_a1.dict_state(),
        dict(
            artifact="rf",
            version="v1.2.3",
            stage="production",
            tag="rf#production#1",
            author=author,
            author_email=author_email,
            commit_hexsha=first_commit.hexsha,
        ),
        skip_keys=skip_keys_assignment,
    )
    check_obj(
        rf_a3.dict_state(),
        dict(
            artifact="rf",
            version="v1.2.4",
            stage="production",
            tag="rf#production#3",
            author=author,
            author_email=author_email,
            commit_hexsha=second_commit.hexsha,
        ),
        skip_keys=skip_keys_assignment,
    )
    check_obj(
        rf_a2.dict_state(),
        dict(
            artifact="rf",
            version="v1.2.4",
            stage="staging",
            tag="rf#staging#2",
            author=author,
            author_email=author_email,
            commit_hexsha=second_commit.hexsha,
        ),
        skip_keys=skip_keys_assignment,
    )
