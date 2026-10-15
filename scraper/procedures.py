"""Consulta G: care production by procedure, per IPRESS.

Used to answer the commercial question "does this clinic already offer ozone
therapy?". The monthly files are large (200 MB+), so the table is scanned
lazily and filtered to the target IPRESS before any rows reach memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from .tabular import clean_text, parse_int, read_source_csv
from .text import OZONE_MARKERS, fold_text

# Cheap superset used to keep the heavy scan inside Polars. Ozone has no accented
# characters, so a lowercase substring test cannot miss a real hit.
OZONE_PREFILTER = "ozon"
CORE_COLUMNS = ("CO_IPRESS", "PROCEDIMIENTO", "TOTAL")
_IPRESS = "CO_IPRESS"
_PROCEDURE = "PROCEDIMIENTO"
_TOTAL = "TOTAL"


@dataclass(frozen=True)
class OzoneTherapy:
    # `checked` separates "confirmed absent" from "not looked at yet".
    checked: bool = False
    performs: bool = False
    total_attendances: int = 0
    procedures: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OzoneDetection:
    """Result of asking Consulta G whether an IPRESS offers ozone therapy.

    `signal_available` is false when the published procedure catalogue contains
    no ozone procedure at all. In that case the question cannot be answered for
    anyone, so every entry stays unchecked: emitting `performs: false` would
    read as a confirmed negative when the source simply cannot express it.
    """

    signal_available: bool
    therapy: dict[str, OzoneTherapy]


def is_ozone_procedure(name: str) -> bool:
    folded = fold_text(name)
    return any(marker in folded for marker in OZONE_MARKERS)


def detect_ozone_therapy(path: Path, ipress_codes: set[str]) -> OzoneDetection:
    """Flag which of the requested IPRESS already record ozone procedures."""
    frame = (
        read_source_csv(path, lazy=True)
        .select(list(CORE_COLUMNS))
        .filter(
            pl.col(_IPRESS).is_in(sorted(ipress_codes))
            | pl.col(_PROCEDURE).str.to_lowercase().str.contains(OZONE_PREFILTER)
        )
    )

    seen: set[str] = set()
    hits: dict[str, list[tuple[str, int]]] = {}
    signal_available = False

    for row in frame.collect(engine="streaming").iter_rows(named=True):
        code = clean_text(row[_IPRESS])
        name = clean_text(row[_PROCEDURE])
        if code in ipress_codes:
            seen.add(code)
        if is_ozone_procedure(name):
            signal_available = True
            if code in ipress_codes:
                hits.setdefault(code, []).append((name, parse_int(row[_TOTAL])))

    if not signal_available:
        return OzoneDetection(
            signal_available=False,
            therapy={code: OzoneTherapy() for code in ipress_codes},
        )

    therapy = {code: OzoneTherapy() for code in ipress_codes}
    for code in seen:
        found = hits.get(code, [])
        therapy[code] = OzoneTherapy(
            checked=True,
            performs=bool(found),
            total_attendances=sum(attendance for _, attendance in found),
            procedures=sorted({name for name, _ in found}),
        )
    return OzoneDetection(signal_available=True, therapy=therapy)
