from functools import total_ordering
from typing import Union

import semver

from gto.constants import VersionPart
from gto.exceptions import GTOException, IncomparableVersions, InvalidVersion


class AbstractVersion:
    version: str

    def __init__(self, version) -> None:
        if not self.is_valid(version):
            raise InvalidVersion(version=version, cls=self.__class__)
        self.version = version

    @classmethod
    def is_valid(cls, version) -> bool:
        raise NotImplementedError

    def __eq__(self, other):
        return self.version == other.version

    def __lt__(self, other):
        raise NotImplementedError

    def bump(self, part: Union[VersionPart, str]) -> "AbstractVersion":
        raise NotImplementedError

    @classmethod
    def get_minimal(cls):
        raise NotImplementedError


@total_ordering
class NumberedVersion(AbstractVersion):
    @classmethod
    def is_valid(cls, version):
        if not isinstance(version, str):
            return False
        return version.startswith("v") and version[1:].isdigit()

    def to_number(self):
        return int(self.version[1:])

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
        return self.to_number() < other.to_number()

    def bump(self, part: Union[VersionPart, str] = VersionPart.MAJOR):
        part = VersionPart(part)
        if part != VersionPart.MAJOR:
            raise GTOException(f"With {self.__class__} you can only bump MAJOR part")
        return self.__class__(f"v{self.to_number() + 1}")

    @classmethod
    def get_minimal(cls):
        return cls("v1")


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
        except ValueError:
            return False

    @classmethod
    def parse(cls, version: str) -> "SemVer":
        """
        Parse version string to a Version instance.

        :param version: version string with "v" or "V" prefix
        :raises ValueError: when version does not start with "v" or "V"
        :return: a new instance
        """
        if not isinstance(version, str):
            raise ValueError("Version should be of type str")
        if version[0] not in ("v"):
            raise ValueError(
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

    def bump(self, part: Union[VersionPart, str] = VersionPart.PATCH):
        part = VersionPart(part)
        next_version = getattr(self.parse(self.version), f"bump_{part.value}")()
        return self.__class__(f"v{next_version}")

    @classmethod
    def get_minimal(cls):
        return cls("v0.0.1")
