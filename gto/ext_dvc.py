# from typing import Optional

# from pydantic import BaseModel
# from ruamel.yaml import safe_load

# from gto.ext import Enrichment, EnrichmentInfo


# class DVCEnrichmentInfo(EnrichmentInfo):
#     source = "dvc"
#     size: int
#     hash: str

#     def get_object(self) -> BaseModel:
#         return self

#     def get_human_readable(self) -> str:
#         return f"""DVC-tracked [{self.size} bytes]"""


# class DVCEnrichment(Enrichment):
#     def describe(self, obj: str) -> Optional[DVCEnrichmentInfo]:
#         try:
#             with open(obj + ".dvc", encoding="utf8") as f:
#                 dvc_data = safe_load(f)
#                 data = dvc_data["outs"][0]
#                 return DVCEnrichmentInfo(size=data["size"], hash=data["md5"])
#         except FileNotFoundError:
#             return None
