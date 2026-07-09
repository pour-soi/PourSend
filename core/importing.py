from __future__ import annotations

import csv
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from .groups import DEFAULT_GROUP
from .phone import normalize_us_phone


NAME_COLUMNS = {"name", "full_name", "fullname", "contact", "contact_name"}
PHONE_COLUMNS = {"phone", "phone_number", "phonenumber", "mobile", "cell", "cell_phone"}
PHONE_AT_END_RE = re.compile(r"(?P<phone>\+?[\d(][\d\s().-]{6,})\s*$")
PHONE_CHARS_RE = re.compile(r"^[\d\s().+\-]+$")
PHONE_EXTRACT_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]*)?(?:\(\d{3}\)|\d{3})[\s.-]*\d{3}[\s.-]*\d{4}(?!\d)"
)


@dataclass(frozen=True)
class ParsedRecipient:
    name: str
    phone: str
    source: str = ""


@dataclass(frozen=True)
class RejectedRow:
    source: str
    reason: str


@dataclass(frozen=True)
class PastePreviewRow:
    name: str
    phone: str
    normalized: str
    status: str
    source: str = ""


def parse_pasted_list(text: str) -> tuple[list[ParsedRecipient], list[RejectedRow]]:
    accepted: list[ParsedRecipient] = []
    rejected: list[RejectedRow] = []

    for line_number, line in enumerate((text or "").splitlines(), start=1):
        source = line.strip()
        if not source:
            continue

        parsed = _parse_line(source)
        if parsed is None:
            rejected.append(RejectedRow(source=f"Line {line_number}: {source}", reason="Could not detect phone number"))
        else:
            accepted.append(ParsedRecipient(parsed[0], parsed[1], source=f"Line {line_number}"))

    return accepted, rejected


def preview_pasted_recipients(text: str, existing_numbers: set[str] | None = None) -> list[PastePreviewRow]:
    existing = existing_numbers or set()
    seen: set[str] = set()
    rows: list[PastePreviewRow] = []

    for line_number, line in enumerate((text or "").splitlines(), start=1):
        source = line.strip()
        if not source:
            continue
        for name, phone in _parse_preview_line(source):
            normalized, phone_status = normalize_us_phone(phone)
            if phone_status != "Valid":
                status = "Invalid"
            elif normalized in seen:
                status = "Duplicate in this batch"
            elif normalized in existing:
                status = "Already exists"
            else:
                status = "Valid"
                seen.add(normalized)
            rows.append(
                PastePreviewRow(
                    name=name or "None",
                    phone=phone,
                    normalized=normalized,
                    status=status,
                    source=f"Line {line_number}",
                )
            )

    return rows


def rows_to_add(rows: list[PastePreviewRow], group: str = DEFAULT_GROUP) -> list[dict]:
    clean_group = group.strip() or DEFAULT_GROUP
    return [
        {
            "phone": row.normalized,
            "selected": False,
            "group": clean_group,
            "groups": [clean_group],
            "notes": "",
        }
        for row in rows
        if row.status == "Valid"
    ]


def normalized_numbers_from_text(text: str) -> list[str]:
    return [
        row.normalized
        for row in preview_pasted_recipients(text)
        if row.normalized and row.status in {"Valid", "Duplicate in this batch"}
    ]


def preview_import_file(path: str | Path, existing_numbers: set[str] | None = None) -> list[PastePreviewRow]:
    source = Path(path)
    suffix = source.suffix.lower()
    try:
        if suffix == ".txt":
            text = source.read_text(encoding="utf-8-sig")
        elif suffix == ".csv":
            text = _csv_to_text(source)
        elif suffix == ".xlsx":
            text = _xlsx_to_text(source)
        else:
            raise ValueError("Unsupported import file type")
    except (csv.Error, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise ValueError(f"Could not read {suffix or 'file'} content") from exc
    return preview_pasted_recipients(text, existing_numbers)


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
    return name, phone


def _parse_preview_line(line: str) -> list[tuple[str, str]]:
    extracted = _extract_phone_candidates(line)
    if len(extracted) > 1:
        return [("", phone) for _name, phone in extracted]
    if len(extracted) == 1:
        name, phone = extracted[0]
        return [(name, phone)]

    delimited = _split_delimited(line)
    if len(delimited) > 1:
        phone_like = [cell for cell in delimited if _looks_like_phone(cell)]
        if not phone_like:
            return []
        if len(delimited) == 2 and len(phone_like) == 1 and not _looks_like_phone(delimited[0]):
            return [(delimited[0], delimited[1])]
        return [("", cell) for cell in phone_like]

    if _looks_like_phone(line):
        return [("", line)]

    parsed = _parse_line(line)
    if parsed is not None:
        return [parsed]

    return []


def _extract_phone_candidates(line: str) -> list[tuple[str, str]]:
    matches = list(PHONE_EXTRACT_RE.finditer(line))
    if not matches:
        return []
    if len(matches) == 1:
        match = matches[0]
        name = line[: match.start()].strip(" ,;:-\t")
        return [(name, match.group().strip())]
    return [("", match.group().strip()) for match in matches]


def _csv_to_text(path: Path) -> str:
    lines: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            cells = [cell.strip() for cell in row if cell.strip()]
            if cells:
                lines.append("\t".join(cells))
    return "\n".join(lines)


def _xlsx_to_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _read_xlsx_shared_strings(archive)
        worksheet_names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("xl/worksheets/") and name.endswith(".xml")
        )
        lines: list[str] = []
        for worksheet_name in worksheet_names:
            root = ElementTree.fromstring(archive.read(worksheet_name))
            for row in root.findall(".//{*}sheetData/{*}row"):
                cells = [_xlsx_cell_text(cell, shared_strings) for cell in row.findall("{*}c")]
                cleaned = [cell for cell in cells if cell]
                if cleaned:
                    lines.append("\t".join(cleaned))
    return "\n".join(lines)


def _read_xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("{*}si"):
        strings.append("".join(text.text or "" for text in item.findall(".//{*}t")))
    return strings


def _xlsx_cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//{*}t")).strip()

    value = cell.find("{*}v")
    if value is None or value.text is None:
        return ""

    text = value.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(text)].strip()
        except (ValueError, IndexError):
            return ""
    return text


def _split_delimited(line: str) -> list[str]:
    if "\t" in line:
        return [cell.strip() for cell in line.split("\t") if cell.strip()]
    if ";" in line:
        return [cell.strip() for cell in line.split(";") if cell.strip()]
    if "," in line:
        row = next(csv.reader([line]), [])
        return [cell.strip() for cell in row if cell.strip()]
    return [line.strip()]


def _looks_like_phone(value: str) -> bool:
    text = value.strip()
    if not text or not PHONE_CHARS_RE.fullmatch(text):
        return False
    digit_count = sum(char.isdigit() for char in text)
    return digit_count >= 3


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
            if not phone:
                rejected.append(RejectedRow(source=f"CSV row {row_number}", reason="Missing phone number"))
                continue
            accepted.append(ParsedRecipient(name=name, phone=phone, source=f"CSV row {row_number}"))

    return accepted, rejected


def _normalize_column(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
