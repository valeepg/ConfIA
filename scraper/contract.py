"""The `prospect_mock.json` contract shared with the other hackathon modules.

It is the boundary with the database module (RF-09) and the Kanban (RF-03):
`pipeline_stage` mirrors the CRM columns, so the dashboard can render the
scraper output without a translation layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from .capacity import IpressCapacity
from .procedures import OzoneTherapy
from .renipress import Ipress
from .scoring import TOTAL_WEIGHT, Score, is_valid_phone

CONTRACT_VERSION = "prospect_mock/v0"

PipelineStage = Literal["discovered", "contacted", "proposal_sent", "contract_signed"]
PIPELINE_STAGES: tuple[str, ...] = (
    "discovered",
    "contacted",
    "proposal_sent",
    "contract_signed",
)

TAG_TARGET_PROFILE = "target-profile"
TAG_ALREADY_OFFERS_OZONE = "already-offers-ozone-therapy"
TAG_NO_CAPACITY_DATA = "no-capacity-data"
TAG_PRIORITY_HIGH = "priority-high"
TAG_WEB_ENRICHED = "web-enriched"


class Coordinates(BaseModel):
    """Latitude and longitude, the pair that maps onto a Firestore GeoPoint.

    RENIPRESS publishes them in columns named NORTE and ESTE, but the values are latitude
    and longitude; see `scraper/renipress.py` for the measurement.
    """

    latitude: float
    longitude: float


class Location(BaseModel):
    department: str
    # Null when the source is a search result, which knows the district but not the province.
    province: str | None = None
    district: str
    # Null when the source is a search result rather than the registry.
    ubigeo: str | None = None
    # Null when the registry publishes nothing, which is 15 % of the target profile.
    coordinates: Coordinates | None = None


class Contact(BaseModel):
    phone: str = ""
    phone_valid: bool = False
    address: str = ""
    schedule: str = ""


class Capacity(BaseModel):
    doctors_total: int = 0
    consulting_rooms: int = 0
    functional_consulting_rooms: int = 0
    beds: int = 0
    nurses: int = 0
    ambulances: int = 0
    # Null means the source has no record, which is not the same as zero doctors.
    period: str | None = None


class OzoneTherapyOut(BaseModel):
    checked: bool = False
    performs: bool = False
    total_attendances: int = 0
    # Supporting strings, whatever produced them: procedure names from Consulta G,
    # citing sentences from a web page.
    evidence: list[str] = Field(default_factory=list)
    # Where a web claim came from, so it can be audited instead of trusted.
    source_url: str | None = None
    attribution: str | None = None


class ScoreBreakdown(BaseModel):
    total: int
    level: Literal["high", "medium", "low"]
    components: dict[str, int]
    # 100 = scored over full evidence; 70 = capacity unknown and its weight redistributed.
    measured_weight: int = TOTAL_WEIGHT


class GooglePlace(BaseModel):
    """What the search source knows and the registry cannot say.

    The registry files establishments, not specialties, so for the focused segment this
    block carries the signal: what kind of place Google says it is, how much patient
    activity the reviews suggest, and whether it belongs to a brand with several sites.
    """

    cid: str
    query: str
    category: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    rating_band: str | None = None
    reviews_band: str | None = None
    website: str | None = None
    position: int | None = None
    chain_brand: str | None = None
    chain_sites: int = 1


class Prospect(BaseModel):
    id: str
    # Where the record came from. The registry and the search source answer different
    # questions, so mixing them without saying which is which would be dishonest.
    origin: Literal["renipress", "places"] = "renipress"
    ipress_code: str | None = None
    name: str
    legal_name: str | None = None
    # Registry fields: null for a place that the registry does not file under this profile.
    institution: str | None = None
    category: str | None = None
    classification: str | None = None
    establishment_type: str | None = None
    location: Location
    # A search result has no registry capacity and no ozone reading, so these default to
    # empty instead of forcing every caller to spell out what it does not know.
    contact: Contact = Field(default_factory=Contact)
    capacity: Capacity = Field(default_factory=Capacity)
    ozone_therapy: OzoneTherapyOut = Field(default_factory=OzoneTherapyOut)
    # The registry score does not apply to a search result, so it stays null there.
    score: ScoreBreakdown | None = None
    google: GooglePlace | None = None
    pipeline_stage: PipelineStage = "discovered"
    tags: list[str] = Field(default_factory=list)


class Source(BaseModel):
    dataset: str
    url: str
    # A file source is identified by the hash of its bytes; an API source by the questions
    # that were asked, because that is what makes the result reproducible.
    sha256: str | None = None
    last_modified: str | None = None
    queries: list[str] = Field(default_factory=list)


class ProspectArchive(BaseModel):
    contract_version: str = CONTRACT_VERSION
    generated_at: str
    sources: list[Source] = Field(default_factory=list)
    total: int = 0
    prospects: list[Prospect] = Field(default_factory=list)


def _tags(capacity: IpressCapacity, ozone: OzoneTherapy, score: Score) -> list[str]:
    tags = [TAG_TARGET_PROFILE]
    if ozone.performs:
        tags.append(TAG_ALREADY_OFFERS_OZONE)
    if capacity.period is None:
        tags.append(TAG_NO_CAPACITY_DATA)
    if score.level == "high":
        tags.append(TAG_PRIORITY_HIGH)
    return tags


def build_prospect(
    ipress: Ipress,
    *,
    capacity: IpressCapacity,
    ozone_therapy: OzoneTherapy,
    score: Score,
) -> Prospect:
    return Prospect(
        # The IPRESS code is the deduplication key used across all three sources.
        id=ipress.ipress_code,
        ipress_code=ipress.ipress_code,
        name=ipress.name,
        legal_name=capacity.legal_name,
        institution=ipress.institution,
        category=ipress.category,
        classification=ipress.classification,
        establishment_type=ipress.establishment_type,
        location=Location(
            department=ipress.department,
            province=ipress.province,
            district=ipress.district,
            ubigeo=ipress.ubigeo,
            coordinates=(
                Coordinates(latitude=ipress.latitude, longitude=ipress.longitude)
                if ipress.latitude is not None and ipress.longitude is not None
                else None
            ),
        ),
        contact=Contact(
            phone=ipress.phone,
            phone_valid=is_valid_phone(ipress.phone),
            address=ipress.address,
            schedule=ipress.schedule,
        ),
        capacity=Capacity(
            doctors_total=capacity.doctors_total,
            consulting_rooms=capacity.consulting_rooms,
            functional_consulting_rooms=capacity.functional_consulting_rooms,
            beds=capacity.beds,
            nurses=capacity.nurses,
            ambulances=capacity.ambulances,
            period=capacity.period,
        ),
        ozone_therapy=OzoneTherapyOut(
            checked=ozone_therapy.checked,
            performs=ozone_therapy.performs,
            total_attendances=ozone_therapy.total_attendances,
            evidence=list(ozone_therapy.procedures),
        ),
        score=ScoreBreakdown(
            total=score.total,
            level=score.level,
            components=dict(score.components),
            measured_weight=score.measured_weight,
        ),
        tags=_tags(capacity, ozone_therapy, score),
    )


def _sort_key(prospect: Prospect) -> tuple[int, int, str]:
    """Scored prospects first, by score; the rest after them, in a stable order."""
    if prospect.score is None:
        return (1, 0, prospect.id)
    return (0, -prospect.score.total, prospect.id)


def build_archive(
    prospects: list[Prospect],
    *,
    sources: list[Source],
    generated_at: str | None = None,
) -> ProspectArchive:
    """Order prospects for stable diffs: scored by score, the rest by identifier."""
    ordered = sorted(prospects, key=_sort_key)
    return ProspectArchive(
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
        sources=sources,
        total=len(ordered),
        prospects=ordered,
    )
