# pylint: disable=unused-variable
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
        == f"myartifact{ActionSign[Action.PROMOTE]}stage-1"
    )


def test_parse_name():
    assert parse_name(f"path{ActionSign[Action.REGISTER]}v1") == dict(
        name="path", version="v1", action=Action.REGISTER
    )
    assert parse_name(f"path{ActionSign[Action.PROMOTE]}stage") == dict(
        name="path", action=Action.PROMOTE, stage="stage"
    )
    assert parse_name(f"path{ActionSign[Action.PROMOTE]}stage-1") == dict(
        name="path", action=Action.PROMOTE, stage="stage", number=1
    )
