from .config import CONFIG


class GitopsException(Exception):
    """Base class for all prototype exceptions."""

    def __init__(self, msg, *args):
        assert msg
        self.msg = msg
        super().__init__(msg, *args)


class ObjectNotFound(GitopsException):
    _message = "Requested model '{model}' wasn't found in registry"

    def __init__(self, model) -> None:
        self.message = self._message.format(model=model)
        super().__init__(self.message)


class VersionAlreadyRegistered(GitopsException):
    _message = (
        "Version '{version}' already was registered.\n"
        "Even if it was unregistered, you must use another name to avoid confusion."
    )

    def __init__(self, version) -> None:
        self.message = self._message.format(version=version)
        super().__init__(self.message)


class VersionExistsForCommit(GitopsException):
    _message = "The model {model} was already registered in this commit with version '{version}'."

    def __init__(self, model, version) -> None:
        self.message = self._message.format(model=model, version=version)
        super().__init__(self.message)


class VersionIsOld(GitopsException):
    _message = "Version '{suggested}' is younger than the latest {latest}"

    def __init__(self, latest, suggested) -> None:
        self.message = self._message.format(latest=latest, suggested=suggested)
        super().__init__(self.message)


class UnknownEnvironment(GitopsException):
    _message = f"Environment '{{env}}' is not present in your config file. Allowed envs are: {CONFIG.ENVIRONMENTS}."

    def __init__(self, env) -> None:
        self.message = self._message.format(env=env)
        super().__init__(self.message)


class NoActiveLabel(GitopsException):
    _message = "No active label '{label}' was found for {category} '{object}'"

    def __init__(self, label, category, object) -> None:
        self.message = self._message.format(
            label=label, category=category, object=object
        )
        super().__init__(self.message)


class RefNotFound(GitopsException):
    _message = "Ref '{ref}' was not found in the repository history"

    def __init__(self, ref) -> None:
        self.message = self._message.format(ref=ref)
        super().__init__(self.message)


class InvalidVersion(GitopsException):
    _message = "Supplied version {version} doesn't look like {cls} version"

    def __init__(self, version, cls) -> None:
        self.message = self._message.format(version=version, cls=cls)
        super().__init__(self.message)


class IncomparableVersions(GitopsException):
    message = "You can compare only versions of the same system."

    def __init__(self) -> None:
        super().__init__(self.message)
