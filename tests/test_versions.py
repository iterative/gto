import pytest

from gitops.versions import NumberedVersion


def test_number_version_is_valid():
    assert NumberedVersion.is_valid("v1")
    assert NumberedVersion.is_valid("v0")
    assert not NumberedVersion.is_valid("v-1")
    assert not NumberedVersion.is_valid("-v1")
    assert not NumberedVersion.is_valid("v1x")
    assert not NumberedVersion.is_valid("v1.")
    assert not NumberedVersion.is_valid("v1.0")


def test_numbered_version_comparison():
    assert NumberedVersion("v1") < NumberedVersion("v2")
    assert NumberedVersion("v1") == NumberedVersion("v1")
    assert not NumberedVersion("v1") > NumberedVersion("v2")
    assert NumberedVersion("v1") < "v2"
    assert NumberedVersion("v1") == "v1"
