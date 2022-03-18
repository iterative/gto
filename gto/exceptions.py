class GTOException(Exception):
    """Base class for all prototype exceptions."""

    def __init__(self, msg, *args):
        assert msg
        self.msg = msg
        super().__init__(msg, *args)


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


class ArtifactExists(GTOException):
    _message = "Artifact '{name}' is already exists in Index"

    def __init__(self, name) -> None:
        self.message = self._message.format(name=name)
        super().__init__(self.message)


class ArtifactNotFound(GTOException):
    _message = "Artifact '{name}' doesn't exist in Index"

    def __init__(self, name) -> None:
        self.message = self._message.format(name=name)
        super().__init__(self.message)


class PathIsUsed(GTOException):
    _message = "Provided path conflicts with {path} ({type} {name})"

    def __init__(self, type, name, path) -> None:
        self.message = self._message.format(type=type, name=name, path=path)
        super().__init__(self.message)


class VersionRequired(GTOException):
    _message = "No versions found for '{name}'"

    def __init__(self, name, skip_deprecated=True) -> None:
        self.message = self._message.format(name=name) + (
            ", skipping deprecated" if skip_deprecated else ""
        )
        super().__init__(self.message)


class ManyVersions(GTOException):
    _message = "{versions} versions of artifact {name} found"

    def __init__(self, name, versions, skip_deprecated) -> None:
        self.message = self._message.format(
            name=name, versions=versions, skip_deprecated=skip_deprecated
        ) + (", skipping deprecated" if skip_deprecated else "")
        super().__init__(self.message)


class VersionAlreadyRegistered(GTOException):
    _message = (
        "Version '{version}' already was registered.\n"
        "Even if it was deprecated, you must use another name to avoid confusion."
    )

    def __init__(self, version) -> None:
        self.message = self._message.format(version=version)
        super().__init__(self.message)


class VersionExistsForCommit(GTOException):
    _message = "The model {model} was already registered in this commit with version '{version}'."

    def __init__(self, model, version) -> None:
        self.message = self._message.format(model=model, version=version)
        super().__init__(self.message)


class VersionIsOld(GTOException):
    _message = "Version '{suggested}' is younger than the latest {latest}"

    def __init__(self, latest, suggested) -> None:
        self.message = self._message.format(latest=latest, suggested=suggested)
        super().__init__(self.message)


class UnknownEnvironment(GTOException):
    _message = "Environment '{env}' is not present in your config file. Allowed envs are: {envs}."

    def __init__(self, env) -> None:
        # to avoid circular import
        from .config import CONFIG  # pylint: disable=import-outside-toplevel

        self.message = self._message.format(env=env, envs=CONFIG.ENV_WHITELIST)
        super().__init__(self.message)


class NoActiveLabel(GTOException):
    _message = "No active label '{label}' was found for '{name}'"

    def __init__(self, label, name) -> None:
        self.message = self._message.format(label=label, name=name)
        super().__init__(self.message)


class RefNotFound(GTOException):
    _message = "Ref '{ref}' was not found in the repository history"

    def __init__(self, ref) -> None:
        self.message = self._message.format(ref=ref)
        super().__init__(self.message)


class InvalidVersion(GTOException):
    _message = "Supplied version {version} doesn't look like {cls} version"

    def __init__(self, version, cls) -> None:
        self.message = self._message.format(version=version, cls=cls)
        super().__init__(self.message)


class IncomparableVersions(GTOException):
    _message = "You can compare only versions of the same system, but not {} and {}"

    def __init__(self, this, that) -> None:
        self.message = self._message.format(this, that)
        super().__init__(self.message)


class UnknownAction(GTOException):
    message = "Unknown action '{action}' was requested."

    def __init__(self, action) -> None:
        self.message = self.message.format(action=action)
        super().__init__(self.message)


class MissingArg(GTOException):
    message = "'{arg}' is required."

    def __init__(self, arg) -> None:
        self.message = self.message.format(arg=arg)
        super().__init__(self.message)
