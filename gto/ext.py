import subprocess
from abc import ABC, abstractmethod
from functools import lru_cache
from json import loads
from typing import Dict, List, Optional, Type, Union

import entrypoints
from mlem.utils.importing import import_string
from pydantic import BaseModel, parse_obj_as, validator

ENRICHMENT_ENRTYPOINT = "gto.enrichment"


class EnrichmentInfo(BaseModel, ABC):
    source: str

    @abstractmethod
    def get_object(self) -> BaseModel:
        raise NotImplementedError

    def get_dict(self):
        return self.get_object().dict()

    @abstractmethod
    def get_human_readable(self) -> str:
        raise NotImplementedError


class Enrichment(BaseModel, ABC):
    @abstractmethod
    def describe(self, obj: str) -> Optional[EnrichmentInfo]:
        raise NotImplementedError


class CLIEnrichmentInfo(EnrichmentInfo):
    data: Dict
    repr: str

    def get_object(self) -> BaseModel:
        return self

    def get_human_readable(self) -> str:
        return self.repr


class CLIEnrichment(Enrichment):
    cmd: str
    info_type: Union[str, Type[EnrichmentInfo]] = CLIEnrichmentInfo

    @validator("info_type")
    def info_class_validator(
        cls, value
    ):  # pylint: disable=no-self-argument,no-self-use  # noqa: B902
        if isinstance(value, type):
            return value
        info_class = import_string(value)
        if not isinstance(info_class, type) or not issubclass(
            info_class, EnrichmentInfo
        ):
            raise ValueError(
                "Wrong value for info_type: should be class or string path to class (e.g. `package.module.ClassName`)"
            )
        return info_class

    @property
    def info_class(self) -> Type[EnrichmentInfo]:
        return self.info_class_validator(self.info_type)

    def describe(self, obj: str) -> Optional[EnrichmentInfo]:
        try:
            data = loads(subprocess.check_output(self.cmd.split() + [obj]))
            return parse_obj_as(self.info_class, data)
        except subprocess.SubprocessError:
            return None


@lru_cache()
def _find_enrichments():
    eps = entrypoints.get_group_named(ENRICHMENT_ENRTYPOINT)
    return {k: ep.load() for k, ep in eps.items()}


@lru_cache()
def find_enrichments() -> List[Enrichment]:
    enrichments = _find_enrichments()
    res = []
    for e in enrichments:
        if isinstance(e, type) and issubclass(e, Enrichment) and not e.__fields_set__:
            res.append(e())
        if isinstance(e, Enrichment):
            res.append(e)
    return res


@lru_cache()
def find_enrichment_types() -> Dict[str, Type[Enrichment]]:
    enrichments = _find_enrichments()
    return {
        k: e
        for k, e in enrichments.items()
        if isinstance(e, type) and issubclass(e, Enrichment)
    }
