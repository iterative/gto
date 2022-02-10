# pylint: disable=no-self-use, no-self-argument, inconsistent-return-statements
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseSettings, validator

from .constants import BRANCH, TAG
from .exceptions import UnknownEnvironment
from .versions import NumberedVersion, SemVer

CONFIG_FILE = Path(__file__).parent.parent / "gitops_config.yaml"
VERSIONS_MAPPING = {"NumberedVersion": NumberedVersion, "SemVer": SemVer}


def config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    """
    A simple settings source that loads variables from a yaml file in MLEM DIR
    """

    encoding = settings.__config__.env_file_encoding
    config_file = CONFIG_FILE
    if not config_file.exists():
        return {}
    conf = yaml.safe_load(config_file.read_text(encoding=encoding))

    return {k.upper(): v for k, v in conf.items()} if conf else {}


class RegistryConfig(BaseSettings):
    INDEX: str = "index.yaml"
    VERSION_BASE: str = TAG
    VERSION_CONVENTION: str = "NumberedVersion"
    VERSION_REQUIRED_FOR_ENV: bool = True
    ENV_BASE: str = BRANCH
    ENV_WHITELIST: List[str] = []
    ENV_BRANCH_MAPPING: Dict[str, str] = {}

    def assert_env(self, name):
        if not self.check_env(name):
            raise UnknownEnvironment(name)

    def check_env(self, name):
        if self.ENV_BASE == TAG:
            return name in self.ENV_WHITELIST or not self.ENV_WHITELIST
        if self.ENV_BASE == BRANCH:
            return name in self.ENV_BRANCH_MAPPING or not self.ENV_BRANCH_MAPPING

    def branch_to_env(self, branch_name):
        if self.ENV_BRANCH_MAPPING:
            return self.ENV_BRANCH_MAPPING[branch_name]
        return branch_name

    def env_to_branch(self, env_name):
        if self.ENV_BRANCH_MAPPING:
            return {value: key for key, value in self.ENV_BRANCH_MAPPING.items()}[
                env_name
            ]

    class Config:
        env_prefix = "gitops_"
        env_file_encoding = "utf-8"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
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

    @validator("ENV_BASE", always=True)
    def validate_env_base(cls, value):
        if value not in (BRANCH, TAG):
            raise ValueError("ENV_BASE must be either 'branch' or 'tag'")
        return value

    @validator("ENV_WHITELIST", always=True)
    def validate_env_whitelist(cls, value, values):
        if values["ENV_BASE"] == BRANCH:
            # logging.warning("ENV_WHITELIST is ignored when ENV_BASE is BRANCH")
            pass
        return value

    @validator("ENV_BRANCH_MAPPING", always=True)
    def validate_env_branch_mapping(
        cls, value: Dict[str, str], values
    ) -> Dict[str, str]:
        if values["ENV_BASE"] != BRANCH:
            # logging.warning("ENV_BRANCH_MAPPING is ignored when ENV_BASE is not BRANCH")
            return value
        if not isinstance(value, dict):
            raise ValueError(
                f"ENV_BRANCH_MAPPING must be a dict, got {type(value)}",
                "ENV_BRANCH_MAPPING",
            )
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            raise ValueError(
                "ENV_BRANCH_MAPPING must be a dict of str:str", "ENV_BRANCH_MAPPING"
            )
        return value

    @property
    def versions_class(self):
        if self.VERSION_CONVENTION not in VERSIONS_MAPPING:
            raise ValueError(f"Unknown versioning system {self.VERSION_CONVENTION}")
        return VERSIONS_MAPPING[self.VERSION_CONVENTION]


CONFIG = RegistryConfig()
