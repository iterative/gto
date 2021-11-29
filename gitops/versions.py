from functools import total_ordering


class AbstractVersion:
    version: str

    def __init__(self, version) -> None:
        assert self.__class__.is_valid(
            version
        ), f"Supplied version doesn't look like {self.__class__} version"
        self.version = version

    @classmethod
    def is_valid(cls) -> bool:
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
    def is_valid(self, version):
        return version.startswith("v") and version[1:].isdigit()

    def to_number(self):
        return int(self.version[1:])

    def __eq__(self, other):
        if isinstance(other, str):
            other = NumberedVersion(other)
        assert isinstance(
            other, NumberedVersion
        ), "You can compare only versions of the same system."
        return self.version == other.version

    def __lt__(self, other):
        if isinstance(other, str):
            other = NumberedVersion(other)
        assert isinstance(
            other, NumberedVersion
        ), "You can compare only versions of the same system."
        return self.to_number() < other.to_number()

    def bump(self):
        return NumberedVersion(f"v{self.to_number() + 1}")


class SemVer(AbstractVersion):
    pass
