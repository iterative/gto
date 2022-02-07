from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseSettings, validator

from .constants import BRANCH, TAG
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
    VERSION_BASE: str = TAG
    VERSION_CONVENTION: str = "NumberedVersion"
    VERSION_REQUIRED_FOR_ENV: bool = True
    ENV_BASE: str = BRANCH
    ENV_WHITELIST: List[str] = []
    ENV_BRANCH_MAPPING: Dict[str, str] = {}

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

    @validator("ENV_BASE", always=True)
    def validate_env_base(cls, value):  # pylint: disable=no-self-use, no-self-argument
        if value not in (BRANCH, TAG):
            raise ValueError("ENV_BASE must be either 'branch' or 'tag'")
        return value

    @validator("ENV_WHITELIST", always=True)
    def validate_env_whitelist(
        cls, value, values
    ):  # pylint: disable=no-self-use, no-self-argument
        if values["ENV_BASE"] == BRANCH:
            # logging.warning("ENV_WHITELIST is ignored when ENV_BASE is BRANCH")
            pass
        return value

    @validator("ENV_BRANCH_MAPPING", always=True)
    def validate_env_branch_mapping(  # pylint: disable=no-self-use, no-self-argument
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
