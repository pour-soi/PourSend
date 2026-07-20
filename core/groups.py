from __future__ import annotations

import unicodedata
from typing import Iterable

from .phone import format_phone_number, normalize_us_phone, phone_search_digits


ALL_RECIPIENTS = "__all__"
ALL_RECIPIENTS_LABEL = "All Recipients"
DEFAULT_GROUP = "Default"
DEFAULT_GROUP_COLOR = "#53627c"
ALL_RECIPIENTS_COLOR = "#64748b"
GROUP_COLOR_PALETTE = (
    "#6685a8",
    "#7d72a8",
    "#548b8b",
    "#739276",
    "#aa8750",
    "#b47768",
    "#a66f83",
    "#718096",
)
SORT_PHONE = "phone"
SORT_GROUP = "group"
SORT_RECENT = "recent"


def group_name_key(name: str) -> str:
    return unicodedata.normalize("NFKC", str(name)).strip().casefold()


def group_name_error(name: str, groups: Iterable[str], exclude: str | None = None) -> str | None:
    clean_name = str(name).strip()
    if not clean_name:
        return "Enter a group name."
    key = group_name_key(clean_name)
    excluded_key = group_name_key(exclude) if exclude is not None else None
    protected = {group_name_key(ALL_RECIPIENTS_LABEL), group_name_key(DEFAULT_GROUP)}
    existing = {group_name_key(group) for group in groups if group_name_key(group) != excluded_key}
    if key in protected or key in existing:
        return f'A group named "{clean_name}" already exists. Please choose a different name.'
    return None


def normalize_group_names(groups: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for group in groups:
        name = str(group).strip()
        key = group_name_key(name)
        if not name or key in seen:
            continue
        seen.add(key)
        normalized.append(name)
    return normalized


def ensure_default_group(groups: Iterable[str] = ()) -> list[str]:
    normalized = [group for group in normalize_group_names(groups) if group_name_key(group) != group_name_key(DEFAULT_GROUP)]
    return [DEFAULT_GROUP, *normalized]


def normalize_group_colors(value) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    colors: dict[str, str] = {}
    for raw_group, raw_color in value.items():
        group = str(raw_group).strip()
        color = str(raw_color).strip().lower()
        if (
            group
            and len(color) == 7
            and color.startswith("#")
            and all(character in "0123456789abcdef" for character in color[1:])
        ):
            colors[group] = color
    return colors


def next_group_color(colors: dict[str, str]) -> str:
    used = set(colors.values())
    for color in GROUP_COLOR_PALETTE:
        if color not in used:
            return color
    return GROUP_COLOR_PALETTE[len(colors) % len(GROUP_COLOR_PALETTE)]


def ensure_group_colors(groups: Iterable[str], colors=None) -> dict[str, str]:
    normalized_colors = normalize_group_colors(colors)
    names = [group for group in normalize_group_names(groups) if group != ALL_RECIPIENTS]
    assigned = {group: normalized_colors[group] for group in names if group in normalized_colors}
    for group in names:
        if group not in assigned:
            assigned[group] = next_group_color(assigned)
    return {group: assigned[group] for group in names}


def rename_group_color(colors: dict[str, str], old_name: str, new_name: str) -> None:
    clean_name = new_name.strip()
    if old_name in colors and clean_name:
        colors[clean_name] = colors.pop(old_name)


def delete_group_color(colors: dict[str, str], group: str) -> None:
    colors.pop(group, None)


def resolve_group_color(group: str, colors: dict[str, str]) -> str:
    if group == ALL_RECIPIENTS:
        return ALL_RECIPIENTS_COLOR
    return colors.get(group, GROUP_COLOR_PALETTE[0])


def normalize_recipient_groups(recipient: dict) -> list[str]:
    groups = recipient.get("groups", [])
    if isinstance(groups, str):
        groups = [groups]
    if not isinstance(groups, list):
        groups = []
    names = normalize_group_names(groups)
    legacy_group = str(recipient.get("group", "")).strip()
    if legacy_group:
        names = normalize_group_names([*names, legacy_group])
    return names


def valid_recipient_groups(recipient: dict, groups: Iterable[str] = ()) -> list[str]:
    available_names = normalize_group_names(groups)
    available = ensure_default_group(available_names)
    memberships = [
        group for group in normalize_recipient_groups(recipient)
        if not available_names or group in available
    ]
    if not memberships:
        memberships = [DEFAULT_GROUP]
    return normalize_group_names(memberships)


def normalize_recipient_group(recipient: dict, groups: Iterable[str] = ()) -> str:
    return valid_recipient_groups(recipient, groups)[0]


def set_recipient_groups(recipient: dict, groups: Iterable[str]) -> None:
    memberships = normalize_group_names(groups) or [DEFAULT_GROUP]
    recipient["groups"] = memberships
    recipient["group"] = memberships[0]


def add_recipient_group(recipient: dict, group: str) -> bool:
    clean_group = group.strip()
    if not clean_group:
        return False
    memberships = valid_recipient_groups(recipient)
    if clean_group in memberships:
        return False
    if memberships == [DEFAULT_GROUP] and clean_group != DEFAULT_GROUP:
        memberships = []
    set_recipient_groups(recipient, [*memberships, clean_group])
    return True


def remove_recipient_group(recipient: dict, group: str) -> bool:
    clean_group = group.strip()
    memberships = valid_recipient_groups(recipient)
    if clean_group not in memberships:
        return False
    remaining = [name for name in memberships if name != clean_group]
    set_recipient_groups(recipient, remaining or [DEFAULT_GROUP])
    return True


def recipient_phone_key(recipient: dict) -> str:
    phone = str(recipient.get("phone", ""))
    normalized, status = normalize_us_phone(phone)
    if status == "Valid":
        return normalized
    return phone.strip()


def find_recipient_index_by_phone(recipients: list[dict], normalized_phone: str) -> int | None:
    for index, recipient in enumerate(recipients):
        if recipient_phone_key(recipient) == normalized_phone:
            return index
    return None


def valid_group_or_default(group: str, groups: Iterable[str]) -> str:
    clean_group = group.strip()
    return clean_group if clean_group in ensure_default_group(groups) else DEFAULT_GROUP


def preferred_group(current_group: str | None, recent_group: str, groups: Iterable[str]) -> str:
    if current_group:
        return valid_group_or_default(current_group, groups)
    return valid_group_or_default(recent_group, groups)


def normalize_recipients(recipients: Iterable[dict], groups: Iterable[str] = ()) -> list[dict]:
    available_groups = ensure_default_group(groups)
    seen_numbers: dict[str, int] = {}
    normalized: list[dict] = []
    for recipient in recipients:
        if not isinstance(recipient, dict):
            continue
        item = dict(recipient)
        item["name"] = str(item.get("name", ""))
        item["phone"] = str(item.get("phone", ""))
        key = recipient_phone_key(item)
        normalized_phone, phone_status = normalize_us_phone(item["phone"])
        if phone_status == "Valid":
            item["phone"] = normalized_phone
        item["selected"] = bool(item.get("selected", False))
        item["notes"] = str(item.get("notes", ""))
        memberships = valid_recipient_groups(item, available_groups)
        set_recipient_groups(item, memberships)
        if key and key in seen_numbers:
            existing = normalized[seen_numbers[key]]
            set_recipient_groups(existing, [*valid_recipient_groups(existing), *memberships])
            existing["selected"] = bool(existing.get("selected")) or item["selected"]
            if not existing.get("name") and item.get("name"):
                existing["name"] = item["name"]
            if item["notes"] and item["notes"] not in existing.get("notes", ""):
                existing["notes"] = "\n".join(text for text in [existing.get("notes", ""), item["notes"]] if text)
            continue
        if key:
            seen_numbers[key] = len(normalized)
        normalized.append(item)
    return normalized


def collect_groups(recipients: Iterable[dict], groups: Iterable[str] = ()) -> list[str]:
    names = list(groups)
    for recipient in recipients:
        if isinstance(recipient, dict):
            names.append(str(recipient.get("group", "")).strip())
            names.extend(normalize_recipient_groups(recipient))
    return ensure_default_group(names)


def create_group(groups: list[str], name: str) -> bool:
    clean_name = name.strip()
    if group_name_error(clean_name, groups):
        return False
    groups.append(clean_name)
    return True


def rename_group(recipients: list[dict], groups: list[str], old_name: str, new_name: str) -> bool:
    clean_name = new_name.strip()
    if old_name == DEFAULT_GROUP or old_name not in groups:
        return False
    if group_name_error(clean_name, groups, exclude=old_name):
        return False

    groups[groups.index(old_name)] = clean_name
    for recipient in recipients:
        memberships = [clean_name if group == old_name else group for group in valid_recipient_groups(recipient)]
        set_recipient_groups(recipient, memberships)
    return True


def delete_group(recipients: list[dict], groups: list[str], name: str) -> bool:
    if name == DEFAULT_GROUP or name not in groups:
        return False
    groups.remove(name)
    for recipient in recipients:
        if name in valid_recipient_groups(recipient):
            remove_recipient_group(recipient, name)
    return True


def assign_to_group(recipients: list[dict], indexes: Iterable[int], group: str) -> None:
    clean_group = group.strip()
    if not clean_group:
        return
    for index in indexes:
        if 0 <= index < len(recipients):
            add_recipient_group(recipients[index], clean_group)


def remove_from_group(recipients: list[dict], indexes: Iterable[int], group: str) -> None:
    for index in indexes:
        if 0 <= index < len(recipients):
            remove_recipient_group(recipients[index], group)


def recipient_matches_group(recipient: dict, group_filter: str | Iterable[str]) -> bool:
    if group_filter == ALL_RECIPIENTS:
        return True
    if not isinstance(group_filter, str):
        memberships = set(valid_recipient_groups(recipient))
        return any(group in memberships for group in group_filter)
    return group_filter in valid_recipient_groups(recipient)


def recipient_matches_search(recipient: dict, query: str = "", phone_format: str = "e164") -> bool:
    search = query.strip().lower()
    if not search:
        return True

    phone = str(recipient.get("phone", ""))
    normalized, status = normalize_us_phone(phone)
    display_phone = format_phone_number(phone, phone_format)
    group = "; ".join(valid_recipient_groups(recipient))
    notes = str(recipient.get("notes", ""))
    text_values = [display_phone, normalized if status == "Valid" else phone, group, notes]
    if any(search in value.lower() for value in text_values):
        return True

    search_digits = phone_search_digits(search)
    if search_digits:
        phone_values = [display_phone, normalized if status == "Valid" else phone, phone]
        return any(search_digits in phone_search_digits(value) for value in phone_values)
    return False


def sorted_recipient_indexes(
    recipients: list[dict], indexes: list[int], sort_field: str = SORT_RECENT, descending: bool = False
) -> list[int]:
    if sort_field == SORT_PHONE:
        by_position = sorted(indexes)
        return sorted(by_position, key=lambda index: recipient_phone_key(recipients[index]), reverse=descending)
    if sort_field == SORT_GROUP:
        by_position = sorted(indexes)
        return sorted(by_position, key=lambda index: "; ".join(valid_recipient_groups(recipients[index])).lower(), reverse=descending)
    return sorted(indexes, reverse=descending)


def filtered_recipient_indexes(
    recipients: list[dict],
    group_filter: str | Iterable[str] = ALL_RECIPIENTS,
    query: str = "",
    phone_format: str = "e164",
    sort_field: str = SORT_RECENT,
    descending: bool = False,
) -> list[int]:
    indexes: list[int] = []
    for index, recipient in enumerate(recipients):
        if not recipient_matches_group(recipient, group_filter):
            continue
        if not recipient_matches_search(recipient, query, phone_format):
            continue
        indexes.append(index)
    return sorted_recipient_indexes(recipients, indexes, sort_field, descending)


def checked_recipient_indexes(recipients: Iterable[dict]) -> list[int]:
    indexes: list[int] = []
    seen: set[str] = set()
    for index, recipient in enumerate(recipients):
        if not recipient.get("selected"):
            continue
        key = recipient_phone_key(recipient)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        indexes.append(index)
    return indexes


def set_selected(recipients: list[dict], indexes: Iterable[int], selected: bool) -> None:
    for index in indexes:
        if 0 <= index < len(recipients):
            recipients[index]["selected"] = selected


def count_duplicate_phone_numbers(recipients: Iterable[dict]) -> int:
    seen: set[str] = set()
    duplicates = 0
    for recipient in recipients:
        key = recipient_phone_key(recipient)
        if not key:
            continue
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def batch_update_recipients(
    recipients: list[dict],
    indexes: Iterable[int],
    *,
    group: str | None = None,
    notes: str | None = None,
) -> int:
    updated = 0
    for index in indexes:
        if not 0 <= index < len(recipients):
            continue
        if group is not None:
            clean_group = group.strip()
            if clean_group:
                set_recipient_groups(recipients[index], [clean_group])
        if notes is not None:
            recipients[index]["notes"] = notes.strip()
        updated += 1
    return updated
