from .config import CONFIG


class BaseException(Exception):  # pylint: disable=redefined-builtin
    """Base class for all prototype exceptions."""

    def __init__(self, msg, *args):
        assert msg
        self.msg = msg
        super().__init__(msg, *args)


class ObjectNotFound(BaseException):
    _message = "Requested model '{model}' wasn't found in registry"

    def __init__(self, model) -> None:
        self.message = self._message.format(model=model)
        super().__init__(self.message)


class VersionAlreadyRegistered(BaseException):
    _message = (
        "Version '{version}' already was registered.\n"
        "Even if it was unregistered, you must use another name to avoid confusion."
    )

    def __init__(self, version) -> None:
        self.message = self._message.format(version=version)
        super().__init__(self.message)


class VersionExistsForCommit(BaseException):
    _message = "The model {model} was already registered in this commit with version '{version}'."

    def __init__(self, model, version) -> None:
        self.message = self._message.format(model=model, version=version)
        super().__init__(self.message)


class VersionIsOld(BaseException):
    _message = "Version '{suggested}' is younger than the latest {latest}"

    def __init__(self, latest, suggested) -> None:
        self.message = self._message.format(latest=latest, suggested=suggested)
        super().__init__(self.message)


class UnknownEnvironment(BaseException):
    _message = f"Environment '{{env}}' is not present in your config file. Allowed envs are: {CONFIG.ENVIRONMENTS}."

    def __init__(self, env) -> None:
        self.message = self._message.format(env=env)
        super().__init__(self.message)
