import pytest

from gto.constants import (
    Shortcut,
    check_string_is_valid,
    fullname_in_tag_re,
    fullname_re,
    parse_shortcut,
)


@pytest.mark.parametrize(
    "name",
    [
        "1",
        "m",
        "nn",
        "m1",
        "1nn",
        "model-prod",
        "model-prod-v1",
        "dvclive/model",
    ],
)
def test_check_name_is_valid(name):
    assert check_string_is_valid(name)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "m/",
        "/m",
        "###",
        "@@@",
        "a model",
        "a_model",
        "-model",
        "model-",
        "model@1",
        "model#1",
        "@namespace/model",
    ],
)
def test_check_name_is_invalid(name):
    assert not check_string_is_valid(name)


@pytest.mark.parametrize(
    "name",
    [
        "model",
        "dvclive:model",
        "some/folder:some/model",
    ],
)
def test_check_fullname_is_valid(name):
    assert check_string_is_valid(name, regex=fullname_re)


@pytest.mark.parametrize(
    "name",
    [
        "model",
        "dvclive=model",
        "some/folder=some/model",
    ],
)
def test_check_fullname_in_tag_is_valid(name):
    assert check_string_is_valid(name, regex=fullname_in_tag_re)


@pytest.mark.parametrize(
    "name,shortcut",
    [
        ("", None),
        ("m", None),
        ("m/", None),
        ("nn", None),
        ("model@v1.2.3", Shortcut(name="model", version="v1.2.3")),
        ("model#prod", Shortcut(name="model", stage="prod")),
        ("model:HEAD", Shortcut(name="model", ref="HEAD")),
        (":HEAD", Shortcut(name=None, ref="HEAD")),
        ("@v1.2.3", Shortcut(name=None, version="v1.2.3")),
        ("#prod", Shortcut(name=None, stage="prod")),
        # ("model:HEAD#prod", Shortcut(name="model", ref="HEAD", stage="prod")),
        # ("model#prod:HEAD", Shortcut(name="model", ref="HEAD", stage="prod")),
    ],
)
def test_parse_shortcut(name, shortcut):
    assert parse_shortcut(name) == shortcut
