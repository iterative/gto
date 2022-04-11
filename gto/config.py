# pylint: disable=no-self-use, no-self-argument, inconsistent-return-statements, invalid-name, import-outside-toplevel
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, BaseSettings
from pydantic.env_settings import InitSettingsSource
from ruamel.yaml import YAML

from gto.exceptions import UnknownStage, UnknownType
from gto.ext import Enrichment, find_enrichment_types, find_enrichments

yaml = YAML(typ="safe", pure=True)
yaml.default_flow_style = False

CONFIG_FILE_NAME = ".gto"


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


class EnrichmentConfig(BaseModel):
    type: str
    config: Dict = {}

    def load(self) -> Enrichment:
        return find_enrichment_types()[self.type](**self.config)


class RegistryConfig(BaseSettings):
    INDEX: str = "artifacts.yaml"
    TYPE_ALLOWED: List[str] = []
    STAGE_ALLOWED: List[str] = []
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    ENRICHMENTS: List[EnrichmentConfig] = []
    AUTOLOAD_ENRICHMENTS: bool = True
    CONFIG_FILE_NAME: Optional[str] = CONFIG_FILE_NAME
    EMOJIS: bool = True

    def assert_type(self, name):
        if not self.check_type(name):
            raise UnknownType(name, self.TYPE_ALLOWED)

    def check_type(self, name):
        return name in self.TYPE_ALLOWED or not self.TYPE_ALLOWED

    @property
    def enrichments(self) -> Dict[str, Enrichment]:
        res = {e.source: e for e in (e.load() for e in self.ENRICHMENTS)}
        if self.AUTOLOAD_ENRICHMENTS:
            return {**find_enrichments(), **res}
        return res

    def assert_stage(self, name):
        if not self.check_stage(name):
            raise UnknownStage(name, self.stages)

    def check_stage(self, name):
        return name in self.stages or not self.stages

    @property
    def stages(self) -> List[str]:
        return self.STAGE_ALLOWED

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

    # @validator("VERSION_REQUIRED_FOR_ENV", always=True)
    # def validate_version_required_for_env(cls, value):
    #     if not value:
    #         raise NotImplementedError
    #     return value

    # TODO: now fails, make this work
    # @validator("ENV_BASE", always=True, pre=True)
    # def validate_env_base(cls, value):
    #     if value not in cls.ENV_MANAGERS_MAPPING:
    #         raise ValueError(f"ENV_BASE must be one of: {cls.ENV_MANAGERS_MAPPING.keys()}")
    #     return value

    # @validator("ENV_WHITELIST", always=True)
    # def validate_env_whitelist(cls, value, values):
    #     if values["ENV_BASE"] == BRANCH:
    #         # logging.warning("ENV_WHITELIST is ignored when ENV_BASE is BRANCH")
    #         pass
    #     return value

    # @validator("ENV_BRANCH_MAPPING", always=True)
    # def validate_env_branch_mapping(
    #     cls, value: Dict[str, str], values
    # ) -> Dict[str, str]:
    #     if values["ENV_BASE"] != BRANCH:
    #         # logging.warning("ENV_BRANCH_MAPPING is ignored when ENV_BASE is not BRANCH")
    #         return value
    #     if not isinstance(value, dict):
    #         raise ValueError(
    #             f"ENV_BRANCH_MAPPING must be a dict, got {type(value)}",
    #             "ENV_BRANCH_MAPPING",
    #         )
    #     if not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
    #         raise ValueError(
    #             "ENV_BRANCH_MAPPING must be a dict of str:str", "ENV_BRANCH_MAPPING"
    #         )
    #     return value


CONFIG = RegistryConfig()
