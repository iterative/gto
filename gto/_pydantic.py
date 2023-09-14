__all__ = [
    "BaseModel",
    "BaseSettings",
    "ValidationError",
    "parse_obj_as",
    "validator",
    "InitSettingsSource",
]


try:
    from pydantic.v1 import (
        BaseModel,
        BaseSettings,
        ValidationError,
        parse_obj_as,
        validator,
    )
    from pydantic.v1.env_settings import InitSettingsSource
except ImportError:
    from pydantic import (  # type: ignore[no-redef,assignment]
        BaseModel,
        BaseSettings,
        ValidationError,
        parse_obj_as,
        validator,
    )
    from pydantic.env_settings import (  # type: ignore[no-redef,assignment]
        InitSettingsSource,
    )
