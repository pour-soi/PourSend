from __future__ import annotations

import re


ALLOWED_PHONE_CHARS_RE = re.compile(r"^[\d\s().+\-]+$")

PHONE_FORMAT_E164 = "e164"
PHONE_FORMAT_DIGITS = "digits"
PHONE_FORMAT_DASHES = "dashes"
PHONE_FORMAT_PARENS = "parens"
PHONE_FORMAT_SPACES = "spaces"

PHONE_FORMATS = [
    (PHONE_FORMAT_E164, "+14151234567"),
    (PHONE_FORMAT_DIGITS, "4151234567"),
    (PHONE_FORMAT_DASHES, "415-123-4567"),
    (PHONE_FORMAT_PARENS, "(415) 123-4567"),
    (PHONE_FORMAT_SPACES, "+1 415 123 4567"),
]


def normalize_us_phone(value: str) -> tuple[str, str]:
    """Return (normalized_number, status_message) for a US phone number."""
    raw = (value or "").strip()
    if not raw:
        return "", "Invalid: empty phone number"

    if not ALLOWED_PHONE_CHARS_RE.fullmatch(raw):
        return "", "Invalid: unsupported characters"

    if raw.count("+") > 1 or ("+" in raw and not raw.lstrip().startswith("+")):
        return "", "Invalid: misplaced plus sign"

    compact = re.sub(r"[\s().-]", "", raw)
    if compact.startswith("+"):
        digits = compact[1:]
        if not digits.isdigit():
            return "", "Invalid: malformed international number"
        if len(digits) == 11 and digits.startswith("1") and _valid_us_digits(digits[1:]):
            return "+" + digits, "Valid"
        return "", "Invalid: only US +1 numbers are supported"

    if not compact.isdigit():
        return "", "Invalid: malformed phone number"

    if len(compact) == 10 and _valid_us_digits(compact):
        return "+1" + compact, "Valid"

    if len(compact) == 11 and compact.startswith("1") and _valid_us_digits(compact[1:]):
        return "+" + compact, "Valid"

    return "", "Invalid: expected a 10-digit US number or 1 plus 10 digits"


def normalize_phone_format(format_key: str | None) -> str:
    valid_formats = {key for key, _label in PHONE_FORMATS}
    return format_key if format_key in valid_formats else PHONE_FORMAT_E164


def phone_search_digits(value: str) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def format_phone_number(value: str, format_key: str = PHONE_FORMAT_E164) -> str:
    normalized, status = normalize_us_phone(value)
    if status != "Valid":
        return str(value or "")

    digits = normalized[2:]
    area = digits[:3]
    exchange = digits[3:6]
    line = digits[6:]
    format_key = normalize_phone_format(format_key)

    if format_key == PHONE_FORMAT_DIGITS:
        return digits
    if format_key == PHONE_FORMAT_DASHES:
        return f"{area}-{exchange}-{line}"
    if format_key == PHONE_FORMAT_PARENS:
        return f"({area}) {exchange}-{line}"
    if format_key == PHONE_FORMAT_SPACES:
        return f"+1 {area} {exchange} {line}"
    return normalized


def _valid_us_digits(ten_digits: str) -> bool:
    if len(ten_digits) != 10 or not ten_digits.isdigit():
        return False
    return len(set(ten_digits)) > 1
