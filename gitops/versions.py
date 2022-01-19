from functools import total_ordering

from gitops.exceptions import IncomparableVersions, InvalidVersion


class AbstractVersion:
    version: str

    def __init__(self, version) -> None:
        if not self.__class__.is_valid(version):
            raise InvalidVersion(version=version, cls=self.__class__)
        self.version = version

    @classmethod
    def is_valid(cls, version) -> bool:
        raise NotImplementedError

    def __eq__(self, other):
        return self.version == other.version

    def __lt__(self, other):
        raise NotImplementedError

    def bump(self):
        raise NotImplementedError


@total_ordering
class NumberedVersion(AbstractVersion):
    @classmethod
    def is_valid(cls, version):
        return version.startswith("v") and version[1:].isdigit()

    def to_number(self):
        return int(self.version[1:])

    def __eq__(self, other):
        if isinstance(other, str):
            other = NumberedVersion(other)
        if not isinstance(other, NumberedVersion):
            raise IncomparableVersions()
        return self.version == other.version

    def __lt__(self, other):
        if isinstance(other, str):
            other = NumberedVersion(other)
        if not isinstance(other, NumberedVersion):
            raise IncomparableVersions()
        return self.to_number() < other.to_number()

    def bump(self):
        return NumberedVersion(f"v{self.to_number() + 1}")


class SemVer(AbstractVersion):  # pylint: disable=abstract-method
    pass
