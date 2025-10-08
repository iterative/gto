from abc import ABC, abstractmethod
from functools import lru_cache
from importlib import import_module
from typing import Dict, Optional, Type, Union

import entrypoints
from pydantic import BaseModel
from scmrepo.git import Git

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
        return self.get_object().model_dump()

    @abstractmethod
    def get_human_readable(self) -> str:
        raise NotImplementedError


class EnrichmentReader(BaseModel, ABC):
    source: str

    @abstractmethod
    def describe(
        self, url_or_scm: Union[str, Git], obj: str, rev: Optional[str]
    ) -> Optional[EnrichmentInfo]:
        raise NotImplementedError


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
            res[name] = e()  # type: ignore[call-arg]
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
