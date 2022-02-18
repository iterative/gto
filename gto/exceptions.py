class gtoException(Exception):
    """Base class for all prototype exceptions."""

    def __init__(self, msg, *args):
        assert msg
        self.msg = msg
        super().__init__(msg, *args)


class ObjectNotFound(gtoException):
    _message = "Requested '{name}' wasn't found in registry"

    def __init__(self, name) -> None:
        self.message = self._message.format(name=name)
        super().__init__(self.message)


class VersionAlreadyRegistered(gtoException):
    _message = (
        "Version '{version}' already was registered.\n"
        "Even if it was unregistered, you must use another name to avoid confusion."
    )

    def __init__(self, version) -> None:
        self.message = self._message.format(version=version)
        super().__init__(self.message)


class VersionExistsForCommit(gtoException):
    _message = "The model {model} was already registered in this commit with version '{version}'."

    def __init__(self, model, version) -> None:
        self.message = self._message.format(model=model, version=version)
        super().__init__(self.message)


class VersionIsOld(gtoException):
    _message = "Version '{suggested}' is younger than the latest {latest}"

    def __init__(self, latest, suggested) -> None:
        self.message = self._message.format(latest=latest, suggested=suggested)
        super().__init__(self.message)


class UnknownEnvironment(gtoException):
    _message = "Environment '{env}' is not present in your config file. Allowed envs are: {envs}."

    def __init__(self, env) -> None:
        # to avoid circular import
        from .config import CONFIG  # pylint: disable=import-outside-toplevel

        self.message = self._message.format(env=env, envs=CONFIG.ENV_WHITELIST)
        super().__init__(self.message)


class NoActiveLabel(gtoException):
    _message = "No active label '{label}' was found for '{name}'"

    def __init__(self, label, name) -> None:
        self.message = self._message.format(label=label, name=name)
        super().__init__(self.message)


class RefNotFound(gtoException):
    _message = "Ref '{ref}' was not found in the repository history"

    def __init__(self, ref) -> None:
        self.message = self._message.format(ref=ref)
        super().__init__(self.message)


class InvalidVersion(gtoException):
    _message = "Supplied version {version} doesn't look like {cls} version"

    def __init__(self, version, cls) -> None:
        self.message = self._message.format(version=version, cls=cls)
        super().__init__(self.message)


class IncomparableVersions(gtoException):
    message = "You can compare only versions of the same system."

    def __init__(self) -> None:
        super().__init__(self.message)


class UnknownAction(gtoException):
    message = "Unknown action '{action}' was requested."

    def __init__(self, action) -> None:
        self.message = self.message.format(action=action)
        super().__init__(self.message)


class MissingArg(gtoException):
    message = "'{arg}' is required."

    def __init__(self, arg) -> None:
        self.message = self.message.format(arg=arg)
        super().__init__(self.message)
