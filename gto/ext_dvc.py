"""This is temporary file that should be moved to dvc.gto module"""
from posixpath import relpath
from typing import Any, Optional

import dvc.repo
import git

# from dvc.data.meta import Meta
from dvc.stage import Stage
from funcy import project
from pydantic import BaseModel, parse_obj_as

from gto.ext import Enrichment, EnrichmentInfo


class DVCEnrichmentInfo(EnrichmentInfo):
    source = "dvc"
    stage: Optional[Stage]
    meta: Any  # Meta
    use_cache: bool

    class Config:
        arbitrary_types_allowed = True

    def get_object(self) -> BaseModel:
        return self

    def get_human_readable(self) -> str:
        return f"""DVC-tracked [{self.meta.size} bytes]"""


class DVCEnrichment(Enrichment):
    source = "dvc"

    def describe(
        self, repo: git.Repo, obj: str, rev: Optional[str]
    ) -> Optional[DVCEnrichmentInfo]:
        with dvc.repo.Repo.open(repo.working_dir, rev=rev) as dvc_repo:
            for out in dvc_repo.index.outs:
                if relpath(out.fs_path, repo.working_dir) == obj:
                    return parse_obj_as(
                        DVCEnrichmentInfo,
                        project(vars(out), ["stage", "meta", "use_cache"]),
                    )
        return None

    def discover(
        self, repo: git.Repo, rev: Optional[str]
    ):  # pylint: disable=no-self-use
        with dvc.repo.Repo.open(repo.working_dir, rev=rev) as dvc_repo:
            deps = list(dvc_repo.index.deps)
            outs = list(dvc_repo.index.outs)
        return [*deps, *outs]
