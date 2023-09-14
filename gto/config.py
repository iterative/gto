# pylint: disable=no-self-argument, inconsistent-return-statements, invalid-name, import-outside-toplevel
import pathlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from ruamel.yaml import YAML

from gto.constants import assert_name_is_valid
from gto.exceptions import UnknownStage, WrongConfig

yaml = YAML(typ="safe", pure=True)
yaml.default_flow_style = False

CONFIG_FILE_NAME = ".gto"


class NoFileConfig(BaseSettings):
    INDEX: str = "artifacts.yaml"
    STAGES: Optional[List[str]] = None
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    CONFIG_FILE_NAME: str = CONFIG_FILE_NAME
    EMOJIS: bool = True
    model_config = SettingsConfigDict(env_prefix="gto_")

    def assert_stage(self, name):
        assert_name_is_valid(name)
        if self.STAGES is not None:
            if name not in self.STAGES:
                raise UnknownStage(name, self.STAGES)

    @field_validator("STAGES")
    @classmethod
    def stages_are_valid(cls, v):
        if v:
            for name in v:
                assert_name_is_valid(name)
        return v

    def check_index_exist(self, repo: str):
        index = pathlib.Path(repo) / pathlib.Path(self.INDEX)
        return index.exists() and index.is_file()


def config_settings_source(settings: "RegistryConfig") -> Dict[str, Any]:
    """
    A simple settings source that loads variables from a yaml file in GTO DIR
    """

    encoding = settings.__config__.env_file_encoding
    config_file = getattr(settings, "CONFIG_FILE_NAME", CONFIG_FILE_NAME)
    if not isinstance(config_file, Path):
        config_file = Path(config_file)
    if not config_file.exists():
        return {}
    conf = yaml.load(config_file.read_text(encoding=encoding))

    return {k.upper(): v for k, v in conf.items()} if conf else {}


class YamlSettingsSource(PydanticBaseSettingsSource):
    """
    Source class for loading values from yaml file.
    """

    def __init__(self, settings_cls: Type[BaseSettings]):
        self.init_kwargs: Dict[str, Any] = {}
        config_file = Path(CONFIG_FILE_NAME)
        if config_file.exists():
            self.init_kwargs = yaml.load(config_file.read_text(encoding="utf-8")) or {}

        self.init_kwargs = {k.upper(): v for k, v in self.init_kwargs.items()}

        super().__init__(settings_cls)

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> Tuple[Any, str, bool]:
        # Nothing to do here. Only implement the return statement to make mypy happy
        return None, "", False

    def __call__(self) -> Dict[str, Any]:
        return self.init_kwargs


class RegistryConfig(NoFileConfig):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        return (
            init_settings,
            env_settings,
            YamlSettingsSource(settings_cls),
            file_secret_settings,
        )

    def config_file_exists(self):
        config = pathlib.Path(self.CONFIG_FILE_NAME)
        return config.exists() and config.is_file()


def read_registry_config(config_file_name):
    try:
        return RegistryConfig(CONFIG_FILE_NAME=config_file_name)
    except Exception as e:  # pylint: disable=bare-except
        raise WrongConfig(config_file_name) from e


CONFIG = NoFileConfig()
