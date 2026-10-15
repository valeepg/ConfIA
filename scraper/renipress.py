"""RENIPRESS: the national registry of health service providers.

This is the prospect base (RF-01). The registry publishes the establishment
identity, location, phone and coordinates, but no RUC, email or medical director, so
the target profile here is structural, not commercial.

The coordinate columns are named `NORTE` and `ESTE`, and the name is misleading: measured
over the 2.459 targets, the values are **latitude and longitude** (NORTE runs -18,07 to 0,
ESTE -81,28 to 0, and not one value sits in the UTM range). Trusting the column name
would have put every clinic in the wrong place, so the contract names them latitude and
longitude and the parser validates them against the ranges of Peru.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .config import ACTIVE_STATUS, TARGET_CATEGORIES, TARGET_INSTITUTIONS
from .tabular import clean_text, read_source_csv

RAWNESS = 36128  # documented row count of the 2026 dataset, used only as a sanity hint

# Domain field -> published column. Missing columns mean the publisher changed
# the schema, which must fail loudly instead of producing empty prospects.
COLUMNS = {
    "ipress_code": "COD_IPRESS",
    "name": "NOMBRE",
    "institution": "INSTITUCION",
    "classification": "CLASIFICACION",
    "establishment_type": "TIPO_ESTABLECIMIENTO",
    "department": "DEPARTAMENTO",
    "province": "PROVINCIA",
    "district": "DISTRITO",
    "ubigeo": "UBIGEO",
    "address": "DIRECCION",
    "category": "CATEGORIA",
    "phone": "TELEFONO",
    "schedule": "HORARIO",
    "status": "ESTADO",
}

# The registry calls these NORTE and ESTE. They are latitude and longitude: see the
# module docstring for the measurement that established it.
COORDINATE_COLUMNS = {"latitude": "NORTE", "longitude": "ESTE"}

# The ranges of Peru, plus one deliberate effect: the upper latitude bound also throws
# out the `-6e-08` sentinel that two of the 2.093 published coordinates carry, which is
# the point (0,0) in the ocean off Africa. A missing coordinate dressed as a real one is
# worse than a null.
_PERU_LATITUDE = (-19.0, -0.05)
_PERU_LONGITUDE = (-81.5, -68.0)


class UnexpectedColumns(RuntimeError):
    """The published CSV does not carry the columns the pipeline depends on."""


@dataclass(frozen=True)
class Ipress:
    ipress_code: str
    name: str
    institution: str
    classification: str
    establishment_type: str
    department: str
    province: str
    district: str
    ubigeo: str
    address: str
    category: str
    phone: str
    schedule: str
    status: str
    # Unknown when the registry publishes nothing, or only the (0,0) sentinel.
    latitude: float | None = None
    longitude: float | None = None


def parse_coordinate(value: object, bounds: tuple[float, float]) -> float | None:
    """Read a published coordinate, or `None` when it is missing or implausible."""
    text = clean_text(value)
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if bounds[0] <= number <= bounds[1] else None


def read_renipress(path: Path) -> Iterator[Ipress]:
    """Stream the RENIPRESS CSV as `Ipress` records."""
    frame = read_source_csv(path)
    available = set(frame.collect_schema().names())
    needed = list(COLUMNS.values()) + list(COORDINATE_COLUMNS.values())
    missing = sorted(column for column in needed if column not in available)
    if missing:
        raise UnexpectedColumns(
            "RENIPRESS is missing expected columns: " + ", ".join(missing)
        )

    for row in frame.iter_rows(named=True):
        yield Ipress(
            **{field: clean_text(row[column]) for field, column in COLUMNS.items()},
            latitude=parse_coordinate(row[COORDINATE_COLUMNS["latitude"]], _PERU_LATITUDE),
            longitude=parse_coordinate(row[COORDINATE_COLUMNS["longitude"]], _PERU_LONGITUDE),
        )


def filter_target_profile(rows: Iterable[Ipress]) -> list[Ipress]:
    """Keep private, active establishments of category I-3 / I-4."""
    return [
        row
        for row in rows
        if row.status == ACTIVE_STATUS
        and row.institution in TARGET_INSTITUTIONS
        and row.category in TARGET_CATEGORIES
    ]
