"""TODO: break this file into multiple test/files"""
import gto
from gto.base import BaseArtifact, BaseLabel, BaseVersion
from tests.utils import _check_dict


def test_api(showcase):  # pylint: disable=too-many-locals, too-many-statements
    (
        path,
        repo,
        write_file,  # pylint: disable=unused-variable
        first_commit,
        second_commit,
    ) = showcase

    artifacts = gto.api.get_state(path).artifacts
    assert set(artifacts.keys()) == {"features", "nn", "rf"}
    assert artifacts["features"] == BaseArtifact(
        name="features", versions=[], labels=[]
    )
    nn_artifact = artifacts["nn"]
    assert isinstance(nn_artifact, BaseArtifact)
    assert nn_artifact.name == "nn"
    assert len(nn_artifact.versions) == 1
    nn_version = nn_artifact.versions[0]
    assert isinstance(nn_version, BaseVersion)
    author = repo.commit().author.name
    _check_dict(
        nn_version,
        dict(
            artifact="nn",
            name="v0.0.1",
            author=author,
            commit_hexsha=first_commit.hexsha,
            deprecated_date=None,
        ),
        {"creation_date"},
    )
    assert len(nn_artifact.labels) == 1
    nn_label = nn_artifact.labels[0]
    assert isinstance(nn_label, BaseLabel)
    _check_dict(
        nn_label,
        dict(
            artifact="nn",
            version="v0.0.1",
            name="staging",
            author=author,
            commit_hexsha=first_commit.hexsha,
            deprecated_date=None,
        ),
        {"creation_date"},
    )

    rf_artifact = artifacts["rf"]
    assert isinstance(rf_artifact, BaseArtifact)
    assert rf_artifact.name == "rf"

    assert len(rf_artifact.versions) == 2
    assert all(isinstance(v, BaseVersion) for v in rf_artifact.versions)
    rf_ver1, rf_ver2 = rf_artifact.versions
    _check_dict(
        rf_ver1,
        dict(
            artifact="rf",
            name="v1.2.3",
            author=author,
            commit_hexsha=first_commit.hexsha,
            deprecated_date=None,
        ),
        {"creation_date"},
    )
    _check_dict(
        rf_ver2,
        dict(
            artifact="rf",
            name="v1.2.4",
            author=author,
            commit_hexsha=second_commit.hexsha,
            deprecated_date=None,
        ),
        {"creation_date"},
    )

    assert len(rf_artifact.labels) == 4
    assert all(isinstance(l, BaseLabel) for l in rf_artifact.labels)
    rf_l1, rf_l2, rf_l3, _ = rf_artifact.labels

    _check_dict(
        rf_l1,
        dict(
            artifact="rf",
            version="v1.2.3",
            name="production",
            author=author,
            commit_hexsha=first_commit.hexsha,
            deprecated_date=None,
        ),
        {"creation_date"},
    )
    _check_dict(
        rf_l3,
        dict(
            artifact="rf",
            version="v1.2.4",
            name="production",
            author=author,
            commit_hexsha=second_commit.hexsha,
            deprecated_date=None,
        ),
        {"creation_date"},
    )
    _check_dict(
        rf_l2,
        dict(
            artifact="rf",
            version="v1.2.4",
            name="staging",
            author=author,
            commit_hexsha=second_commit.hexsha,
            deprecated_date=None,
        ),
        {"creation_date"},
    )
