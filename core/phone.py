from __future__ import annotations

import re


ALLOWED_PHONE_CHARS_RE = re.compile(r"^[\d\s().+\-]+$")


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


def _valid_us_digits(ten_digits: str) -> bool:
    if len(ten_digits) != 10 or not ten_digits.isdigit():
        return False
    return len(set(ten_digits)) > 1
