from gitops.tag import DEMOTE, PROMOTE, REGISTER, UNREGISTER, name_tag, parse_name


def test_name_tag():
    assert name_tag(REGISTER, "model", "v1") == f"model-model-{REGISTER}-v1"
    assert name_tag(UNREGISTER, "model", "v1") == f"model-model-{UNREGISTER}-v1"


def test_parse_name():
    assert parse_name(f"model-model-{REGISTER}-v1") == dict(
        model="model", version="v1", action=REGISTER
    )
    assert parse_name(f"model-model-{UNREGISTER}-v1") == dict(
        model="model", version="v1", action=UNREGISTER
    )
    assert parse_name(f"model-model-{PROMOTE}-stage-1") == dict(
        model="model", action=PROMOTE, label="stage", number=1
    )
    assert parse_name(f"model-model-{DEMOTE}-stage-1") == dict(
        model="model", action=DEMOTE, label="stage", number=1
    )
