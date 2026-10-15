"""Resource discovery against the SUSALUD CKAN API.

The published filename carries the dataset revision (`RENIPRESS_2026_v7.csv`,
`ConsultaG_2026_08_v1.csv`), so it is resolved at run time from the package
metadata instead of being pinned in code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from .config import CKAN_API_URL, DATASETS, DATASET_ALTERNATIVES, USER_AGENT


class NoResourcesError(RuntimeError):
    """No published resource matches the requested format and period."""


class CkanError(RuntimeError):
    """The CKAN API answered with an error or an unexpected payload."""


class DatasetUnavailable(CkanError):
    """No candidate identifier for this source resolves any more.

    Measured on 14-10-2026: SUSALUD removed the historical health-resources package, so the
    identifier this project used started answering 404 while the CSV already on disk stayed
    valid. The caller decides whether a local copy can stand in.
    """


_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_ROMAN_NUMERALS = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
    "xi": 11,
    "xii": 12,
}
_YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
# Word boundaries matter: without them the roman numeral `i` matches the letter
# inside ordinary words such as "Produccion" and every period becomes 1.
_MONTH_PATTERN = re.compile(r"\b(?:" + "|".join(_MONTHS) + r")\b", re.IGNORECASE)
_ROMAN_PATTERN = re.compile(
    r"\b(?:" + "|".join(sorted(_ROMAN_NUMERALS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Resource:
    dataset: str
    name: str
    url: str
    format: str
    year: int
    period: int
    last_modified: str | None = None


def _period_from_name(name: str) -> tuple[int, int]:
    """Read `(year, period)` from a resource title.

    Titles are shaped like `... - Agosto 2026`, `... - 2025 - IV` or
    `... - 2018 I`. A title without a period yields period 0.
    """
    year_match = _YEAR_PATTERN.search(name)
    year = int(year_match.group()) if year_match else 0

    month_match = _MONTH_PATTERN.search(name)
    if month_match:
        return year, _MONTHS[month_match.group().lower()]

    roman_match = _ROMAN_PATTERN.search(name)
    if roman_match:
        return year, _ROMAN_NUMERALS[roman_match.group().lower()]

    return year, 0


def list_resources(package: dict, *, dataset: str = "", format: str = "csv") -> list[Resource]:
    """List the published resources of a CKAN package for one format."""
    result = package.get("result") or package
    resources = []
    for entry in result.get("resources") or []:
        if str(entry.get("format") or "").lower() != format.lower():
            continue
        name = entry.get("name") or ""
        year, period = _period_from_name(name)
        resources.append(
            Resource(
                dataset=dataset,
                name=name,
                url=entry.get("url") or "",
                format=format,
                year=year,
                period=period,
                last_modified=entry.get("last_modified"),
            )
        )
    return resources


def pick_resource(
    resources: list[Resource],
    *,
    year: int | None = None,
    period: int | None = None,
) -> Resource:
    """Return the most recent resource matching the optional filters."""
    candidates = [
        resource
        for resource in resources
        if (year is None or resource.year == year) and (period is None or resource.period == period)
    ]
    if not candidates:
        raise NoResourcesError(
            f"no csv resource matches year={year} period={period} "
            f"among {len(resources)} published resources"
        )
    return max(candidates, key=lambda resource: (resource.year, resource.period))


def fetch_package(client: httpx.Client, dataset_id: str) -> dict:
    response = client.get(
        f"{CKAN_API_URL}/package_show",
        params={"id": dataset_id},
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise CkanError(f"CKAN package_show failed for dataset '{dataset_id}'")
    return payload


def resolve_resource(
    client: httpx.Client,
    dataset_key: str,
    *,
    year: int | None = None,
    period: int | None = None,
    include_alternatives: bool = True,
) -> Resource:
    """Resolve the current CSV resource of a catalogued dataset.

    Tries every identifier known for the source, because the catalogue entry can move: an
    identifier that worked yesterday can answer 404 today with the data still published under a
    different name. Only when none resolves does it give up, and then it says which names it
    tried.

    `include_alternatives=False` limits it to the current identifier, which is what the caller
    wants when it can fall back to a local copy: an older dataset is worse than the data already
    on disk. Measured, preferring the older dataset cut capacity coverage from 248 prospects to
    33 without saying anything.
    """
    candidates = list(DATASET_ALTERNATIVES.get(dataset_key) or (DATASETS[dataset_key],))
    if not include_alternatives:
        candidates = candidates[:1]
    errors: list[str] = []
    for dataset_id in candidates:
        try:
            package = fetch_package(client, dataset_id)
            resources = list_resources(package, dataset=dataset_key)
        except (httpx.HTTPError, CkanError) as error:
            errors.append(f"{dataset_id}: {type(error).__name__}")
            continue
        if not resources:
            errors.append(f"{dataset_id}: sin recursos csv")
            continue
        return pick_resource(resources, year=year, period=period)

    raise DatasetUnavailable(
        f"ningun identificador de '{dataset_key}' resolvio en el catalogo: " + "; ".join(errors)
    )
