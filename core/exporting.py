from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from html import escape

from app.storage import make_saved_data, parse_saved_data, parse_saved_settings, repair_saved_group_names
from core.groups import ALL_RECIPIENTS, checked_recipient_indexes, filtered_recipient_indexes, valid_recipient_groups
from core.phone import PHONE_FORMAT_E164, format_phone_number, normalize_us_phone


SCOPE_ALL = "all"
SCOPE_GROUP = "group"
SCOPE_SEARCH = "search"
SCOPE_SELECTION = "selection"

COPY_DISPLAYED = "displayed"
COPY_DIGITS = "digits"
COPY_E164 = "e164"

BACKUP_VERSION = 1
BACKUP_APP = "PourSend"


@dataclass(frozen=True)
class ExportSelection:
    recipients: list[dict]
    empty_reason: str = ""


def resolve_recipient_scope(
    recipients: list[dict],
    scope: str,
    *,
    group_filter: str = ALL_RECIPIENTS,
    query: str = "",
    phone_format: str = PHONE_FORMAT_E164,
    sort_field: str = "recent",
    descending: bool = False,
) -> ExportSelection:
    visible_indexes = filtered_recipient_indexes(
        recipients, group_filter, query, phone_format, sort_field, descending
    )
    if scope == SCOPE_ALL:
        indexes = filtered_recipient_indexes(recipients, ALL_RECIPIENTS, "", phone_format, sort_field, descending)
    elif scope == SCOPE_GROUP:
        indexes = filtered_recipient_indexes(recipients, group_filter, "", phone_format, sort_field, descending)
    elif scope == SCOPE_SEARCH:
        indexes = visible_indexes
    elif scope == SCOPE_SELECTION:
        indexes = checked_recipient_indexes(recipients)
    else:
        indexes = []

    if not indexes:
        if scope == SCOPE_SELECTION:
            return ExportSelection([], "No recipients are checked. Select one or more recipients in the Select column, then try again.")
        return ExportSelection([], "No recipients match that scope.")
    return ExportSelection(_dedupe_recipients([recipients[index] for index in indexes]))


def _dedupe_recipients(recipients: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for recipient in recipients:
        normalized, status = normalize_us_phone(str(recipient.get("phone", "")))
        key = normalized if status == "Valid" else str(recipient.get("phone", "")).strip()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(recipient)
    return deduped


def format_copy_number(phone: str, copy_mode: str, display_format: str) -> str:
    normalized, status = normalize_us_phone(phone)
    if status != "Valid":
        return ""
    if copy_mode == COPY_DIGITS:
        return normalized.lstrip("+")
    if copy_mode == COPY_E164:
        return normalized
    return format_phone_number(normalized, display_format)


def build_number_lines(recipients: list[dict], copy_mode: str, display_format: str) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for recipient in recipients:
        normalized, status = normalize_us_phone(str(recipient.get("phone", "")))
        if status != "Valid" or normalized in seen:
            continue
        seen.add(normalized)
        value = format_copy_number(normalized, copy_mode, display_format)
        if value:
            lines.append(value)
    return lines


def build_copy_text(recipients: list[dict], copy_mode: str, display_format: str) -> str:
    return "\n".join(build_number_lines(recipients, copy_mode, display_format))


def export_txt(recipients: list[dict], display_format: str) -> str:
    return "\n".join(build_number_lines(recipients, COPY_DISPLAYED, display_format))


def export_csv(recipients: list[dict], display_format: str) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Phone Number", "Group", "Notes"])
    for recipient in recipients:
        writer.writerow([
            format_phone_number(str(recipient.get("phone", "")), display_format),
            "; ".join(valid_recipient_groups(recipient)),
            str(recipient.get("notes", "")),
        ])
    return output.getvalue()


def export_xlsx_bytes(recipients: list[dict], display_format: str) -> bytes:
    rows = [["Phone Number", "Group", "Notes"]]
    rows.extend(
        [
            format_phone_number(str(recipient.get("phone", "")), display_format),
            "; ".join(valid_recipient_groups(recipient)),
            str(recipient.get("notes", "")),
        ]
        for recipient in recipients
    )

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _RELS)
        archive.writestr("xl/workbook.xml", _WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def make_backup(recipients: list[dict], groups: list[str], settings: dict | None = None) -> dict:
    return {
        "backup_version": BACKUP_VERSION,
        "app": BACKUP_APP,
        "data": make_saved_data(recipients, groups, settings),
    }


def backup_json(recipients: list[dict], groups: list[str], settings: dict | None = None) -> str:
    return json.dumps(make_backup(recipients, groups, settings), indent=2)


def parse_backup_json(text: str) -> tuple[list[dict], list[str], dict, int]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if isinstance(parsed, dict) and parsed.get("backup_version") == BACKUP_VERSION and isinstance(parsed.get("data"), dict):
        data = parsed["data"]
        version = parsed["backup_version"]
    elif isinstance(parsed, dict) and "recipients" in parsed and "groups" in parsed:
        data = parsed
        version = 0
    else:
        raise ValueError("Unsupported backup structure")

    data, warnings = repair_saved_group_names(data)
    recipients, groups = parse_saved_data(data)
    if not isinstance(recipients, list) or not isinstance(groups, list):
        raise ValueError("Unsupported backup data")
    for recipient in recipients:
        _normalized, status = normalize_us_phone(str(recipient.get("phone", "")))
        if status != "Valid":
            raise ValueError("Backup contains invalid recipient phone data")
    settings = parse_saved_settings(data)
    if warnings:
        settings["migration_warnings"] = warnings
    return recipients, groups, settings, version


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Recipients" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
