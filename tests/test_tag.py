# pylint: disable=unused-variable
import pytest

from gto.constants import Action
from gto.tag import ActionSign, name_tag, parse_name


def test_name_tag(empty_git_repo):
    repo, write_func = empty_git_repo
    assert (
        name_tag(Action.REGISTER, "myartifact", "v1")
        == f"myartifact{ActionSign[Action.REGISTER]}v1"
    )
    assert (
        name_tag(Action.PROMOTE, "myartifact", stage="stage", simple=True)
        == f"myartifact{ActionSign[Action.PROMOTE]}stage"
    )
    assert (
        name_tag(Action.PROMOTE, "myartifact", repo=repo, stage="stage", simple=False)
        == f"myartifact{ActionSign[Action.PROMOTE]}stage{ActionSign[Action.PROMOTE]}1"
    )


def test_parse_name():
    assert parse_name(f"path{ActionSign[Action.REGISTER]}v1.2.3") == dict(
        name="path", version="v1.2.3", action=Action.REGISTER
    )
    assert parse_name(f"path{ActionSign[Action.PROMOTE]}stage") == dict(
        name="path", action=Action.PROMOTE, stage="stage"
    )
    assert parse_name(
        f"path{ActionSign[Action.PROMOTE]}stage{ActionSign[Action.PROMOTE]}1"
    ) == dict(name="path", action=Action.PROMOTE, stage="stage", number=1)


@pytest.mark.parametrize(
    "tag_name",
    [
        "",
        "###",
        "@@@",
        "model@v1",
        "model@v111",
        "model-prod",
        "model@0.0.1",
        "model-prod-v1",
        "model#prod#-1",
        "model#prod#1-2",
        "model#prod?#1-2",
        "model-prod-v1-stage",
        "model@prod@v1@stage-1",
        "namespace/model@0.0.1",
        "@namespace/model@0.0.1",
        "model#prod#v1#stage#1-",
        "model#prod-v1-stage@1-2",
        "model#prod-v1-stage@1-2#@",
    ],
)
def test_parse_wrong_names(tag_name):
    assert not parse_name(tag_name, raise_on_fail=False)
