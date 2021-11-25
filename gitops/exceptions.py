class BaseException(Exception):
    """Base class for all prototype exceptions."""

    def __init__(self, msg, *args):
        assert msg
        self.msg = msg
        super().__init__(msg, *args)


class ModelNotFound(BaseException):
    _message = "Requested model '{model}' wasn't found in registry"

    def __init__(self, model) -> None:
        self.message = self._message.format(model=model)
        super().__init__(self.message)
