from abc import ABC, abstractmethod
from functools import lru_cache
from importlib import import_module
from typing import Dict, Optional, Type

import entrypoints
from pydantic import BaseModel

ENRICHMENT_ENTRYPOINT = "gto.enrichment"


def import_string(path):
    split = path.split(".")
    module_name, object_name = ".".join(split[:-1]), split[-1]
    mod = import_module(module_name)
    try:
        return getattr(mod, object_name)
    except AttributeError as e:
        raise ImportError(f"No object {object_name} in module {module_name}") from e


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


class EnrichmentReader(BaseModel, ABC):
    source: str

    @abstractmethod
    def describe(
        self, repo: str, obj: str, rev: Optional[str]
    ) -> Optional[EnrichmentInfo]:
        raise NotImplementedError


# class CLIEnrichmentInfo(EnrichmentInfo):
#     data: Dict
#     repr: str

#     def get_object(self) -> BaseModel:
#         return self

#     def get_human_readable(self) -> str:
#         return self.repr


# class CLIEnrichment(EnrichmentReader):
#     cmd: str
#     info_type: Union[str, Type[EnrichmentInfo]] = CLIEnrichmentInfo

#     @validator("info_type")
#     def info_class_validator(
#         cls, value
#     ):  # pylint: disable=no-self-argument,no-self-use  # noqa: B902
#         if isinstance(value, type):
#             return value
#         info_class = import_string(value)
#         if not isinstance(info_class, type) or not issubclass(
#             info_class, EnrichmentInfo
#         ):
#             raise ValueError(
#                 "Wrong value for info_type: should be class or string path to class (e.g. `package.module.ClassName`)"
#             )
#         return info_class

#     @property
#     def info_class(self) -> Type[EnrichmentInfo]:
#         return self.info_class_validator(self.info_type)

#     def describe(self, obj: str) -> Optional[EnrichmentInfo]:
#         try:
#             data = loads(subprocess.check_output(self.cmd.split() + [obj]))
#             return parse_obj_as(self.info_class, data)
#         except subprocess.SubprocessError:
#             return None


@lru_cache()
def _find_enrichments():
    eps = entrypoints.get_group_named(ENRICHMENT_ENTRYPOINT)
    return {k: ep.load() for k, ep in eps.items()}


@lru_cache()
def find_enrichments() -> Dict[str, EnrichmentReader]:
    enrichments = _find_enrichments()
    res = {}
    for name, e in enrichments.items():
        # if isinstance(e, type) and issubclass(e, Enrichment) and not e.__fields_set__:
        if isinstance(e, type) and issubclass(e, EnrichmentReader):
            res[name] = e()
        if isinstance(e, EnrichmentReader):
            res[name] = e
    return res


@lru_cache()
def find_enrichment_types() -> Dict[str, Type[EnrichmentReader]]:
    enrichments = _find_enrichments()
    return {
        k: e
        for k, e in enrichments.items()
        if isinstance(e, type) and issubclass(e, EnrichmentReader)
    }
