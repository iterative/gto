"""TODO: break this file into multiple test/files"""
import gto
from gto.base import BaseLabel, BaseObject, BaseVersion
from tests.utils import _check_dict


def test_api(showcase):  # pylint: disable=too-many-locals, too-many-statements
    (
        path,
        repo,
        write_file,
        first_commit,
        second_commit,
    ) = showcase  # pylint: disable=unused-variable

    objects = gto.api.get_state(path).objects
    assert set(objects.keys()) == {"features", "nn", "rf"}
    assert objects["features"] == BaseObject(name="features", versions=[], labels=[])
    nn_object = objects["nn"]
    assert isinstance(nn_object, BaseObject)
    assert nn_object.name == "nn"
    assert len(nn_object.versions) == 1
    nn_version = nn_object.versions[0]
    assert isinstance(nn_version, BaseVersion)
    author = repo.commit().author.name
    _check_dict(
        nn_version,
        dict(
            object="nn",
            name="v1",
            author=author,
            commit_hexsha=first_commit.hexsha,
            unregistered_date=None,
        ),
        {"creation_date"},
    )
    assert len(nn_object.labels) == 1
    nn_label = nn_object.labels[0]
    assert isinstance(nn_label, BaseLabel)
    _check_dict(
        nn_label,
        dict(
            object="nn",
            version="v1",
            name="staging",
            author=author,
            commit_hexsha=first_commit.hexsha,
            unregistered_date=None,
        ),
        {"creation_date"},
    )

    rf_object = objects["rf"]
    assert isinstance(rf_object, BaseObject)
    assert rf_object.name == "rf"

    assert len(rf_object.versions) == 2
    assert all(isinstance(v, BaseVersion) for v in rf_object.versions)
    rf_ver1, rf_ver2 = rf_object.versions
    _check_dict(
        rf_ver1,
        dict(
            object="rf",
            name="v1",
            author=author,
            commit_hexsha=first_commit.hexsha,
            unregistered_date=None,
        ),
        {"creation_date"},
    )
    _check_dict(
        rf_ver2,
        dict(
            object="rf",
            name="v2",
            author=author,
            commit_hexsha=second_commit.hexsha,
            unregistered_date=None,
        ),
        {"creation_date"},
    )

    assert len(rf_object.labels) == 4
    assert all(isinstance(l, BaseLabel) for l in rf_object.labels)
    rf_l1, rf_l2, rf_l3, _ = rf_object.labels

    _check_dict(
        rf_l1,
        dict(
            object="rf",
            version="v1",
            name="production",
            author=author,
            commit_hexsha=first_commit.hexsha,
            unregistered_date=None,
        ),
        {"creation_date"},
    )
    _check_dict(
        rf_l3,
        dict(
            object="rf",
            version="v2",
            name="production",
            author=author,
            commit_hexsha=second_commit.hexsha,
            unregistered_date=None,
        ),
        {"creation_date"},
    )
    _check_dict(
        rf_l2,
        dict(
            object="rf",
            version="v2",
            name="staging",
            author=author,
            commit_hexsha=second_commit.hexsha,
            unregistered_date=None,
        ),
        {"creation_date"},
    )


def test_cli(init_showcase):
    pass
