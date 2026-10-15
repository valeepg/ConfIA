"""Discovery: turn a target IPRESS into attributed ozone evidence.

Per clinic the pipeline is one search query, then fetch and read:

1. `search_clinic` asks the provider for `"<name>" <district>`.
2. `fetch_page` reads the top candidates with browser-like headers, respecting
   robots.txt.
3. `attribute` accepts a page only if it shows the published phone number or the
   published street.
4. `find_ozone_mentions` reads ozone mentions out of the accepted page.

The query shape is measured, not guessed. On 2026-10-13 the three shapes were
probed against real clinics:

| Query | Measured result |
|---|---|
| `"<full name>" <district>` | **The only productive one**: returned cefraperu.com first |
| the published phone | Unrelated businesses: for San Felipe it returned a Facebook page in Los Olivos, not the registry's Lurigancho address |
| `<short name> <district> ozonoterapia` | Generic ozone providers, never the clinic |

So the phone identifies a page once found, but it does not find the clinic; and
adding the ozone term to the query destroys precision. Quoting the full name does
the opposite.

Nothing here invents data. A clinic whose pages cannot be attributed stays
`unknown` (`checked=False`), and a page that was read and shows no ozone mention is
reported as read with no mention, which is not the same claim.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from urllib.robotparser import RobotFileParser

from .config import ENRICHMENT_DIR, USER_AGENT
from .contract import (
    TAG_ALREADY_OFFERS_OZONE,
    TAG_WEB_ENRICHED,
    OzoneTherapyOut,
    Prospect,
)
from .enrichment import Candidate, OzoneMention, attribute, find_ozone_mentions
from .renipress import Ipress
from .text import html_to_text

SERPER_ENDPOINT = "https://google.serper.dev/search"
RESULTS_PER_QUERY = 5
PAGES_TO_TRY = 3
MAX_PAGE_BYTES = 1_500_000
_ROBOTS_TIMEOUT_SECONDS = 10.0

# Hosts that cannot answer whether a clinic offers a treatment: a map pin or a
# directory entry is not the clinic's own voice, so the absence of a mention there
# proves nothing. A mention found there is still evidence and is kept.
#
# The directory entries were not guessed: they are the hosts the 50-clinic run
# actually attributed pages to (13 of 24 attributed pages were directories, and not
# one of the 24 mentioned ozone). The long tail of such sites is long, so this list
# is a floor, not a solution.
NON_CLINICAL_HOSTS = (
    "waze.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "pinterest.",
    "tripadvisor.",
    "foursquare.com",
    "google.com/maps",
    "maps.google",
    # Medidos en la corrida de 50 clinicas
    "cuidamisalud.com",
    "tumedico.pe",
    "establecimientosdesalud.info",
    "universidadperu.com",
    "deperu.com",
    "checksalud.com",
    "guiabbb.pe",
    "doctorperu.pe",
    "paginasamarillas",
    "openalfa.com",
    "peru-streets",
)

# A plain client gets HTTP 406 from Mod_Security on several clinic sites
# (measured on centromedicosanborja.com), while the same request with browser-like
# headers gets 200. We are reading a public page a visitor would read.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.5",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}


@dataclass(frozen=True)
class SearchOutcome:
    query: str
    candidates: tuple[Candidate, ...] = ()
    credits: int = 0


@dataclass(frozen=True)
class Page:
    url: str
    status: int = 0
    allowed: bool = True
    text: str = ""
    truncated: bool = False


@dataclass(frozen=True)
class EnrichmentOutcome:
    ipress_code: str
    checked: bool = False
    attribution: str | None = None
    source_url: str | None = None
    mentions: tuple[OzoneMention, ...] = ()
    query: str = ""
    credits: int = 0
    pages_fetched: int = 0
    note: str | None = None

    @property
    def performs(self) -> bool:
        return self.checked and bool(self.mentions)

    def to_json(self) -> str:
        return json.dumps(
            {
                "ipress_code": self.ipress_code,
                "checked": self.checked,
                "attribution": self.attribution,
                "source_url": self.source_url,
                "mentions": [{"text": m.text, "markers": list(m.markers)} for m in self.mentions],
                "query": self.query,
                "credits": self.credits,
                "pages_fetched": self.pages_fetched,
                "note": self.note,
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, raw: str) -> "EnrichmentOutcome":
        data = json.loads(raw)
        return cls(
            ipress_code=data["ipress_code"],
            checked=data["checked"],
            attribution=data["attribution"],
            source_url=data["source_url"],
            mentions=tuple(
                OzoneMention(text=m["text"], markers=tuple(m["markers"]))
                for m in data.get("mentions", [])
            ),
            query=data.get("query", ""),
            credits=data.get("credits", 0),
            pages_fetched=data.get("pages_fetched", 0),
            note=data.get("note"),
        )


def build_query(ipress: Ipress) -> str:
    """The measured query shape: quoted full name plus the district."""
    return f'"{ipress.name}" {ipress.district}'


def search_clinic(
    client: httpx.Client,
    ipress: Ipress,
    *,
    api_key: str,
    num: int = RESULTS_PER_QUERY,
) -> SearchOutcome:
    """One search query, mapped to candidates. The shape is the verified Serper one."""
    query = build_query(ipress)
    response = client.post(
        SERPER_ENDPOINT,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "gl": "pe", "hl": "es", "num": num},
    )
    response.raise_for_status()
    payload = response.json()

    candidates = tuple(
        Candidate(
            url=item["link"],
            text=" ".join(
                part for part in (item.get("title"), item.get("snippet")) if part
            ),
        )
        for item in payload.get("organic") or []
        if item.get("link")
    )
    return SearchOutcome(query=query, candidates=candidates, credits=int(payload.get("credits") or 0))


def _robots(client: httpx.Client, url: str, cache: dict[str, RobotFileParser]) -> RobotFileParser:
    """robots.txt per origin, cached. An unreadable file allows everything."""
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in cache:
        parser = RobotFileParser()
        parser.set_url(f"{origin}/robots.txt")
        try:
            response = client.get(
                parser.url, headers={"User-Agent": USER_AGENT}, timeout=_ROBOTS_TIMEOUT_SECONDS
            )
            parser.parse(response.text.splitlines() if response.status_code == 200 else [])
        except httpx.HTTPError:
            parser.parse([])
        cache[origin] = parser
    return cache[origin]


def fetch_page(
    client: httpx.Client,
    url: str,
    *,
    robots_cache: dict[str, RobotFileParser] | None = None,
) -> Page:
    """Read one page as a reader would, then reduce it to text."""
    robots_cache = {} if robots_cache is None else robots_cache
    if not _robots(client, url, robots_cache).can_fetch("*", url):
        return Page(url=url, allowed=False)

    with client.stream("GET", url, headers=BROWSER_HEADERS, follow_redirects=True) as response:
        if response.status_code != 200:
            return Page(url=url, status=response.status_code)

        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes(1 << 16):
            chunks.append(chunk)
            size += len(chunk)
            if size >= MAX_PAGE_BYTES:
                break
        body = b"".join(chunks)[:MAX_PAGE_BYTES]
        encoding = response.charset_encoding or "utf-8"

    return Page(
        url=url,
        status=200,
        text=html_to_text(body.decode(encoding, errors="replace")),
        truncated=size >= MAX_PAGE_BYTES,
    )


def enrich_ipress(
    client: httpx.Client,
    ipress: Ipress,
    *,
    api_key: str,
    enrichment_dir: Path | None = None,
    refresh: bool = False,
    pages_to_try: int = PAGES_TO_TRY,
) -> EnrichmentOutcome:
    """Resolve the ozone signal of one clinic from the open web.

    Results are cached per IPRESS so repeating a sample does not spend the same
    query twice. `credits` always reports what **this call** spent, so a cache hit
    reports zero and adding the outcomes of a run gives the real query cost.
    """
    cached = None
    if enrichment_dir is not None:
        cached = Path(enrichment_dir) / f"{ipress.ipress_code}.json"
        if cached.exists() and not refresh:
            previous = EnrichmentOutcome.from_json(cached.read_text(encoding="utf-8"))
            return replace(previous, note="cache", credits=0, pages_fetched=0)

    search = search_clinic(client, ipress, api_key=api_key)
    if not search.candidates:
        outcome = EnrichmentOutcome(
            ipress_code=ipress.ipress_code,
            query=search.query,
            credits=search.credits,
            note="no-candidates",
        )
    else:
        outcome = _read_candidates(client, ipress, search, pages_to_try=pages_to_try)

    if cached is not None:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(outcome.to_json(), encoding="utf-8")
    return outcome


def _is_third_party(url: str) -> bool:
    lowered = url.lower()
    return any(marker in lowered for marker in NON_CLINICAL_HOSTS)


def _read_candidates(
    client: httpx.Client,
    ipress: Ipress,
    search: SearchOutcome,
    *,
    pages_to_try: int,
) -> EnrichmentOutcome:
    robots_cache: dict[str, RobotFileParser] = {}
    pages_fetched = 0
    blocked_by_robots = False

    for candidate in search.candidates[:pages_to_try]:
        page = fetch_page(client, candidate.url, robots_cache=robots_cache)
        if not page.allowed:
            blocked_by_robots = True
            continue
        if page.status != 200 or not page.text:
            continue
        pages_fetched += 1

        # The page carries the phone; the search snippet carries the declared text.
        enriched = replace(candidate, text=f"{candidate.text} {page.text}")
        reason = attribute(enriched, ipress)
        if reason is None:
            continue

        mentions = find_ozone_mentions(page.text)
        if not mentions and _is_third_party(page.url):
            # A positive claim is evidence wherever it appears; the absence of one on
            # a map pin is not evidence of absence.
            return EnrichmentOutcome(
                ipress_code=ipress.ipress_code,
                checked=False,
                attribution=reason,
                source_url=page.url,
                query=search.query,
                credits=search.credits,
                pages_fetched=pages_fetched,
                note="third-party-host",
            )
        return EnrichmentOutcome(
            ipress_code=ipress.ipress_code,
            checked=True,
            attribution=reason,
            source_url=page.url,
            mentions=mentions,
            query=search.query,
            credits=search.credits,
            pages_fetched=pages_fetched,
        )

    note = "robots" if blocked_by_robots and not pages_fetched else "not-attributed"
    return EnrichmentOutcome(
        ipress_code=ipress.ipress_code,
        query=search.query,
        credits=search.credits,
        pages_fetched=pages_fetched,
        note=note,
    )


def apply_enrichment(prospect: Prospect, outcome: EnrichmentOutcome) -> Prospect:
    """Merge one web enrichment outcome into a prospect.

    An unattributed page adds nothing, so the clinic stays `unknown` and whatever
    the other sources said is preserved. A page on a map or directory host is that
    same case, which is why the reader already reports it unchecked.

    The claim keeps its source URL and the signal that attributed it, because
    somebody acting on "this clinic already offers ozone" has to be able to check it.
    """
    if outcome.ipress_code != prospect.ipress_code:
        raise ValueError(
            f"enrichment for {outcome.ipress_code} cannot be applied to {prospect.ipress_code}"
        )
    if not outcome.checked:
        return prospect

    tags = list(prospect.tags)
    if outcome.performs and TAG_ALREADY_OFFERS_OZONE not in tags:
        tags.append(TAG_ALREADY_OFFERS_OZONE)
    if TAG_WEB_ENRICHED not in tags:
        tags.append(TAG_WEB_ENRICHED)

    return prospect.model_copy(
        update={
            "ozone_therapy": OzoneTherapyOut(
                checked=True,
                performs=outcome.performs,
                total_attendances=0,  # the open web publishes no attendance counts
                evidence=[mention.text for mention in outcome.mentions],
                source_url=outcome.source_url,
                attribution=outcome.attribution,
            ),
            "tags": tags,
        }
    )
