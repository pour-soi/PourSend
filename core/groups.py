from __future__ import annotations

from typing import Iterable


ALL_RECIPIENTS = "__all__"
UNASSIGNED = "__unassigned__"


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


def normalize_recipient_groups(recipient: dict) -> list[str]:
    groups = recipient.get("groups", [])
    if isinstance(groups, str):
        groups = [groups]
    if not isinstance(groups, list):
        groups = []
    return normalize_group_names(groups)


def normalize_recipients(recipients: Iterable[dict]) -> list[dict]:
    normalized: list[dict] = []
    for recipient in recipients:
        if not isinstance(recipient, dict):
            continue
        item = dict(recipient)
        item["name"] = str(item.get("name", ""))
        item["phone"] = str(item.get("phone", ""))
        item["selected"] = bool(item.get("selected", False))
        item["groups"] = normalize_recipient_groups(item)
        normalized.append(item)
    return normalized


def collect_groups(recipients: Iterable[dict], groups: Iterable[str] = ()) -> list[str]:
    names = list(groups)
    for recipient in recipients:
        names.extend(normalize_recipient_groups(recipient))
    return normalize_group_names(names)


def create_group(groups: list[str], name: str) -> bool:
    clean_name = name.strip()
    if not clean_name or clean_name in groups:
        return False
    groups.append(clean_name)
    return True


def rename_group(recipients: list[dict], groups: list[str], old_name: str, new_name: str) -> bool:
    clean_name = new_name.strip()
    if old_name not in groups or not clean_name:
        return False
    if clean_name != old_name and clean_name in groups:
        return False

    groups[groups.index(old_name)] = clean_name
    for recipient in recipients:
        memberships = normalize_recipient_groups(recipient)
        recipient["groups"] = [clean_name if group == old_name else group for group in memberships]
    return True


def delete_group(recipients: list[dict], groups: list[str], name: str) -> bool:
    if name not in groups:
        return False
    groups.remove(name)
    for recipient in recipients:
        recipient["groups"] = [group for group in normalize_recipient_groups(recipient) if group != name]
    return True


def assign_to_group(recipients: list[dict], indexes: Iterable[int], group: str) -> None:
    clean_group = group.strip()
    if not clean_group:
        return
    for index in indexes:
        if 0 <= index < len(recipients):
            memberships = normalize_recipient_groups(recipients[index])
            if clean_group not in memberships:
                memberships.append(clean_group)
            recipients[index]["groups"] = memberships


def remove_from_group(recipients: list[dict], indexes: Iterable[int], group: str) -> None:
    for index in indexes:
        if 0 <= index < len(recipients):
            recipients[index]["groups"] = [
                name for name in normalize_recipient_groups(recipients[index]) if name != group
            ]


def recipient_matches_group(recipient: dict, group_filter: str) -> bool:
    groups = normalize_recipient_groups(recipient)
    if group_filter == ALL_RECIPIENTS:
        return True
    if group_filter == UNASSIGNED:
        return not groups
    return group_filter in groups


def filtered_recipient_indexes(
    recipients: list[dict], group_filter: str = ALL_RECIPIENTS, query: str = ""
) -> list[int]:
    search = query.strip().lower()
    indexes: list[int] = []
    for index, recipient in enumerate(recipients):
        if not recipient_matches_group(recipient, group_filter):
            continue
        haystack = f"{recipient.get('name', '')} {recipient.get('phone', '')}".lower()
        if search and search not in haystack:
            continue
        indexes.append(index)
    return indexes


def set_selected(recipients: list[dict], indexes: Iterable[int], selected: bool) -> None:
    for index in indexes:
        if 0 <= index < len(recipients):
            recipients[index]["selected"] = selected
