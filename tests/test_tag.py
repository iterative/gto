from gitops.constants import Action
from gitops.tag import name_tag, parse_name


def test_name_tag():
    assert (
        name_tag(Action.REGISTER, "model", "path", "v1")
        == f"model-path-{Action.REGISTER.value}-v1"
    )
    assert (
        name_tag(Action.UNREGISTER, "model", "path", "v1")
        == f"model-path-{Action.UNREGISTER.value}-v1"
    )


def test_parse_name():
    assert parse_name(f"model-path-{Action.REGISTER.value}-v1") == dict(
        category="model", object="path", version="v1", action=Action.REGISTER
    )
    assert parse_name(f"model-path-{Action.UNREGISTER.value}-v1") == dict(
        category="model", object="path", version="v1", action=Action.UNREGISTER
    )
    assert parse_name(f"model-path-{Action.PROMOTE.value}-stage-1") == dict(
        category="model", object="path", action=Action.PROMOTE, label="stage", number=1
    )
    assert parse_name(f"model-path-{Action.DEMOTE.value}-stage-1") == dict(
        category="model", object="path", action=Action.DEMOTE, label="stage", number=1
    )
