class GTOException(Exception):
    """Base class for all prototype exceptions."""

    def __init__(self, msg, *args):
        assert msg
        self.msg = msg
        super().__init__(msg, *args)


class NotFound(GTOException):
    """Raised when a requested resource is not found."""


class NoRepo(GTOException):
    _message = "No Git repo found in '{path}'"

    def __init__(self, path) -> None:
        self.message = self._message.format(path=path)
        super().__init__(self.message)


class NoFile(GTOException):
    _message = "No file/folder found in '{path}' for checkouted commit"

    def __init__(self, path) -> None:
        self.message = self._message.format(path=path)
        super().__init__(self.message)


class UnknownType(GTOException):
    _message = "Allowed types are: '{types}'"

    def __init__(self, type, types) -> None:
        self.message = self._message.format(type=type, types=types)
        super().__init__(self.message)


class ArtifactExists(GTOException):
    _message = "Enrichment for '{name}' already exists"

    def __init__(self, name) -> None:
        self.message = self._message.format(name=name)
        super().__init__(self.message)


class ArtifactNotFound(GTOException):
    _message = "Cannot find artifact"

    def __init__(self, name) -> None:
        self.message = self._message.format(name=name)
        super().__init__(self.message)


class PathIsUsed(GTOException):
    _message = "Provided path conflicts with '{path}' ('{type}' '{name}')"

    def __init__(self, type, name, path) -> None:
        self.message = self._message.format(type=type, name=name, path=path)
        super().__init__(self.message)


class VersionRequired(GTOException):
    _message = "No versions found for '{name}'"

    def __init__(self, name) -> None:
        self.message = self._message.format(name=name)
        super().__init__(self.message)


class ManyVersions(GTOException):
    _message = "'{versions}' versions of artifact '{name}' found"

    def __init__(self, name, versions) -> None:
        self.message = self._message.format(name=name, versions=versions)
        super().__init__(self.message)


class VersionAlreadyRegistered(GTOException):
    _message = "Version '{version}' already was registered.\n"

    def __init__(self, version) -> None:
        self.message = self._message.format(version=version)
        super().__init__(self.message)


class VersionExistsForCommit(GTOException):
    _message = "'{model}' is already registered in this commit with version '{version}'"

    def __init__(self, model, version) -> None:
        self.message = self._message.format(model=model, version=version)
        super().__init__(self.message)


class UnknownStage(GTOException):
    _message = "Allowed stages are: '{stages}'"

    def __init__(self, stage, stages) -> None:
        self.message = self._message.format(stage=stage, stages=stages)
        super().__init__(self.message)


class NoActivePromotion(GTOException):
    _message = "No version in stage '{stage}' was found for '{name}'"

    def __init__(self, stage, name) -> None:
        self.message = self._message.format(stage=stage, name=name)
        super().__init__(self.message)


class RefNotFound(GTOException):
    _message = "Ref '{ref}' was not found in the repository history"

    def __init__(self, ref) -> None:
        self.message = self._message.format(ref=ref)
        super().__init__(self.message)


class InvalidVersion(GTOException):
    _message = "Supplied version '{version}' doesn't look like valid {cls} version"

    def __init__(self, version, cls) -> None:
        self.message = self._message.format(version=version, cls=cls)
        super().__init__(self.message)


class IncomparableVersions(GTOException):
    _message = "You can compare only versions of the same system, but not '{}' and '{}'"

    def __init__(self, this, that) -> None:
        self.message = self._message.format(this, that)
        super().__init__(self.message)


class UnknownAction(GTOException):
    message = "Unknown action '{action}' was requested"

    def __init__(self, action) -> None:
        self.message = self.message.format(action=action)
        super().__init__(self.message)


class MissingArg(GTOException):
    message = "'{arg}' is required"

    def __init__(self, arg) -> None:
        self.message = self.message.format(arg=arg)
        super().__init__(self.message)


class WrongArgs(GTOException):
    pass
