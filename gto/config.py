# pylint: disable=no-self-argument, inconsistent-return-statements, invalid-name, import-outside-toplevel
import pathlib
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings import (
    YamlConfigSettingsSource as _YamlConfigSettingsSource,
)
from ruamel.yaml import YAML

from gto.constants import assert_name_is_valid
from gto.exceptions import UnknownStage, UnknownType, WrongConfig
from gto.ext import EnrichmentReader, find_enrichment_types, find_enrichments

yaml = YAML(typ="safe", pure=True)
yaml.default_flow_style = False

CONFIG_FILE_NAME = ".gto"


class EnrichmentConfig(BaseModel):
    type: str
    config: Dict = {}

    def load(self) -> EnrichmentReader:
        return find_enrichment_types()[self.type](**self.config)


class NoFileConfig(BaseSettings):  # type: ignore[valid-type]
    INDEX: str = "artifacts.yaml"
    CONFIG_FILE_NAME: Optional[str] = CONFIG_FILE_NAME
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    EMOJIS: bool = True

    types: Optional[List[str]] = None
    stages: Optional[List[str]] = None
    enrichments: List[EnrichmentConfig] = Field(default_factory=list)
    autoload_enrichments: bool = True

    model_config = SettingsConfigDict(env_prefix="gto_")

    def assert_type(self, name):
        assert_name_is_valid(name)
        # pylint: disable-next=unsupported-membership-test
        if self.types is not None and name not in self.types:
            raise UnknownType(name, self.types)

    def assert_stage(self, name):
        assert_name_is_valid(name)
        # pylint: disable-next=unsupported-membership-test
        if self.stages is not None and name not in self.stages:
            raise UnknownStage(name, self.stages)

    @property
    def enrichments_(self) -> Dict[str, EnrichmentReader]:
        res = {e.source: e for e in (e.load() for e in self.enrichments)}
        if self.autoload_enrichments:
            return {**find_enrichments(), **res}
        return res

    @field_validator("types")
    @classmethod
    def types_are_valid(cls, v):  # pylint: disable=no-self-use
        if v:
            for name in v:
                assert_name_is_valid(name)
        return v

    @field_validator("stages")
    @classmethod
    def stages_are_valid(cls, v):  # pylint: disable=no-self-use
        if v:
            for name in v:
                assert_name_is_valid(name)
        return v

    def check_index_exist(self, repo: str):
        index = pathlib.Path(repo) / pathlib.Path(self.INDEX)
        return index.exists() and index.is_file()


class YamlConfigSettingsSource(_YamlConfigSettingsSource):
    def _read_file(self, file_path: pathlib.Path) -> dict[str, Any]:
        with open(file_path, encoding=self.yaml_file_encoding) as yaml_file:
            return yaml.load(yaml_file) or {}


class RegistryConfig(NoFileConfig):
    model_config = SettingsConfigDict(env_prefix="gto_", env_file_encoding="utf-8")

    def config_file_exists(self):
        config = pathlib.Path(self.CONFIG_FILE_NAME)
        return config.exists() and config.is_file()


def read_registry_config(config_file_name) -> "RegistryConfig":
    class _RegistryConfig(RegistryConfig):
        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ):
            encoding = getattr(settings_cls.model_config, "env_file_encoding", "utf-8")
            return (
                init_settings,
                env_settings,
                (
                    YamlConfigSettingsSource(
                        settings_cls,
                        yaml_file=config_file_name,
                        yaml_file_encoding=encoding,
                    )
                ),
                dotenv_settings,
                file_secret_settings,
            )

    try:
        return _RegistryConfig(CONFIG_FILE_NAME=config_file_name)
    except Exception as e:  # pylint: disable=bare-except
        raise WrongConfig(config_file_name) from e


CONFIG = NoFileConfig()
