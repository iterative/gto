"""TODO: break this file into multiple test/files"""
# pylint: disable=unused-variable, too-many-locals, too-many-statements
import gto
from gto.base import BaseArtifact, BasePromotion, BaseVersion
from tests.utils import _check_obj


def test_api(showcase):
    (
        path,
        repo,
        write_file,
        first_commit,
        second_commit,
    ) = showcase

    artifacts = gto.api._get_state(path).artifacts  # pylint: disable=protected-access
    assert set(artifacts.keys()) == {"nn", "rf"}
    nn_artifact = artifacts["nn"]
    assert isinstance(nn_artifact, BaseArtifact)
    assert nn_artifact.name == "nn"
    assert len(nn_artifact.versions) == 1
    nn_version = nn_artifact.versions[0]
    assert isinstance(nn_version, BaseVersion)
    author = repo.commit().author.name
    _check_obj(
        nn_version,
        dict(
            artifact="nn",
            name="v0.0.1",
            author=author,
            commit_hexsha=first_commit.hexsha,
            discovered=False,
        ),
        # TODO: remove tag, details here and everywhere
        {"creation_date", "promotions", "enrichments", "tag", "details"},
    )
    assert len(nn_artifact.stages) == 1
    nn_promotion = nn_artifact.stages[0]
    assert isinstance(nn_promotion, BasePromotion)
    _check_obj(
        nn_promotion,
        dict(
            artifact="nn",
            version="v0.0.1",
            stage="staging",
            author=author,
            commit_hexsha=first_commit.hexsha,
        ),
        {"creation_date", "tag", "details"},
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
            commit_hexsha=first_commit.hexsha,
            discovered=False,
        ),
        {"creation_date", "promotions", "enrichments", "tag", "details"},
    )
    _check_obj(
        rf_ver2,
        dict(
            artifact="rf",
            name="v1.2.4",
            author=author,
            commit_hexsha=second_commit.hexsha,
            discovered=False,
        ),
        {"creation_date", "promotions", "enrichments", "tag", "details"},
    )

    assert len(rf_artifact.stages) == 4
    assert all(isinstance(l, BasePromotion) for l in rf_artifact.stages)
    rf_l1, _ = rf_ver1.promotions
    rf_l3, rf_l4 = rf_ver2.promotions

    _check_obj(
        rf_l1,
        dict(
            artifact="rf",
            version="v1.2.3",
            stage="production",
            author=author,
            commit_hexsha=first_commit.hexsha,
        ),
        {"creation_date", "tag", "details"},
    )
    _check_obj(
        rf_l4,
        dict(
            artifact="rf",
            version="v1.2.4",
            stage="production",
            author=author,
            commit_hexsha=second_commit.hexsha,
        ),
        {"creation_date", "tag", "details"},
    )
    _check_obj(
        rf_l3,
        dict(
            artifact="rf",
            version="v1.2.4",
            stage="staging",
            author=author,
            commit_hexsha=second_commit.hexsha,
        ),
        {"creation_date", "tag", "details"},
    )
