from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseSettings

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
    VERSION_BASE: str = "tag"
    VERSION_CONVENTION: str = "NumberedVersion"
    ENV_BASE: str = "tag"
    ENV_WHITELIST: List = ["production", "staging"]

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

    @property
    def versions_class(self):
        if self.VERSION_CONVENTION not in VERSIONS_MAPPING:
            raise ValueError(f"Unknown versioning system {self.VERSION_CONVENTION}")
        return VERSIONS_MAPPING[self.VERSION_CONVENTION]


CONFIG = RegistryConfig()
