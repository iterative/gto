import pytest

from gto.versions import NumberedVersion


@pytest.mark.parametrize("version", ["v0", "v1"])
def test_number_version_is_valid(version):
    assert NumberedVersion.is_valid(version)


@pytest.mark.parametrize("version", ["v-1", "-v1", "v1x", "v1.", "v1.0"])
def test_number_version_is_not_valid(version):
    assert not NumberedVersion.is_valid(version)


def test_numbered_version_comparison():
    assert NumberedVersion("v1") < NumberedVersion("v2")
    assert NumberedVersion("v1") == NumberedVersion("v1")
    assert NumberedVersion("v1") < "v2"
    assert NumberedVersion("v1") == "v1"
