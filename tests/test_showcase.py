"""TODO: break this file into multiple test/files"""
# pylint: disable=unused-variable, too-many-locals, too-many-statements
import gto
from gto.base import BaseArtifact, BaseAssignment, BaseVersion
from tests.utils import _check_obj


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
    assert isinstance(nn_artifact, BaseArtifact)
    assert nn_artifact.name == "nn"
    assert len(nn_artifact.versions) == 2
    nn_version = nn_artifact.versions[0]
    assert isinstance(nn_version, BaseVersion)
    author = repo.commit().author.name
    author_email = repo.commit().author.email

    skip_keys_registration = {
        "created_at",
        "assignments",
        "enrichments",
        "tag",
        "message",
    }
    skip_keys_assignment = {"created_at", "tag", "message"}

    _check_obj(
        nn_version,
        dict(
            artifact="nn",
            name="v0.0.1",
            author=author,
            author_email=author_email,
            commit_hexsha=first_commit.hexsha,
            discovered=False,
        ),
        skip_keys=skip_keys_registration,
    )
    assert len(nn_artifact.stages) == 1
    nn_assignment = nn_artifact.stages[0]
    assert isinstance(nn_assignment, BaseAssignment)
    _check_obj(
        nn_assignment,
        dict(
            artifact="nn",
            version="v0.0.1",
            stage="staging",
            author=author,
            author_email=author_email,
            commit_hexsha=first_commit.hexsha,
        ),
        skip_keys=skip_keys_assignment,
    )

    rf_artifact = artifacts["rf"]
    assert isinstance(rf_artifact, BaseArtifact)
    assert rf_artifact.name == "rf"

    assert len(rf_artifact.versions) == 2
    assert all(isinstance(v, BaseVersion) for v in rf_artifact.versions)
    rf_ver1, rf_ver2 = rf_artifact.versions
    _check_obj(
        rf_ver1,
        dict(
            artifact="rf",
            name="v1.2.3",
            author=author,
            author_email=author_email,
            commit_hexsha=first_commit.hexsha,
            discovered=False,
        ),
        skip_keys=skip_keys_registration,
    )
    _check_obj(
        rf_ver2,
        dict(
            artifact="rf",
            name="v1.2.4",
            author=author,
            author_email=author_email,
            commit_hexsha=second_commit.hexsha,
            discovered=False,
        ),
        skip_keys=skip_keys_registration,
    )

    assert len(rf_artifact.stages) == 4
    assert all(isinstance(p, BaseAssignment) for p in rf_artifact.stages)
    rf_l1, _ = rf_ver1.assignments
    rf_l3, rf_l4 = rf_ver2.assignments

    _check_obj(
        rf_l1,
        dict(
            artifact="rf",
            version="v1.2.3",
            stage="production",
            author=author,
            author_email=author_email,
            commit_hexsha=first_commit.hexsha,
        ),
        skip_keys=skip_keys_assignment,
    )
    _check_obj(
        rf_l4,
        dict(
            artifact="rf",
            version="v1.2.4",
            stage="production",
            author=author,
            author_email=author_email,
            commit_hexsha=second_commit.hexsha,
        ),
        skip_keys=skip_keys_assignment,
    )
    _check_obj(
        rf_l3,
        dict(
            artifact="rf",
            version="v1.2.4",
            stage="staging",
            author=author,
            author_email=author_email,
            commit_hexsha=second_commit.hexsha,
        ),
        skip_keys=skip_keys_assignment,
    )
    assert gto.api.find_versions_in_stage(repo, "rf", "staging", all=True) == [rf_l3]
