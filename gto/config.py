# pylint: disable=no-self-use, no-self-argument, inconsistent-return-statements, invalid-name, import-outside-toplevel
import pathlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseSettings, validator
from pydantic.env_settings import InitSettingsSource
from ruamel.yaml import YAML

from gto.constants import assert_name_is_valid
from gto.exceptions import UnknownStage, WrongConfig

yaml = YAML(typ="safe", pure=True)
yaml.default_flow_style = False

CONFIG_FILE_NAME = ".gto"


class NoFileConfig(BaseSettings):
    INDEX: str = "artifacts.yaml"
    STAGES: Optional[List[str]]
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    CONFIG_FILE_NAME: Optional[str] = CONFIG_FILE_NAME
    EMOJIS: bool = True

    class Config:
        env_prefix = "gto_"

    def assert_stage(self, name):
        assert_name_is_valid(name)
        if self.STAGES is not None and name not in self.STAGES:
            raise UnknownStage(name, self.STAGES)

    @validator("STAGES")
    def stages_are_valid(cls, v):
        if v:
            for name in v:
                assert_name_is_valid(name)
        return v

    def check_index_exist(self, repo: str):
        index = pathlib.Path(repo) / pathlib.Path(self.INDEX)
        return index.exists() and index.is_file()


def _set_location_init_source(init_source: InitSettingsSource):
    def inner(settings: "RegistryConfig"):
        if "CONFIG_FILE_NAME" in init_source.init_kwargs:
            settings.__dict__["CONFIG_FILE_NAME"] = init_source.init_kwargs[
                "CONFIG_FILE_NAME"
            ]
        return {}

    return inner


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


class RegistryConfig(NoFileConfig):
    class Config:
        env_prefix = "gto_"
        env_file_encoding = "utf-8"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                _set_location_init_source(init_settings),
                init_settings,
                env_settings,
                config_settings_source,
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
