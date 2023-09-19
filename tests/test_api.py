# pylint: disable=protected-access
"""TODO: add more tests for API"""
import os
from contextlib import contextmanager
from time import sleep
from typing import Optional
from unittest.mock import ANY, call, patch

import pytest
from freezegun import freeze_time
from pytest_mock import MockFixture
from pytest_test_utils import TmpDir
from scmrepo.git import Git

import gto
import tests.resources
from gto.api import show
from gto.exceptions import RefNotFound, WrongArgs
from gto.git_utils import cloned_git_repo
from gto.index import RepoIndexManager
from gto.tag import find
from gto.versions import SemVer
from tests.utils import (
    check_obj,
    convert_objects_to_str_in_json_serializable_object,
)


def test_empty_index(scm: Git):
    with RepoIndexManager.from_scm(scm) as index:
        assert isinstance(index, RepoIndexManager)
        assert len(index.artifact_centric_representation()) == 0


@pytest.mark.usefixtures("scm")
def test_empty_state(tmp_dir: TmpDir):
    state = gto.api._get_state(tmp_dir)
    assert len(state.artifacts) == 0


@pytest.mark.usefixtures("scm")
def test_api_info_commands_empty_repo(tmp_dir: TmpDir):
    gto.api.show(tmp_dir)
    gto.api.history(tmp_dir)


@pytest.fixture(name="artifact")
def _artifact(tmp_dir: TmpDir, scm: Git, request: pytest.FixtureRequest) -> str:
    request.getfixturevalue("init_showcase_semver")
    tmp_dir.gen(
        "artifacts.yaml", "rf: \n  type: model\n  path: models/random-forest.pkl\n"
    )
    scm.add(["artifacts.yaml"])
    scm.commit("Commit 1")
    tmp_dir.gen(
        "artifacts.yaml", "rf: \n  type: model\n  path: models/random-forest.pklx\n"
    )
    scm.add(["artifacts.yaml"])
    scm.commit("Commit 2")
    return "new-artifact"


def test_register_deregister(tmp_dir: TmpDir, scm: Git, artifact: str):
    vname1, vname2 = "v1.0.0", "v1.0.1"
    gto.api.register(tmp_dir, artifact, "HEAD", vname1)
    latest = gto.api.find_latest_version(tmp_dir, artifact)
    assert latest.version == vname1
    tmp_dir.gen("tmp.txt", "some text")
    scm.add(["tmp.txt"])
    scm.commit("Irrelevant action to create a git commit to register another version")
    message = "Some message"
    author = "GTO"
    author_email = "gto@iterative.ai"
    gto.api.register(
        tmp_dir,
        artifact,
        "HEAD",
        message=message,
        author=author,
        author_email=author_email,
    )
    latest = gto.api.find_latest_version(tmp_dir, artifact)
    assert latest.version == vname2
    assert latest.message == message
    assert latest.author == author
    assert latest.author_email == author_email

    assert len(gto.api.show(tmp_dir, artifact, deprecated=False)) == 2

    # test _show_versions
    assert (
        gto.api._show_versions(tmp_dir, artifact, ref="HEAD")[0]["ref"]
        == f"{artifact}@v1.0.1"
    )
    assert (
        gto.api._show_versions(tmp_dir, artifact, ref="HEAD^1")[0]["ref"]
        == f"{artifact}@v1.0.0"
    )
    assert (
        gto.api._show_versions(tmp_dir, artifact, ref=scm.get_rev())[0]["ref"]
        == f"{artifact}@v1.0.1"
    )
    with pytest.raises(RefNotFound):
        gto.api._show_versions(tmp_dir, artifact, ref="HEAD^2")

    gto.api.deregister(repo=tmp_dir, name=artifact, version=vname2)
    latest = gto.api.find_latest_version(tmp_dir, artifact)
    assert latest.version == vname1

    assert len(gto.api.show(tmp_dir, artifact, deprecated=False)) == 1
    assert len(gto.api.show(tmp_dir, artifact, deprecated=True)) == 2
    assert len(gto.api._show_versions(tmp_dir, artifact, ref="HEAD")) == 0


@pytest.mark.parametrize(
    "name",
    (
        "model",
        "folder:artifact",
        "some/folder:some/artifact",
    ),
)
@pytest.mark.usefixtures("artifact")
def test_assign(tmp_dir: TmpDir, scm: Git, name: str):
    stage = "staging"
    scm.tag("v1.0.0")
    scm.tag("wrong-tag-unrelated")
    message = "some msg"
    author = "GTO"
    author_email = "gto@iterative.ai"
    event = gto.api.assign(
        tmp_dir,
        name,
        stage,
        ref="HEAD",
        name_version="v0.0.1",
        message=message,
        author=author,
        author_email=author_email,
    )
    assignments = gto.api.find_versions_in_stage(tmp_dir, name, stage)
    assert len(assignments) == 1
    check_obj(
        assignments[0].dict_state(),
        {
            "artifact": name,
            "version": "v0.0.1",
            "stage": stage,
            "author": author,
            "author_email": author_email,
            "message": message,
            "commit_hexsha": scm.get_rev(),
            "is_active": True,
            "ref": event.ref,
        },
        {"created_at", "assignments", "unassignments", "tag", "activated_at"},
    )
    event = gto.api.assign(
        tmp_dir,
        name,
        stage,
        ref="HEAD^1",
        name_version="v0.0.2",
        message=message,
        author=author,
        author_email=author_email,
    )
    assignments = gto.api.find_versions_in_stage(tmp_dir, name, stage)
    assert len(assignments) == 1
    assignments = gto.api.find_versions_in_stage(
        tmp_dir, name, stage, versions_per_stage=-1
    )
    assert len(assignments) == 2


def test_assign_skip_registration(tmp_dir: TmpDir, artifact: str):
    stage = "staging"
    with pytest.raises(WrongArgs):
        gto.api.assign(
            tmp_dir,
            artifact,
            stage,
            ref="HEAD",
            name_version="v0.0.1",
            skip_registration=True,
        )
    gto.api.assign(tmp_dir, artifact, stage, ref="HEAD", skip_registration=True)
    assignments = gto.api.find_versions_in_stage(tmp_dir, artifact, stage)
    assert len(assignments) == 1
    assert not SemVer.is_valid(assignments[0].version)


def test_assign_force_is_needed(tmp_dir: TmpDir, artifact: str):
    gto.api.assign(tmp_dir, artifact, "staging", ref="HEAD")
    gto.api.assign(tmp_dir, artifact, "staging", ref="HEAD^1")
    with pytest.raises(WrongArgs):
        gto.api.assign(tmp_dir, artifact, "staging", ref="HEAD")
    with pytest.raises(WrongArgs):
        gto.api.assign(tmp_dir, artifact, "staging", ref="HEAD^1")
    gto.api.assign(tmp_dir, artifact, "staging", ref="HEAD", force=True)
    gto.api.assign(tmp_dir, artifact, "staging", ref="HEAD^1", force=True)


@pytest.mark.usefixtures("artifact")
def test_unassign(tmp_dir: TmpDir):
    gto.api.register(tmp_dir, name="model", ref="HEAD")
    gto.api.assign(tmp_dir, name="model", ref="HEAD", stage="dev")
    assert (
        gto.api.find_versions_in_stage(tmp_dir, name="model", stage="dev") is not None
    )

    gto.api.unassign(tmp_dir, name="model", ref="HEAD", stage="dev")
    assert gto.api.find_versions_in_stage(tmp_dir, name="model", stage="dev") is None


@pytest.mark.usefixtures("artifact")
def test_deprecate(tmp_dir: TmpDir):
    gto.api.register(tmp_dir, name="model", ref="HEAD")
    assert len(gto.api.show(tmp_dir, "model")) == 1

    sleep(1)
    gto.api.deprecate(tmp_dir, name="model")
    assert len(gto.api.show(tmp_dir, "model", deprecated=False)) == 0
    assert len(gto.api.show(tmp_dir, "model", deprecated=True)) == 1

    with pytest.raises(WrongArgs):
        gto.api.deprecate(tmp_dir, name="model")
        gto.api.deprecate(tmp_dir, name="model", simple=True, force=True)
    gto.api.deprecate(tmp_dir, name="model", force=True)


@contextmanager
def environ(**overrides):
    old = {name: os.environ[name] for name in overrides if name in os.environ}
    to_del = set(overrides) - set(old)
    try:
        os.environ.update(overrides)
        yield
    finally:
        os.environ.update(old)
        for name in to_del:
            os.environ.pop(name, None)


@pytest.mark.usefixtures("artifact")
@pytest.mark.parametrize("with_prefix", [True, False])
def test_check_ref_detailed(scm: Git, with_prefix: bool):
    NAME = "model"
    SEMVER = "v1.2.3"
    GIT_AUTHOR_NAME = "Alexander Guschin"
    GIT_AUTHOR_EMAIL = "aguschin@iterative.ai"
    GIT_COMMITTER_NAME = "Oliwav"
    GIT_COMMITTER_EMAIL = "oliwav@iterative.ai"

    with environ(
        GIT_AUTHOR_NAME=GIT_AUTHOR_NAME,
        GIT_AUTHOR_EMAIL=GIT_AUTHOR_EMAIL,
        GIT_COMMITTER_NAME=GIT_COMMITTER_NAME,
        GIT_COMMITTER_EMAIL=GIT_COMMITTER_EMAIL,
    ):
        gto.api.register(scm, name=NAME, ref="HEAD", version=SEMVER)

    ref = f"{NAME}@{SEMVER}"
    if with_prefix:
        ref = f"refs/tags/{ref}"
    events = gto.api.check_ref(scm, ref)
    assert len(events) == 1, "Should return one event"
    check_obj(
        events[0].dict_state(),
        {
            "event": "registration",
            "artifact": NAME,
            "version": SEMVER,
            "author": GIT_COMMITTER_NAME,
            "author_email": GIT_COMMITTER_EMAIL,
            "tag": f"{NAME}@{SEMVER}",
        },
        skip_keys={"commit_hexsha", "created_at", "message", "priority", "addition"},
    )


@pytest.mark.usefixtures("showcase")
def test_check_ref_multiple_showcase(scm: Git):
    for tag in find(scm=scm):
        events = gto.api.check_ref(scm, tag.name)
        assert len(events) == 1, "Should return one event"
        assert events[0].ref == tag.name


@pytest.mark.usefixtures("artifact")
def test_check_ref_catch_the_bug(scm: Git):
    NAME = "artifact"
    gto.api.register(scm, NAME, "HEAD")
    assignment1 = gto.api.assign(scm, NAME, "staging", ref="HEAD")
    assignment2 = gto.api.assign(scm, NAME, "prod", ref="HEAD")
    assignment3 = gto.api.assign(scm, NAME, "dev", ref="HEAD")
    for assignment, tag in zip(
        [assignment1, assignment2, assignment3],
        [f"{NAME}#staging#1", f"{NAME}#prod#2", f"{NAME}#dev#3"],
    ):
        events = gto.api.check_ref(scm, tag)
        assert len(events) == 1, events
        assert events[0].ref == assignment.tag == tag


@pytest.mark.usefixtures("scm")
def test_is_not_gto_repo(tmp_dir: TmpDir):
    assert not gto.api._is_gto_repo(tmp_dir)


@pytest.mark.usefixtures("init_showcase_semver")
def test_is_gto_repo_because_of_config(tmp_dir: TmpDir):
    assert gto.api._is_gto_repo(tmp_dir)


@pytest.mark.usefixtures("repo_with_commit")
def test_is_gto_repo_because_of_registered_artifact(tmp_dir: TmpDir):
    gto.api.register(tmp_dir, "model", "HEAD", "v1.0.0")
    assert gto.api._is_gto_repo(tmp_dir)


@pytest.mark.usefixtures("scm")
def test_is_gto_repo_because_of_artifacts_yaml(tmp_dir: TmpDir):
    tmp_dir.gen("artifacts.yaml", "{}")
    assert gto.api._is_gto_repo(tmp_dir)


def test_if_show_on_remote_git_repo_then_return_expected_registry():
    result = show(repo=tests.resources.SAMPLE_REMOTE_REPO_URL)
    assert result == tests.resources.get_sample_remote_repo_expected_registry()


@pytest.mark.parametrize(
    "ref,expected_stage,expected_version,expected_artifact",
    (
        ("churn#prod#2", "prod", "v3.0.0", "churn"),
        ("segment@v0.4.1", None, "v0.4.1", "segment"),
    ),
)
def test_if_check_ref_on_remote_git_repo_then_return_expected_reference(
    ref: str,
    expected_stage: Optional[str],
    expected_version: str,
    expected_artifact: str,
):
    result = gto.api.check_ref(repo=tests.resources.SAMPLE_REMOTE_REPO_URL, ref=ref)
    assert len(result) == 1
    if expected_stage is not None:
        assert result[0].stage == expected_stage
    else:
        assert hasattr(result[0], "stage") is False
    assert result[0].version == expected_version
    assert result[0].artifact == expected_artifact


@freeze_time("1996-06-09 00:00:00", tz_offset=0)
def test_if_history_on_remote_git_repo_then_return_expected_history():
    result = gto.api.history(
        repo=tests.resources.SAMPLE_REMOTE_REPO_URL, artifact="churn"
    )
    assert (
        convert_objects_to_str_in_json_serializable_object(result)
        == tests.resources.get_sample_remote_repo_expected_history_churn()
    )


def test_if_stages_on_remote_git_repo_then_return_expected_stages():
    result = gto.api.get_stages(repo=tests.resources.SAMPLE_REMOTE_REPO_URL)
    assert result == ["dev", "prod", "staging"]


def test_if_describe_on_remote_git_repo_then_return_expected_info():
    result = gto.api.describe(repo=tests.resources.SAMPLE_REMOTE_REPO_URL, name="churn")
    assert result.dict(exclude_defaults=True) == {
        "type": "model",
        "path": "models/churn.pkl",
        "virtual": False,
    }


@pytest.mark.usefixtures("artifact")
def test_if_register_with_auto_push_then_invoke_git_push_tag(tmp_dir: TmpDir):
    with patch("gto.registry.git_push_tag") as mocked_git_push_tags:
        gto.api.register(repo=tmp_dir, name="model", ref="HEAD", push=True)
    mocked_git_push_tags.assert_called_once_with(
        scm=ANY,
        tag_name="model@v0.0.1",
        delete=False,
    )


@pytest.mark.usefixtures("artifact")
def test_if_assign_with_auto_push_then_invoke_git_push_tag_2_times_for_registration_and_promotion(
    tmp_dir: TmpDir,
):
    with patch("gto.registry.git_push_tag") as mocked_git_push_tags:
        gto.api.assign(tmp_dir, name="model", stage="dev", ref="HEAD", push=True)
    expected_calls = [
        call(
            scm=ANY,
            tag_name="model@v0.0.1",
            delete=False,
        ),
        call(
            scm=ANY,
            tag_name="model#dev#1",
            delete=False,
        ),
    ]
    mocked_git_push_tags.assert_has_calls(expected_calls)


@pytest.mark.usefixtures("artifact")
def test_if_unassign_with_auto_push_then_invoke_git_push_tag(tmp_dir: TmpDir):
    gto.api.assign(tmp_dir, name="model", stage="dev", ref="HEAD", push=False)
    with patch("gto.registry.git_push_tag") as mocked_git_push_tags:
        gto.api.unassign(
            tmp_dir,
            name="model",
            stage="dev",
            version="v0.0.1",
            push=True,
        )
    mocked_git_push_tags.assert_called_once_with(
        scm=ANY,
        tag_name="model#dev!#2",
        delete=False,
    )


@pytest.mark.usefixtures("artifact")
def test_if_unassign_with_delete_and_auto_push_then_invoke_git_push_tag(
    tmp_dir: TmpDir,
):
    gto.api.assign(tmp_dir, name="model", stage="dev", ref="HEAD", push=False)
    with patch("gto.registry.git_push_tag") as mocked_git_push_tags:
        gto.api.unassign(
            tmp_dir,
            name="model",
            stage="dev",
            version="v0.0.1",
            delete=True,
            push=True,
        )
    mocked_git_push_tags.assert_called_once_with(
        scm=ANY, tag_name="model#dev#1", delete=True
    )


@pytest.mark.usefixtures("artifact")
def test_if_deregister_with_auto_push_then_invoke_git_push_tag(tmp_dir: TmpDir):
    gto.api.register(tmp_dir, name="model", ref="HEAD", push=False)
    with patch("gto.registry.git_push_tag") as mocked_git_push_tags:
        gto.api.deregister(tmp_dir, name="model", version="v0.0.1", push=True)
    mocked_git_push_tags.assert_called_once_with(
        scm=ANY,
        tag_name="model@v0.0.1!",
        delete=False,
    )


@pytest.mark.usefixtures("artifact")
def test_if_deregister_with_delete_and_auto_push_then_invoke_git_push_tag(
    tmp_dir: TmpDir,
):
    gto.api.register(tmp_dir, name="model", ref="HEAD", push=False)
    with patch("gto.registry.git_push_tag") as mocked_git_push_tags:
        gto.api.deregister(
            tmp_dir,
            name="model",
            version="v0.0.1",
            push=True,
            delete=True,
        )
    mocked_git_push_tags.assert_called_once_with(
        scm=ANY,
        tag_name="model@v0.0.1",
        delete=True,
    )


@pytest.mark.usefixtures("artifact")
def test_if_deprecate_with_auto_push_then_invoke_git_push_tag(tmp_dir: TmpDir):
    gto.api.register(tmp_dir, name="model", ref="HEAD", push=False)
    with patch("gto.registry.git_push_tag") as mocked_git_push_tags:
        gto.api.deprecate(tmp_dir, name="model", push=True)
    mocked_git_push_tags.assert_called_once_with(
        scm=ANY,
        tag_name="model@deprecated",
        delete=False,
    )


@pytest.mark.usefixtures("artifact")
def test_if_deprecate_with_delete_and_auto_push_then_invoke_git_push_tag(
    tmp_dir: TmpDir,
):
    gto.api.register(tmp_dir, name="model", ref="HEAD", push=False)
    with patch("gto.registry.git_push_tag") as mocked_git_push_tags:
        gto.api.deprecate(tmp_dir, name="model", push=True, delete=True)
    mocked_git_push_tags.assert_called_once_with(
        scm=ANY,
        tag_name="model@v0.0.1",
        delete=True,
    )


def test_if_register_with_remote_repo_then_invoke_git_push_tag(tmp_dir: TmpDir):
    with patch("gto.registry.git_push_tag") as mocked_git_push_tag:
        with patch("gto.git_utils.TemporaryDirectory") as MockedTemporaryDirectory:
            MockedTemporaryDirectory.return_value = tmp_dir
            gto.api.register(
                repo=tests.resources.SAMPLE_REMOTE_REPO_URL,
                name="model",
                ref="HEAD",
            )
            mocked_git_push_tag.assert_called_once_with(
                scm=ANY,
                tag_name="model@v0.0.1",
                delete=False,
            )


def test_if_assign_with_remote_repo_then_invoke_git_push_tag(tmp_dir: TmpDir):
    with patch("gto.registry.git_push_tag") as mocked_git_push_tag:
        with patch("gto.git_utils.TemporaryDirectory") as MockedTemporaryDirectory:
            MockedTemporaryDirectory.return_value = tmp_dir
            gto.api.assign(
                repo=tests.resources.SAMPLE_REMOTE_REPO_URL,
                name="model",
                stage="dev",
                ref="HEAD",
            )
            expected_calls = [
                call(
                    scm=ANY,
                    tag_name="model@v0.0.1",
                    delete=False,
                ),
                call(
                    scm=ANY,
                    tag_name="model#dev#1",
                    delete=False,
                ),
            ]
            mocked_git_push_tag.assert_has_calls(expected_calls)


def test_if_deprecate_with_remote_repo_then_invoke_git_push_tag(tmp_dir: TmpDir):
    with patch("gto.registry.git_push_tag") as mocked_git_push_tag:
        with patch("gto.git_utils.TemporaryDirectory") as MockedTemporaryDirectory:
            MockedTemporaryDirectory.return_value = tmp_dir
            gto.api.deprecate(
                repo=tests.resources.SAMPLE_REMOTE_REPO_URL,
                name="churn",
            )
            mocked_git_push_tag.assert_called_once_with(
                scm=ANY,
                tag_name="churn@deprecated",
                delete=False,
            )


def test_if_deregister_with_remote_repo_then_invoke_git_push_tag(tmp_dir: TmpDir):
    with patch("gto.registry.git_push_tag") as mocked_git_push_tag:
        with patch("gto.git_utils.TemporaryDirectory") as MockedTemporaryDirectory:
            MockedTemporaryDirectory.return_value = tmp_dir
            gto.api.deregister(
                repo=tests.resources.SAMPLE_REMOTE_REPO_URL,
                name="churn",
                version="v3.0.0",
            )
            mocked_git_push_tag.assert_called_once_with(
                scm=ANY,
                tag_name="churn@v3.0.0!",
                delete=False,
            )


def test_if_unassign_with_remote_repo_then_invoke_git_push_tag(tmp_dir: TmpDir):
    with patch("gto.registry.git_push_tag") as mocked_git_push_tag:
        with patch("gto.git_utils.TemporaryDirectory") as MockedTemporaryDirectory:
            MockedTemporaryDirectory.return_value = tmp_dir
            gto.api.unassign(
                repo=tests.resources.SAMPLE_REMOTE_REPO_URL,
                name="churn",
                stage="staging",
                version="v3.1.0",
            )
            mocked_git_push_tag.assert_called_once_with(
                scm=ANY,
                tag_name="churn#staging!#3",
                delete=False,
            )


def test_action_doesnt_push_even_if_repo_has_remotes_set(mocker: MockFixture):
    # test for https://github.com/iterative/gto/issues/405
    with cloned_git_repo(tests.resources.SAMPLE_REMOTE_REPO_URL) as scm:
        mocked_git_push_tag = mocker.patch("gto.registry.git_push_tag")
        gto.api.unassign(
            repo=scm,
            name="churn",
            stage="staging",
            version="v3.1.0",
        )
        mocked_git_push_tag.assert_not_called()
