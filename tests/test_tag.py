from gto.constants import Action
from gto.tag import ActionSign, name_tag, parse_name


def test_name_tag():
    assert (
        name_tag(Action.REGISTER, "path", "v1")
        == f"path{ActionSign[Action.REGISTER]}v1"
    )
    assert (
        name_tag(Action.DEPRECATE, "path", "v1")
        == f"path{ActionSign[Action.DEPRECATE]}v1"
    )


def test_parse_name():
    assert parse_name(f"path{ActionSign[Action.REGISTER]}v1") == dict(
        name="path", version="v1", action=Action.REGISTER
    )
    assert parse_name(f"path{ActionSign[Action.DEPRECATE]}v1") == dict(
        name="path", version="v1", action=Action.DEPRECATE
    )
    assert parse_name(f"path{ActionSign[Action.PROMOTE]}stage-1") == dict(
        name="path", action=Action.PROMOTE, label="stage", number=1
    )
    assert parse_name(f"path{ActionSign[Action.DEMOTE]}stage-1") == dict(
        name="path", action=Action.DEMOTE, label="stage", number=1
    )
