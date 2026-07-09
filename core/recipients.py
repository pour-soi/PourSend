from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .phone import format_phone_number, normalize_us_phone


FORMAT_SEPARATORS = {
    "comma": ",",
    "semicolon": ";",
    "newline": "\n",
}


@dataclass(frozen=True)
class CopyResult:
    selected: int
    copied: int
    duplicates_removed: int
    invalid_skipped: int
    output: str


def build_clipboard_output(
    recipients: Iterable[dict], output_format: str = "comma", phone_format: str = "e164"
) -> CopyResult:
    separator = FORMAT_SEPARATORS.get(output_format, ",")
    selected = 0
    invalid = 0
    duplicates = 0
    seen: set[str] = set()
    numbers: list[str] = []

    for recipient in recipients:
        if not recipient.get("selected"):
            continue
        selected += 1
        normalized, status = normalize_us_phone(str(recipient.get("phone", "")))
        if status != "Valid":
            invalid += 1
            continue
        if normalized in seen:
            duplicates += 1
            continue
        seen.add(normalized)
        numbers.append(format_phone_number(normalized, phone_format))

    return CopyResult(
        selected=selected,
        copied=len(numbers),
        duplicates_removed=duplicates,
        invalid_skipped=invalid,
        output=separator.join(numbers),
    )
