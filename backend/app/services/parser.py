"""
parser.py — Converts informal grocery order text into structured line items.

Design principles (carried from uploaded app, extended here):
  1. This module does one thing: text → [ParsedItem]. It has no I/O, no DB, no HTTP.
  2. It does not pretend to solve OCR or translation. Callers feed normalised text;
     OCR/transcription adapters live in ocr/ and are wired in ingestion.py.
  3. confidence reflects parse certainty so the UI can flag uncertain items
     without marking the whole order as needs_review.
  4. The filler-word list covers common Hinglish patterns observed in real kirana
     WhatsApp messages.
"""

import re
from dataclasses import dataclass


# ── Unit normalisation ────────────────────────────────────────────────────────

UNIT_ALIASES: dict[str, str] = {
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilogram": "kg",
    "g": "g", "gm": "g", "gram": "g", "grams": "g",
    "l": "l", "ltr": "l", "liter": "l", "litre": "l", "litres": "l", "liters": "l",
    "ml": "ml",
    "pkt": "pkt", "packet": "pkt", "pack": "pkt", "packets": "pkt",
    "dozen": "dozen", "dz": "dozen",
    "pcs": "pcs", "piece": "pcs", "pieces": "pcs", "nos": "pcs",
    "bottle": "bottle", "btl": "bottle",
    "box": "box", "tin": "tin", "can": "can",
}

# Filler words stripped from item names before storing
FILLER_WORDS: frozenset[str] = frozenset({
    "chahiye", "dena", "dedo", "bhej", "bhejna", "bhejdo", "bhejdena",
    "please", "plz", "pls", "aur", "aor", "or", "and",
    "bhaiya", "bhai", "didi", "ji", "sir", "madam",
    "ek", "do", "teen", "char", "paanch",       # number words when used as filler
    "wala", "wali", "wale", "ka", "ki", "ke",
    "lena", "lelo", "le", "de",
})

# Item-level confidence: 0.85 if quantity was explicit, 0.65 otherwise
HIGH_CONFIDENCE = 0.85
LOW_CONFIDENCE  = 0.65


@dataclass
class ParsedItem:
    name:       str
    quantity:   float
    unit:       str
    confidence: float


# ── Main parser ───────────────────────────────────────────────────────────────

_QTY_UNIT_NAME_RE = re.compile(
    r"^"
    r"(?:(?P<qty>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>kg|kgs|kilo|kilogram|g|gm|gram|grams|l|ltr|liter|litre|litres|liters|ml"
    r"|pkt|packet|pack|packets|dozen|dz|pcs|piece|pieces|nos|bottle|btl|box|tin|can)?\s+)?"
    r"(?P<name>.+?)$",
    re.IGNORECASE,
)


def parse_order_text(text: str | None) -> list[ParsedItem]:
    """
    Parse informal multilingual grocery-list text into structured line items.

    Handles:
      - Comma, semicolon, newline, and dash-separated lists
      - Leading quantity+unit ("2 kg atta", "1L oil")
      - Hinglish filler words ("bhaiya ek atta chahiye")
      - Mixed scripts in item names (passed through as-is; transliteration is
        the caller's responsibility if needed)

    Returns an empty list for None or empty input.
    """
    if not text or not text.strip():
        return []

    # Split on common separators; also split on patterns like " - " used in lists
    raw_parts = re.split(r"[,;\n\r।|]+|(?:\s+-\s+)", text)

    items: list[ParsedItem] = []
    seen: set[str] = set()

    for part in raw_parts:
        item = _parse_single(part.strip())
        if item is None:
            continue
        key = item.name.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(item)

    return items


def _parse_single(raw: str) -> ParsedItem | None:
    """Parse one candidate item string. Returns None if nothing useful found."""
    cleaned = raw.strip(" .:-–—\t").lower()
    if not cleaned:
        return None

    # Hard skip: entire string is a filler word or common non-order phrase
    if cleaned in FILLER_WORDS:
        return None
    if re.fullmatch(r"(order|list|items?|grocery|saman)", cleaned):
        return None

    match = _QTY_UNIT_NAME_RE.match(cleaned)
    if not match:
        return None

    qty_str  = match.group("qty")
    unit_raw = match.group("unit") or ""
    name_raw = match.group("name") or ""

    # Strip filler words from the name token
    name_tokens = [
        t for t in name_raw.split()
        if t not in FILLER_WORDS and len(t) > 1
    ]
    name = " ".join(name_tokens).strip(" .:-")

    if len(name) < 2:
        return None

    qty        = float(qty_str) if qty_str else 1.0
    unit       = UNIT_ALIASES.get(unit_raw.lower(), unit_raw.lower() or "pcs")
    confidence = HIGH_CONFIDENCE if qty_str else LOW_CONFIDENCE

    # Capitalise first letter for display
    name = name[0].upper() + name[1:]

    return ParsedItem(name=name, quantity=qty, unit=unit, confidence=confidence)
