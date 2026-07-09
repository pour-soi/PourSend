from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


NAME_COLUMNS = {"name", "full_name", "fullname", "contact", "contact_name"}
PHONE_COLUMNS = {"phone", "phone_number", "phonenumber", "mobile", "cell", "cell_phone"}
PHONE_AT_END_RE = re.compile(r"(?P<phone>\+?[\d(][\d\s().-]{6,})\s*$")


@dataclass(frozen=True)
class ParsedRecipient:
    name: str
    phone: str
    source: str = ""


@dataclass(frozen=True)
class RejectedRow:
    source: str
    reason: str


def parse_pasted_list(text: str) -> tuple[list[ParsedRecipient], list[RejectedRow]]:
    accepted: list[ParsedRecipient] = []
    rejected: list[RejectedRow] = []

    for line_number, line in enumerate((text or "").splitlines(), start=1):
        source = line.strip()
        if not source:
            continue

        parsed = _parse_line(source)
        if parsed is None:
            rejected.append(RejectedRow(source=f"Line {line_number}: {source}", reason="Could not detect name and phone number"))
        else:
            accepted.append(ParsedRecipient(parsed[0], parsed[1], source=f"Line {line_number}"))

    return accepted, rejected


def _parse_line(line: str) -> tuple[str, str] | None:
    for delimiter in [",", "\t", ";"]:
        if delimiter in line:
            row = next(csv.reader([line], delimiter=delimiter), [])
            cells = [cell.strip() for cell in row if cell.strip()]
            if len(cells) >= 2:
                return cells[0], cells[1]

    match = PHONE_AT_END_RE.search(line)
    if not match:
        return None

    phone = match.group("phone").strip()
    name = line[: match.start("phone")].strip()
    if not name:
        return None
    return name, phone


def detect_csv_columns(fieldnames: list[str] | None) -> tuple[str | None, str | None]:
    if not fieldnames:
        return None, None

    normalized = {_normalize_column(name): name for name in fieldnames}
    name_column = next((normalized[key] for key in NAME_COLUMNS if key in normalized), None)
    phone_column = next((normalized[key] for key in PHONE_COLUMNS if key in normalized), None)
    return name_column, phone_column


def read_csv_recipients(
    path: str | Path, name_column: str, phone_column: str
) -> tuple[list[ParsedRecipient], list[RejectedRow]]:
    accepted: list[ParsedRecipient] = []
    rejected: list[RejectedRow] = []

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            name = (row.get(name_column) or "").strip()
            phone = (row.get(phone_column) or "").strip()
            if not name or not phone:
                rejected.append(RejectedRow(source=f"CSV row {row_number}", reason="Missing name or phone number"))
                continue
            accepted.append(ParsedRecipient(name=name, phone=phone, source=f"CSV row {row_number}"))

    return accepted, rejected


def _normalize_column(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
