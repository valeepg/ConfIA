"""Consulta A: health resources per IPRESS.

Supplies the installed capacity used by scoring (doctors, consulting rooms,
beds). One row per IPRESS per month, so the last published month wins.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .tabular import clean_text, parse_int, read_source_csv

COLUMNS = {
    "legal_name": "RAZON_SOC",
    "consulting_rooms": "CA_CONSULTORIOS",
    "functional_consulting_rooms": "CA_CONSULTORIOS_FN",
    "beds": "CA_CAMAS",
    "doctors_total": "CA_MEDICOS_TOTAL",
    "nurses": "CA_ENFERMERAS",
    "ambulances": "CA_AMBULANCIAS",
}
_YEAR = "ANHO"
_MONTH = "MES"
_IPRESS = "CO_IPRESS"


@dataclass(frozen=True)
class IpressCapacity:
    ipress_code: str
    legal_name: str | None = None
    period: str | None = None
    consulting_rooms: int = 0
    functional_consulting_rooms: int = 0
    beds: int = 0
    doctors_total: int = 0
    nurses: int = 0
    ambulances: int = 0


def _period_key(year: int, month: int) -> int:
    return year * 100 + month


def consolidate_capacity(path: Path, ipress_codes: set[str]) -> dict[str, IpressCapacity]:
    """Return capacity per IPRESS using only its most recent published month."""
    capacity: dict[str, IpressCapacity] = {
        code: IpressCapacity(ipress_code=code) for code in ipress_codes
    }
    frame = read_source_csv(path)
    frame = frame.filter(frame[_IPRESS].is_in(sorted(ipress_codes)))

    for row in frame.iter_rows(named=True):
        code = clean_text(row[_IPRESS])
        stamp = _period_key(parse_int(row[_YEAR]), parse_int(row[_MONTH]))
        current = capacity.get(code)
        if current is not None and current.period is not None:
            current_year, _, current_month = current.period.partition("-")
            if _period_key(parse_int(current_year), parse_int(current_month)) >= stamp:
                continue
        capacity[code] = IpressCapacity(
            ipress_code=code,
            legal_name=clean_text(row[COLUMNS["legal_name"]]) or None,
            period=f"{parse_int(row[_YEAR]):04d}-{parse_int(row[_MONTH]):02d}",
            **{
                field: parse_int(row[column])
                for field, column in COLUMNS.items()
                if field != "legal_name"
            },
        )
    return capacity
