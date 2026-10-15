"""Open-data ingestion for the B2B outbound engine (Module 1: RF-01, RF-02).

Sources are public SUSALUD datasets resolved through its CKAN API:

* RENIPRESS            - national registry of health service providers
* Consulta A           - health resources per IPRESS (installed capacity)
* Consulta G           - care production per procedure (ozone detection)

No LLM is involved in extraction: every field lives at a fixed position in a
published CSV, so extraction is deterministic and free. LLM usage belongs to the
outbound drafting module, downstream of this one.
"""

from .contract import CONTRACT_VERSION, PIPELINE_STAGES, Prospect, ProspectArchive
from .pipeline import PipelineReport, run

__all__ = [
    "CONTRACT_VERSION",
    "PIPELINE_STAGES",
    "PipelineReport",
    "Prospect",
    "ProspectArchive",
    "run",
]
