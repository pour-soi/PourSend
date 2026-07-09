from __future__ import annotations

from typing import Iterable

from .phone import normalize_us_phone


ALL_RECIPIENTS = "__all__"
DEFAULT_GROUP = "Default"


def normalize_group_names(groups: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for group in groups:
        name = str(group).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def ensure_default_group(groups: Iterable[str] = ()) -> list[str]:
    normalized = normalize_group_names(groups)
    if DEFAULT_GROUP not in normalized:
        normalized.insert(0, DEFAULT_GROUP)
    return normalized


def normalize_recipient_groups(recipient: dict) -> list[str]:
    groups = recipient.get("groups", [])
    if isinstance(groups, str):
        groups = [groups]
    if not isinstance(groups, list):
        groups = []
    return normalize_group_names(groups)


def normalize_recipient_group(recipient: dict, groups: Iterable[str] = ()) -> str:
    available_names = normalize_group_names(groups)
    available = ensure_default_group(available_names)
    group = str(recipient.get("group", "")).strip()
    if not group:
        memberships = normalize_recipient_groups(recipient)
        group = memberships[0] if memberships else DEFAULT_GROUP
    if available_names and group not in available:
        group = DEFAULT_GROUP
    return group


def recipient_phone_key(recipient: dict) -> str:
    phone = str(recipient.get("phone", ""))
    normalized, status = normalize_us_phone(phone)
    if status == "Valid":
        return normalized
    return phone.strip()


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
        group = normalize_recipient_group(item, available_groups)
        item["group"] = group
        item["groups"] = [group]
        if key and key in seen_numbers:
            existing = normalized[seen_numbers[key]]
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
    if not clean_name or clean_name in groups:
        return False
    groups.append(clean_name)
    return True


def rename_group(recipients: list[dict], groups: list[str], old_name: str, new_name: str) -> bool:
    clean_name = new_name.strip()
    if old_name == DEFAULT_GROUP or old_name not in groups or not clean_name:
        return False
    if clean_name != old_name and clean_name in groups:
        return False

    old_members = [
        index for index, recipient in enumerate(recipients) if normalize_recipient_group(recipient, groups) == old_name
    ]
    groups[groups.index(old_name)] = clean_name
    for index in old_members:
        recipients[index]["group"] = clean_name
        recipients[index]["groups"] = [clean_name]
    return True


def delete_group(recipients: list[dict], groups: list[str], name: str) -> bool:
    if name == DEFAULT_GROUP or name not in groups:
        return False
    old_members = [
        index for index, recipient in enumerate(recipients) if normalize_recipient_group(recipient, groups) == name
    ]
    groups.remove(name)
    for index in old_members:
        recipients[index]["group"] = DEFAULT_GROUP
        recipients[index]["groups"] = [DEFAULT_GROUP]
    return True


def assign_to_group(recipients: list[dict], indexes: Iterable[int], group: str) -> None:
    clean_group = group.strip()
    if not clean_group:
        return
    for index in indexes:
        if 0 <= index < len(recipients):
            recipients[index]["group"] = clean_group
            recipients[index]["groups"] = [clean_group]


def remove_from_group(recipients: list[dict], indexes: Iterable[int], group: str) -> None:
    for index in indexes:
        if 0 <= index < len(recipients):
            if normalize_recipient_group(recipients[index]) == group:
                recipients[index]["group"] = DEFAULT_GROUP
                recipients[index]["groups"] = [DEFAULT_GROUP]


def recipient_matches_group(recipient: dict, group_filter: str) -> bool:
    if group_filter == ALL_RECIPIENTS:
        return True
    return normalize_recipient_group(recipient) == group_filter


def filtered_recipient_indexes(
    recipients: list[dict], group_filter: str = ALL_RECIPIENTS, query: str = ""
) -> list[int]:
    search = query.strip().lower()
    indexes: list[int] = []
    for index, recipient in enumerate(recipients):
        if not recipient_matches_group(recipient, group_filter):
            continue
        haystack = f"{recipient.get('phone', '')} {recipient.get('notes', '')}".lower()
        if search and search not in haystack:
            continue
        indexes.append(index)
    return indexes


def set_selected(recipients: list[dict], indexes: Iterable[int], selected: bool) -> None:
    for index in indexes:
        if 0 <= index < len(recipients):
            recipients[index]["selected"] = selected
