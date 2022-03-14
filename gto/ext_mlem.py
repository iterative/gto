"""This is temporary file that should be moved to mlem.gto module"""
from typing import Optional

from mlem.core.errors import MlemObjectNotFound
from mlem.core.metadata import load_meta
from mlem.core.objects import DatasetMeta, MlemMeta, ModelMeta
from pydantic import BaseModel

from gto.ext import Enrichment, EnrichmentInfo


class MlemInfo(EnrichmentInfo):
    meta: MlemMeta

    def get_object(self) -> BaseModel:
        return self.meta

    def get_human_readable(self) -> str:
        # TODO: create `.describe` method in MlemMeta https://github.com/iterative/mlem/issues/98
        description = f"""Mlem {self.meta.object_type}"""
        if isinstance(self.meta, ModelMeta):
            description += f": {self.meta.model_type.type}"
        if isinstance(self.meta, DatasetMeta):
            description += f": {self.meta.dataset.dataset_type.type}"
        return description


class MlemEnrichment(Enrichment):
    def describe(self, obj: str) -> Optional[MlemInfo]:
        try:
            return MlemInfo(source="mlem", meta=load_meta(obj))
        except MlemObjectNotFound:
            return None
