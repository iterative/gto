import pytest

from gto.constants import check_name_is_valid


@pytest.mark.parametrize(
    "name",
    [
        "nn",
        "m1",
        "model-prod",
        "model-prod-v1",
        "namespace/model",
    ],
)
def test_check_name_is_valid(name):
    assert check_name_is_valid(name)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "m",
        "1",
        "m/",
        "/m",
        "1nn",
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
    assert not check_name_is_valid(name)
