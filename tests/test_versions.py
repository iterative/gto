import pytest

from gto.versions import NumberedVersion, SemVer


@pytest.mark.parametrize("version", ["v0", "v1"])
def test_number_version_is_valid(version):
    assert NumberedVersion.is_valid(version)


@pytest.mark.parametrize("version", [1, "1", "v-1", "-v1", "v1x", "v1.", "v1.0"])
def test_number_version_is_not_valid(version):
    assert not NumberedVersion.is_valid(version)


def test_numbered_version_comparison():
    assert NumberedVersion("v1") < NumberedVersion("v2")
    assert NumberedVersion("v1") == NumberedVersion("v1")
    assert NumberedVersion("v1") < "v2"
    assert NumberedVersion("v1") == "v1"


def test_bump_numbered_version():
    assert NumberedVersion("v1").bump() == NumberedVersion("v2")


@pytest.mark.parametrize(
    "version", ["v0.1.2", "v3.4.5-pre.2+build.4", "v3.4.5-pre.2-build.4"]
)
def test_semver_is_valid(version):
    assert SemVer.is_valid(version)


@pytest.mark.parametrize(
    "version", [1, "1", "v1", "v1.2", "0.1.2", "3.4.5-pre.2+build.4"]
)
def test_semver_is_not_valid(version):
    assert not SemVer.is_valid(version)


def test_semver_comparison():
    assert SemVer("v1.3.2") < SemVer("v1.3.3")
    assert SemVer("v1.2.4") == SemVer("v1.2.4")
    assert SemVer("v1.3.4") < "v2.0.0"
    assert SemVer("v1.3.4") == "v1.3.4"


def test_bump_semver():
    assert SemVer("v1.3.4").bump("major") == SemVer("v2.0.0")
    assert SemVer("v1.3.4").bump("minor") == SemVer("v1.4.0")
    assert SemVer("v1.3.4").bump("patch") == SemVer("v1.3.5")
