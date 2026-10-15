"""Attribution of ozone evidence found on the web to the right IPRESS.

Consulta G cannot answer whether a clinic already offers ozone therapy: its
catalogue of 7,457 procedures has no ozone entry. So the answer has to come from
the clinic's web presence, and the 3-clinic validation sample produced **0
reliable answers**. All three failures were attribution failures, not detection
failures:

- CENTRO MEDICO ESPECIALIZADO SAN FELIPE exists in both Chosica and Huancayo;
- CEFRA is in San Borja, and so is an unrelated clinic that does offer ozone;
- oxygen therapy and a hyperbaric chamber sit one search away from ozone therapy.

This module therefore does the two things that turned out to be hard, and only
those:

1. `find_ozone_mentions` reads ozone mentions out of a page and keeps the citing
   sentence, so a human can audit the claim instead of trusting a boolean.
2. `resolve_ozone_evidence` attributes a page to an IPRESS through its published
   phone number or a comparable street address, and reports `checked=False` when it
   cannot. The phone is the stronger of the two: a street is shared by the whole
   district, and RENIPRESS publishes a phone for 2,457 of the 2,459 targets.

`checked=False` is not a negative. It mirrors `signal_available` in the Consulta G
reader: an unattributed page leaves the clinic `unknown`, and the pipeline must
never turn that into "does not offer ozone therapy".

Deciding which URL to visit in the first place needs a search provider and an API
key, and is deliberately not implemented here (see `docs/modulo-1-scraper.md`
§2.4). Nothing in this module touches the network, so it is testable offline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

from .renipress import Ipress
from .text import OZONE_MARKERS, fold_text

_MAX_MENTION_LENGTH = 300
_DEFAULT_MAX_MENTIONS = 5

# Two shared street-name tokens. A street number and the name of the town every
# clinic there shares do not identify anything.
_MINIMUM_SHARED_STREET_TOKENS = 2
_MINIMUM_TOKEN_LENGTH = 3

# Road types and address filler that carry no identifying signal.
_NOISE_TOKENS = frozenset(
    {
        "av",
        "avenida",
        "jr",
        "jiron",
        "calle",
        "ca",
        "urb",
        "urbanizacion",
        "mz",
        "lt",
        "lote",
        "nro",
        "num",
        "numero",
        "int",
        "dpto",
        "piso",
        "block",
        "etapa",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "y",
    }
)

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?\n])")
_ADDRESS_SEPARATORS = ".,;:-/()#º°"

# A phone number identifies one clinic; a street name is shared by the whole
# district. Runs shorter than this are street numbers or years, not switchboards.
_MINIMUM_PHONE_DIGITS = 7
_MAXIMUM_PHONE_DIGITS = 9
_COUNTRY_CODE = "51"
_COUNTRY_CODE_DIGITS = len(_COUNTRY_CODE)
# Digits joined only by separators, so a phone stops at the first letter: on
# `999 888 777 Av. Guardia Civil 715` splitting by groups used to merge the phone
# with the street number and lose a real match.
_PHONE_CANDIDATE = re.compile(r"\d(?:[\s.\-()/]*\d){6,}")


@dataclass(frozen=True)
class OzoneMention:
    """One sentence of a page that mentions ozone, with the markers it matched."""

    text: str
    markers: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    """A page proposed for one IPRESS by the discovery step.

    `address`, `district` and `department` are whatever the result declares about
    itself. Empty fields mean "not declared", which cannot attribute the page.
    """

    url: str
    text: str = ""
    address: str = ""
    district: str = ""
    department: str = ""


@dataclass(frozen=True)
class OzoneEvidence:
    source_url: str
    checked: bool
    mentions: tuple[OzoneMention, ...] = ()

    @property
    def performs(self) -> bool:
        """Only a page we could attribute and that mentions ozone counts as a yes."""
        return self.checked and bool(self.mentions)


def address_tokens(address: str) -> frozenset[str]:
    """Meaningful tokens of a street address, ignoring road types and filler."""
    folded = fold_text(address)
    for separator in _ADDRESS_SEPARATORS:
        folded = folded.replace(separator, " ")
    return frozenset(
        token
        for token in folded.split()
        if len(token) >= _MINIMUM_TOKEN_LENGTH and token not in _NOISE_TOKENS
    )


def _national_phone(digits: str) -> str:
    if len(digits) > _MAXIMUM_PHONE_DIGITS and digits.startswith(_COUNTRY_CODE):
        return digits[_COUNTRY_CODE_DIGITS:]
    return digits


def phone_numbers(value: object) -> frozenset[str]:
    """Phone numbers in the national format, found in a field or in a page.

    RENIPRESS publishes some switchboards as `3515111; 3515116` and pages write
    `+51 999 888 777`, so the `+51` prefix is dropped and every run is normalised the
    same way. Runs that come out longer than a national number are street numbers,
    years or unrelated digit soup, and are ignored instead of guessed at.
    """
    numbers: set[str] = set()
    for candidate in _PHONE_CANDIDATE.findall(str(value or "")):
        national = _national_phone(re.sub(r"\D", "", candidate))
        if _MINIMUM_PHONE_DIGITS <= len(national) <= _MAXIMUM_PHONE_DIGITS:
            numbers.add(national)
    return frozenset(numbers)


def _sentences(text: str) -> Iterator[str]:
    for chunk in _SENTENCE_BOUNDARY.split(text or ""):
        cleaned = " ".join(chunk.split())
        if cleaned:
            yield cleaned


def find_ozone_mentions(text: str, *, limit: int = _DEFAULT_MAX_MENTIONS) -> tuple[OzoneMention, ...]:
    """Return the sentences of `text` that mention ozone."""
    mentions: list[OzoneMention] = []
    for sentence in _sentences(text):
        folded = fold_text(sentence)
        markers = tuple(marker for marker in OZONE_MARKERS if marker in folded)
        if markers:
            mentions.append(
                OzoneMention(text=sentence[:_MAX_MENTION_LENGTH], markers=markers)
            )
        if len(mentions) >= limit:
            break
    return tuple(mentions)


def attribute(candidate: Candidate, ipress: Ipress) -> str | None:
    """Return *why* a page belongs to this IPRESS, or `None` when it cannot be attributed.

    The reason is part of the evidence: a phone match and a street match are not
    equally strong, and the enrichment records which one it used. A matching
    district is not enough either, because the sampled false positive was a
    different clinic in the very same district; the whole neighbourhood shares it.

    Known residual risk: a directory page that lists many clinics' phones, or two
    clinics on the same street name in different districts when the result declares
    neither district nor department. Neither is attributable, so the failure mode
    stays `unknown`.
    """
    declared_department = fold_text(candidate.department)
    if declared_department and declared_department != fold_text(ipress.department):
        return None

    declared_district = fold_text(candidate.district)
    if declared_district and declared_district != fold_text(ipress.district):
        return None

    if phone_numbers(candidate.text) & phone_numbers(ipress.phone):
        return "phone"

    published = address_tokens(ipress.address)
    shared = published & address_tokens(candidate.address)
    if _is_identifying(shared):
        return "address"

    # A fetched page declares no address field, so the published street is looked
    # for inside its text as well.
    folded = fold_text(candidate.text)
    present = {token for token in published if token in folded}
    if _is_identifying(present):
        return "address"

    return None


def _is_identifying(tokens: set[str]) -> bool:
    """Two shared alphabetic tokens, meaning the street name itself.

    Numbers and locality names do not identify a clinic. Measured: the Waze listing
    of San Felipe matched on `182` (its street number) and `chosica` (the town every
    clinic there shares), while a real match shares the street name, as CEFRA's
    `guardia civil` does.
    """
    return sum(1 for token in tokens if token.isalpha()) >= _MINIMUM_SHARED_STREET_TOKENS


def clinic_owns_result(candidate: Candidate, ipress: Ipress) -> bool:
    return attribute(candidate, ipress) is not None


def resolve_ozone_evidence(candidate: Candidate, ipress: Ipress) -> OzoneEvidence:
    """Decide the ozone signal for one candidate page: yes, no, or unknown."""
    if not clinic_owns_result(candidate, ipress):
        return OzoneEvidence(source_url=candidate.url, checked=False)
    return OzoneEvidence(
        source_url=candidate.url,
        checked=True,
        mentions=find_ozone_mentions(candidate.text),
    )
