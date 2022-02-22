"""TODO: break this file into multiple test/files"""
import os.path
from typing import Any, Dict, Set

import pytest
from pydantic import BaseModel

from gto import GitRegistry
from gto.base import BaseLabel, BaseObject, BaseVersion
from gto.config import CONFIG_FILE, RegistryConfig
from gto.index import RepoIndexManager


@pytest.fixture
def init_showcase(empty_git_repo):
    path = empty_git_repo.working_dir

    def write_file(name, content):
        fullpath = os.path.join(path, name)
        os.makedirs(os.path.dirname(fullpath), exist_ok=True)
        with open(fullpath, "w", encoding="utf8") as file:
            file.write(content)

    write_file(CONFIG_FILE, "env_base: tag")

    return path, empty_git_repo, write_file


def _check_dict(obj: BaseModel, values: Dict[str, Any], skip_keys: Set[str]):
    obj_values = obj.dict(exclude=skip_keys)
    assert obj_values == values


def test_api(init_showcase):  # pylint: disable=too-many-locals, too-many-statements
    path, repo, write_file = init_showcase  # pylint: disable=unused-variable

    write_file("models/random-forest.pkl", "1st version")
    write_file("models/neural-network.pkl", "1st version")

    index = RepoIndexManager(repo=repo)
    index.add("rf", "model", "models/random-forest.pkl")
    index.add("nn", "model", "models/neural-network.pkl")
    index.add("features", "dataset", "datasets/features.csv")

    repo.index.add(["artifacts.yaml", "models"])
    first_commit = repo.index.commit("Create models")

    config = RegistryConfig(CONFIG_FILE=os.path.join(path, "gto.yaml"))
    registry = GitRegistry(
        repo=repo,
        version_manager=config.VERSION_MANAGERS_MAPPING[config.VERSION_BASE](repo=repo),
        env_manager=config.ENV_MANAGERS_MAPPING[config.ENV_BASE](repo=repo),
    )

    registry.register("rf", "v1", "HEAD")
    registry.register("nn", "v1", "HEAD")

    write_file("models/random-forest.pkl", "2nd version")

    second_commit = repo.index.commit("Update model")

    registry.register("rf", "v2", "HEAD")

    registry.promote("nn", "staging", promote_version="v1")
    registry.promote("rf", "production", promote_version="v1")
    registry.promote("rf", "staging", promote_ref="HEAD")
    registry.promote("rf", "production", promote_ref=repo.head.ref.commit.hexsha)
    registry.promote("rf", "production", promote_version="v1")

    objects = registry.state.objects
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

    assert len(rf_object.labels) == 3
    assert all(isinstance(l, BaseLabel) for l in rf_object.labels)
    rf_l1, rf_l2, rf_l3 = rf_object.labels

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
        rf_l2,
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
        rf_l3,
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
