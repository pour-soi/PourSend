from __future__ import annotations

import json
import sys
from pathlib import Path

from core.groups import (
    collect_groups,
    ensure_default_group,
    normalize_group_colors,
    normalize_group_names,
    normalize_recipients,
    recipient_phone_key,
)
from core.phone import PHONE_FORMAT_E164, format_phone_number, normalize_phone_format


APP_FOLDER = "poursend_data"
DATA_FILE = "recipients.json"


def default_settings() -> dict:
    return {"phone_format": PHONE_FORMAT_E164}


def normalize_group_selections(value) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    selections: dict[str, list[str]] = {}
    for raw_group, raw_phones in value.items():
        group = str(raw_group).strip()
        if not group or not isinstance(raw_phones, list):
            continue
        phones: list[str] = []
        for raw_phone in raw_phones:
            if not isinstance(raw_phone, str):
                continue
            key = recipient_phone_key({"phone": raw_phone})
            if key and key not in phones:
                phones.append(key)
        if phones:
            selections[group] = phones
    return selections


def data_path() -> Path:
    if getattr(sys, "frozen", False):
        portable_dir = Path(sys.executable).resolve().parent
    else:
        portable_dir = Path(__file__).resolve().parents[1]
    data_dir = portable_dir / APP_FOLDER
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return data_dir / DATA_FILE
    except OSError:
        fallback = Path.home() / f".{APP_FOLDER}"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback / DATA_FILE


def parse_saved_data(data) -> tuple[list[dict], list[str]]:
    if isinstance(data, list):
        groups = collect_groups(data)
        recipients = normalize_recipients(data, groups)
        return recipients, collect_groups(recipients)

    if isinstance(data, dict):
        raw_recipients = data.get("recipients", [])
        saved_groups = normalize_group_names(data.get("groups", []))
        group_source = (
            [*saved_groups, *_collect_saved_membership_groups(raw_recipients)]
            if saved_groups
            else collect_groups(raw_recipients)
        )
        groups = ensure_default_group(group_source)
        recipients = normalize_recipients(raw_recipients, groups)
        return recipients, collect_groups(recipients, groups)

    raise ValueError("unexpected format")


def _collect_saved_membership_groups(recipients) -> list[str]:
    names: list[str] = []
    if not isinstance(recipients, list):
        return names
    for recipient in recipients:
        if not isinstance(recipient, dict):
            continue
        groups = recipient.get("groups", [])
        if isinstance(groups, str):
            names.append(groups)
        elif isinstance(groups, list):
            names.extend(str(group) for group in groups)
    return normalize_group_names(names)


def parse_saved_settings(data) -> dict:
    settings = default_settings()
    if isinstance(data, dict) and isinstance(data.get("settings"), dict):
        raw_settings = data["settings"]
        settings["phone_format"] = normalize_phone_format(raw_settings.get("phone_format"))
        window_geometry = raw_settings.get("window_geometry")
        if isinstance(window_geometry, dict):
            settings["window_geometry"] = window_geometry
        group_selections = normalize_group_selections(raw_settings.get("group_selections"))
        if group_selections:
            settings["group_selections"] = group_selections
        group_colors = normalize_group_colors(raw_settings.get("group_colors"))
        if group_colors:
            settings["group_colors"] = group_colors
    return settings


def make_saved_data(recipients: list[dict], groups: list[str], settings: dict | None = None) -> dict:
    groups = ensure_default_group(groups)
    normalized_recipients = normalize_recipients(recipients, groups)
    saved_settings = default_settings()
    if settings:
        saved_settings["phone_format"] = normalize_phone_format(settings.get("phone_format"))
        window_geometry = settings.get("window_geometry")
        if isinstance(window_geometry, dict):
            saved_settings["window_geometry"] = window_geometry
        group_selections = normalize_group_selections(settings.get("group_selections"))
        if group_selections:
            saved_settings["group_selections"] = group_selections
        group_colors = normalize_group_colors(settings.get("group_colors"))
        if group_colors:
            saved_settings["group_colors"] = group_colors
    return {
        "version": 3,
        "settings": saved_settings,
        "groups": collect_groups(normalized_recipients, groups),
        "recipients": normalized_recipients,
    }


def make_export_data(
    recipients: list[dict], groups: list[str], phone_format: str = PHONE_FORMAT_E164, settings: dict | None = None
) -> dict:
    data = make_saved_data(recipients, groups, settings)
    for recipient in data["recipients"]:
        recipient["phone"] = format_phone_number(recipient.get("phone", ""), phone_format)
    return data


def write_default_data_file(path: Path) -> tuple[list[dict], list[str], dict, str | None]:
    settings = default_settings()
    data = make_saved_data([], [], settings)
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        return [], [], settings, f"Could not create local data file: {exc}"
    recipients, groups = parse_saved_data(data)
    return recipients, groups, settings, None


def load_recipient_data() -> tuple[list[dict], list[str], dict, str | None]:
    path = data_path()
    if not path.exists():
        return write_default_data_file(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [], default_settings(), f"Local data could not be read. A fresh empty list was opened. Details: {exc}"

    try:
        recipients, groups = parse_saved_data(data)
    except ValueError:
        return [], [], default_settings(), "Local data had an unexpected format. A fresh empty list was opened."

    return recipients, groups, parse_saved_settings(data), None


def load_recipients() -> tuple[list[dict], str | None]:
    recipients, _groups, _settings, error = load_recipient_data()
    return recipients, error


def save_recipient_data(recipients: list[dict], groups: list[str], settings: dict | None = None) -> str | None:
    try:
        data_path().write_text(json.dumps(make_saved_data(recipients, groups, settings), indent=2), encoding="utf-8")
    except OSError as exc:
        return f"Could not save local data: {exc}"
    return None


def save_recipients(recipients: list[dict]) -> str | None:
    return save_recipient_data(recipients, collect_groups(recipients))
