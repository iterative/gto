from gitops.tag import DEMOTE, PROMOTE, REGISTER, UNREGISTER, name, parse


def test_name():
    assert name(REGISTER, "model", "v1") == f"model-model-{REGISTER}-v1"
    assert name(UNREGISTER, "model", "v1") == f"model-model-{UNREGISTER}-v1"


def test_parse():
    assert parse(f"model-model-{REGISTER}-v1") == dict(
        model="model", version="v1", action=REGISTER
    )
    assert parse(f"model-model-{UNREGISTER}-v1") == dict(
        model="model", version="v1", action=UNREGISTER
    )
    assert parse(f"model-model-{PROMOTE}-stage-1") == dict(
        model="model", action=PROMOTE, label="stage", number=1
    )
    assert parse(f"model-model-{DEMOTE}-stage-1") == dict(
        model="model", action=DEMOTE, label="stage", number=1
    )
