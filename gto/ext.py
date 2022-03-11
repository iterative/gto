from abc import ABC, abstractmethod
from functools import lru_cache
from typing import List

import entrypoints
from pydantic import BaseModel

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
    def is_enriched(self, obj: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def describe(self, obj: str) -> EnrichmentInfo:
        raise NotImplementedError


@lru_cache()
def find_enrichments() -> List[Enrichment]:
    eps = entrypoints.get_group_named(ENRICHMENT_ENRTYPOINT)
    enrichments = [ep.load() for _, ep in eps.items()]
    enrichments = [
        e() if isinstance(e, type) and issubclass(e, Enrichment) else e
        for e in enrichments
    ]
    return [e for e in enrichments if isinstance(e, Enrichment)]
