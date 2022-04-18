import pytest

from gto.versions import SemVer


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
    assert SemVer("v1.3.4").bump_major() == SemVer("v2.0.0")
    assert SemVer("v1.3.4").bump_minor() == SemVer("v1.4.0")
    assert SemVer("v1.3.4").bump_patch() == SemVer("v1.3.5")
