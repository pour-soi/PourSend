from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

from core.groups import (
    collect_groups,
    ALL_RECIPIENTS_LABEL,
    DEFAULT_GROUP,
    ensure_default_group,
    normalize_group_colors,
    normalize_group_names,
    normalize_recipients,
    recipient_phone_key,
    group_name_key,
)
from core.phone import PHONE_FORMAT_E164, format_phone_number, normalize_phone_format
from core.group_tree import normalize_group_tree, serialize_group_tree


APP_FOLDER = "poursend_data"
DATA_FILE = "recipients.json"


def repair_saved_group_names(data) -> tuple[object, list[str]]:
    if not isinstance(data, (dict, list)):
        return data, []
    repaired = deepcopy(data)
    recipients = repaired if isinstance(repaired, list) else repaired.get("recipients", [])
    if not isinstance(recipients, list):
        recipients = []
    raw_groups = repaired.get("groups", []) if isinstance(repaired, dict) else []
    tokens = list(raw_groups) if isinstance(raw_groups, list) else []
    known_raw = {str(token) for token in tokens}
    if not tokens:
        for recipient in recipients:
            if not isinstance(recipient, dict):
                continue
            memberships = recipient.get("groups", [])
            if isinstance(memberships, str):
                memberships = [memberships]
            if isinstance(memberships, list):
                for membership in memberships:
                    if str(membership) not in known_raw:
                        known_raw.add(str(membership))
                        tokens.append(membership)
            legacy = recipient.get("group")
            if legacy is not None and str(legacy) not in known_raw:
                known_raw.add(str(legacy))
                tokens.append(legacy)

    used = {group_name_key(ALL_RECIPIENTS_LABEL), group_name_key(DEFAULT_GROUP)}
    assigned_names = [DEFAULT_GROUP]
    reference_map: dict[str, str] = {}
    occurrence_map: dict[str, list[str]] = {}
    warnings: list[str] = []
    for token in tokens:
        raw = str(token)
        clean = raw.strip()
        if not clean:
            continue
        if group_name_key(clean) == group_name_key(DEFAULT_GROUP) and DEFAULT_GROUP not in reference_map.values():
            assigned = DEFAULT_GROUP
        else:
            assigned = clean
            if group_name_key(assigned) in used:
                suffix = 2
                while group_name_key(f"{clean} ({suffix})") in used:
                    suffix += 1
                assigned = f"{clean} ({suffix})"
                warnings.append(f'Group "{clean}" was renamed to "{assigned}" because group names must be unique.')
            used.add(group_name_key(assigned))
            assigned_names.append(assigned)
        reference_map.setdefault(raw, assigned)
        occurrence_map.setdefault(raw, []).append(assigned)

    def repaired_name(value) -> str:
        raw = str(value)
        return reference_map.get(raw, raw.strip())

    for recipient in recipients:
        if not isinstance(recipient, dict):
            continue
        had_groups = "groups" in recipient
        memberships = recipient.get("groups", [])
        if isinstance(memberships, str):
            memberships = [memberships]
        if not isinstance(memberships, list):
            memberships = []
        names = [repaired_name(group) for group in memberships if str(group).strip()]
        legacy = recipient.get("group")
        names = normalize_group_names(names)
        if had_groups and names:
            recipient["groups"] = names
        if legacy is not None and str(legacy).strip():
            recipient["group"] = repaired_name(legacy)

    if isinstance(repaired, dict):
        repaired["groups"] = assigned_names
        settings = repaired.get("settings")
        if isinstance(settings, dict):
            tree = settings.get("group_tree")
            if isinstance(tree, list):
                queues = {raw: list(values) for raw, values in occurrence_map.items()}
                for record in tree:
                    if not isinstance(record, dict):
                        continue
                    raw = str(record.get("name", ""))
                    choices = queues.get(raw, [])
                    record["name"] = choices.pop(0) if choices else repaired_name(raw)
            for key in ("group_colors", "group_selections"):
                value = settings.get(key)
                if isinstance(value, dict):
                    settings[key] = {repaired_name(name): content for name, content in value.items()}
    return repaired, warnings


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
    data, _warnings = repair_saved_group_names(data)
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
        group_tree = raw_settings.get("group_tree")
        if isinstance(group_tree, list):
            settings["group_tree"] = group_tree
        migration_warnings = raw_settings.get("migration_warnings")
        if isinstance(migration_warnings, list):
            settings["migration_warnings"] = [str(warning) for warning in migration_warnings if str(warning)]
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
        group_tree = normalize_group_tree(groups, settings.get("group_tree"), settings.get("group_colors"))
        saved_settings["group_tree"] = serialize_group_tree(group_tree)
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

    repaired_data, warnings = repair_saved_group_names(data)
    try:
        recipients, groups = parse_saved_data(repaired_data)
    except ValueError:
        return [], [], default_settings(), "Local data had an unexpected format. A fresh empty list was opened."

    warning = "\n".join(warnings) if warnings else None
    return recipients, groups, parse_saved_settings(repaired_data), warning


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
