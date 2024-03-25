from functools import total_ordering

import semver

from gto.exceptions import IncomparableVersions, InvalidVersion, WrongArgs


class AbstractVersion:
    version: str

    def __init__(self, version) -> None:
        if not self.is_valid(version):
            raise InvalidVersion(f"Supplied version '{version}' cannot be parsed")
        self.version = version

    @classmethod
    def is_valid(cls, version) -> bool:
        raise NotImplementedError

    def __eq__(self, other):
        return self.version == other.version

    def __lt__(self, other):
        raise NotImplementedError

    @classmethod
    def get_minimal(cls):
        raise NotImplementedError


@total_ordering
class SemVer(AbstractVersion):
    """
    A subclass of Version which allows a "v" prefix
    """

    @classmethod
    def is_valid(cls, version):
        try:
            cls.parse(version)
            return True
        except (InvalidVersion, ValueError, IndexError) as _:  # noqa: F841
            return False

    @classmethod
    def parse(cls, version: str) -> "semver.VersionInfo":
        """
        Parse version string to a Version instance.

        :param version: version string with "v" or "V" prefix
        :raises ValueError: when version does not start with "v" or "V"
        :return: a new instance
        """
        if not isinstance(version, str):
            raise InvalidVersion("Version should be of type str")
        if version[0] not in ("v"):
            raise InvalidVersion(
                f"{version}: not a valid semantic version tag. Must start with 'v'"
            )
        return semver.VersionInfo.parse(version[1:])

    def __eq__(self, other):
        if isinstance(other, str):
            other = self.__class__(other)
        if not isinstance(other, self.__class__):
            raise IncomparableVersions(self, other)
        return self.version == other.version

    def __lt__(self, other):
        if isinstance(other, str):
            other = self.__class__(other)
        if not isinstance(other, self.__class__):
            raise IncomparableVersions(self, other)
        return self.parse(self.version) < self.parse(other.version)

    def bump_major(self):
        return self.__class__(f"v{self.parse(self.version).bump_major()}")

    def bump_minor(self):
        return self.__class__(f"v{self.parse(self.version).bump_minor()}")

    def bump_patch(self):
        return self.__class__(f"v{self.parse(self.version).bump_patch()}")

    def bump(self, bump_major=False, bump_minor=False, bump_patch=False):
        if sum(bool(i) for i in (bump_major, bump_minor, bump_patch)) != 1:
            raise WrongArgs("Need to specify exactly one bump argument")
        if bump_major:
            return self.bump_major()
        if bump_minor:
            return self.bump_minor()
        if bump_patch:
            return self.bump_patch()
        # TODO: stop using WrongArgs everywhere :)
        raise WrongArgs(
            "At least one of bump_major, bump_minor, bump_patch must be True"
        )

    @classmethod
    def get_minimal(cls):
        return cls("v0.0.1")
