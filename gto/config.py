# pylint: disable=no-self-use, no-self-argument, inconsistent-return-statements, invalid-name, import-outside-toplevel
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, BaseSettings, validator
from pydantic.env_settings import InitSettingsSource
from ruamel.yaml import YAML

from gto.exceptions import (
    UnknownStage,
    UnknownType,
    ValidationError,
    WrongConfig,
)
from gto.ext import Enrichment, find_enrichment_types, find_enrichments

yaml = YAML(typ="safe", pure=True)
yaml.default_flow_style = False

CONFIG_FILE_NAME = ".gto"


def check_name_is_valid(name):
    return bool(re.match(r"[a-zA-Z0-9-/]*$", name))


def assert_name_is_valid(name):
    if not check_name_is_valid(name):
        raise ValidationError(
            f"Invalid value '{name}'. Only alphanumeric characters, '-', '/' are allowed."
        )


class EnrichmentConfig(BaseModel):
    type: str
    config: Dict = {}

    def load(self) -> Enrichment:
        return find_enrichment_types()[self.type](**self.config)


class NoFileConfig(BaseSettings):
    INDEX: str = "artifacts.yaml"
    TYPE_ALLOWED: List[str] = []
    STAGE_ALLOWED: List[str] = []
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    ENRICHMENTS: List[EnrichmentConfig] = []
    AUTOLOAD_ENRICHMENTS: bool = True
    CONFIG_FILE_NAME: Optional[str] = CONFIG_FILE_NAME
    EMOJIS: bool = True

    class Config:
        env_prefix = "gto_"

    def assert_type(self, name):
        assert_name_is_valid(name)
        if self.TYPE_ALLOWED and name not in self.TYPE_ALLOWED:
            raise UnknownType(name, self.TYPE_ALLOWED)

    def assert_stage(self, name):
        assert_name_is_valid(name)
        if self.stages and name not in self.stages:
            raise UnknownStage(name, self.stages)

    @property
    def enrichments(self) -> Dict[str, Enrichment]:
        res = {e.source: e for e in (e.load() for e in self.ENRICHMENTS)}
        if self.AUTOLOAD_ENRICHMENTS:
            return {**find_enrichments(), **res}
        return res

    @property
    def stages(self) -> List[str]:
        return self.STAGE_ALLOWED

    @validator("TYPE_ALLOWED")
    def types_are_valid(cls, v):
        for name in v:
            assert_name_is_valid(name)
        return v

    @validator("STAGE_ALLOWED")
    def stages_are_valid(cls, v):
        for name in v:
            assert_name_is_valid(name)
        return v


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


def read_registry_config(config_file_name):
    try:
        return RegistryConfig(CONFIG_FILE_NAME=config_file_name)
    except Exception as e:  # pylint: disable=bare-except
        raise WrongConfig(config_file_name) from e


CONFIG = NoFileConfig()
