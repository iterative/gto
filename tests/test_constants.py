import pytest

from gto.constants import (
    check_string_is_valid,
    fullname_in_tag_re,
    fullname_re,
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
        "model_prod_v1",
        "dvclive/model",
        "model_A",
        "DVCLive/Model",
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
        "_model",
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
        "some/Other_Folder:some/model",
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
        "Some/folder/A=model",
        "Some/folder/A=Model",
    ],
)
def test_check_fullname_in_tag_is_valid(name):
    assert check_string_is_valid(name, regex=fullname_in_tag_re)
