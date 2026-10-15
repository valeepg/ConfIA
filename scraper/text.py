"""Shared text matching for the ozone vocabulary.

The published sources and the clinics' web pages write the same terms in every
combination of case and accent, so matching happens on a folded copy. This module
is the single place that decides what "folded" means and which markers count as
ozone: if the two drifted apart, the Consulta G reader and the web enrichment
would disagree about the very same word.

It also owns `html_to_text`, because reducing a page to text is the step before
folding it and no other module should reinvent it.
"""

from __future__ import annotations

import html
import re
import unicodedata

# Vocabulary, not a regex: a procedure name or a web page matches when any of
# these appears in its folded form.
OZONE_MARKERS = ("ozono", "ozonoterapia")

_CODE_BLOCKS = re.compile(r"(?is)<(script|style|noscript|template|svg)[^>]*>.*?</\1>")
_ANY_TAG = re.compile(r"(?s)<[^>]+>")


def fold_text(value: object) -> str:
    """Lowercase and strip combining accents.

    Only accents are removed, never letters. `oxígeno` folds to `oxigeno`, which
    still has nothing to do with `ozono`. Keeping oxygen therapy and hyperbaric
    medicine apart from ozone therapy is a clinical distinction, not a cosmetic
    one: confusing them in a medical lead list is a real error.
    """
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def html_to_text(raw: str) -> str:
    """Reduce markup to readable text.

    Enough to look for a phone number or a word, and deliberately nothing more:
    this is not a readability engine and no claim of faithful rendering is made.
    Script and style bodies are dropped so their code cannot be mistaken for page
    copy, and entities are decoded so `&nbsp;` does not split a phone number.
    """
    without_code = _CODE_BLOCKS.sub(" ", raw or "")
    return html.unescape(_ANY_TAG.sub(" ", without_code))
