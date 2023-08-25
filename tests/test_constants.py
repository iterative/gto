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
        "dvclive/model",
    ],
)
def test_check_name_is_valid(name):
    """Test that the check_string_is_valid function returns True for valid names."""
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
    """Test that the check_string_is_valid function returns False for invalid names."""
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
    """Test that the check_string_is_valid function returns True for valid full names."""
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
    """Test that the check_string_is_valid function returns True for valid full names in tags."""
    assert check_string_is_valid(name, regex=fullname_in_tag_re)
