from __future__ import annotations

from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

from .groups import (
    DEFAULT_GROUP,
    DEFAULT_GROUP_COLOR,
    GROUP_COLOR_PALETTE,
    next_group_color,
    group_name_error,
    normalize_group_colors,
    normalize_group_names,
)


LEGACY_GROUP_NAMESPACE = "https://poursend.app/groups/"


def legacy_group_id(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"{LEGACY_GROUP_NAMESPACE}{name}"))


def new_group_id(existing_ids: set[str], name: str) -> str:
    seed = name
    suffix = 1
    while True:
        candidate = str(uuid5(NAMESPACE_URL, f"{LEGACY_GROUP_NAMESPACE}created/{seed}"))
        if candidate not in existing_ids:
            return candidate
        suffix += 1
        seed = f"{name}/{suffix}"


def normalize_group_tree(groups, value=None, legacy_colors=None) -> list[dict]:
    names = normalize_group_names(groups)
    saved = value if isinstance(value, list) else []
    by_name: dict[str, dict] = {}
    used_ids: set[str] = set()
    for raw in saved:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name", "")).strip()
        group_id = str(raw.get("id", "")).strip()
        if not name or name not in names or not group_id or group_id in used_ids:
            continue
        color = raw.get("color")
        if color is not None:
            color = normalize_group_colors({"color": color}).get("color")
        by_name[name] = {
            "id": group_id,
            "name": name,
            "parent_id": str(raw.get("parent_id", "")).strip() or None,
            "color": color,
            "expanded": bool(raw.get("expanded", True)),
        }
        used_ids.add(group_id)

    legacy = normalize_group_colors(legacy_colors)
    assigned = {record["id"]: record["color"] for record in by_name.values() if record["color"]}
    records: list[dict] = []
    for name in names:
        record = by_name.get(name)
        if record is None:
            group_id = legacy_group_id(name)
            if group_id in used_ids:
                group_id = new_group_id(used_ids, name)
            color = DEFAULT_GROUP_COLOR if name == DEFAULT_GROUP else legacy.get(name)
            if color is None:
                color = next_group_color(assigned)
            record = {"id": group_id, "name": name, "parent_id": None, "color": color, "expanded": True}
            used_ids.add(group_id)
        records.append(record)
        if name == DEFAULT_GROUP:
            record["color"] = DEFAULT_GROUP_COLOR
        elif record["color"]:
            assigned[record["id"]] = record["color"]

    valid_ids = {record["id"] for record in records}
    for record in records:
        parent_id = record["parent_id"]
        parent = next((item for item in records if item["id"] == parent_id), None)
        if (
            record["name"] == DEFAULT_GROUP
            or parent_id not in valid_ids
            or parent_id == record["id"]
            or parent is None
            or parent.get("parent_id") is not None
            or parent["name"] == DEFAULT_GROUP
        ):
            record["parent_id"] = None
        if record["parent_id"] is not None and record["color"] is None:
            continue
        if record["color"] is None:
            record["color"] = next_group_color(assigned)
            assigned[record["id"]] = record["color"]
    return records


def serialize_group_tree(records: list[dict]) -> list[dict]:
    return deepcopy(records)


def record_by_id(records: list[dict], group_id: str | None) -> dict | None:
    return next((record for record in records if record["id"] == group_id), None)


def record_by_name(records: list[dict], name: str | None) -> dict | None:
    return next((record for record in records if record["name"] == name), None)


def children_of(records: list[dict], parent_id: str) -> list[dict]:
    return [record for record in records if record.get("parent_id") == parent_id]


def visible_group_records(records: list[dict]) -> list[tuple[dict, int]]:
    visible: list[tuple[dict, int]] = []
    for record in records:
        if record.get("parent_id") is not None:
            continue
        visible.append((record, 0))
        if record.get("expanded", True):
            visible.extend((child, 1) for child in children_of(records, record["id"]))
    return visible


def group_scope_names(records: list[dict], group_id: str | None) -> list[str]:
    record = record_by_id(records, group_id)
    if record is None:
        return []
    names = [record["name"]]
    if record.get("parent_id") is None:
        names.extend(child["name"] for child in children_of(records, record["id"]))
    return names


def resolved_group_color(records: list[dict], group_id: str) -> str:
    record = record_by_id(records, group_id)
    if record is None:
        return GROUP_COLOR_PALETTE[0]
    if record.get("color"):
        return record["color"]
    parent = record_by_id(records, record.get("parent_id"))
    return parent.get("color") if parent and parent.get("color") else GROUP_COLOR_PALETTE[0]


def add_group_record(records: list[dict], name: str, parent_id: str | None = None) -> dict | None:
    clean_name = name.strip()
    if group_name_error(clean_name, [record["name"] for record in records]):
        return None
    parent = record_by_id(records, parent_id)
    if parent_id and (parent is None or parent["name"] == DEFAULT_GROUP or parent.get("parent_id") is not None):
        return None
    group_id = new_group_id({record["id"] for record in records}, clean_name)
    color = None if parent_id else next_group_color({r["id"]: resolved_group_color(records, r["id"]) for r in records})
    record = {"id": group_id, "name": clean_name, "parent_id": parent_id, "color": color, "expanded": True}
    records.append(record)
    if parent:
        parent["expanded"] = True
    return record


def move_group_record(records: list[dict], group_id: str, parent_id: str | None) -> bool:
    record = record_by_id(records, group_id)
    parent = record_by_id(records, parent_id)
    if record is None or record["name"] == DEFAULT_GROUP or group_id == parent_id:
        return False
    if parent_id and (parent is None or parent["name"] == DEFAULT_GROUP or parent.get("parent_id") is not None):
        return False
    if children_of(records, group_id) and parent_id is not None:
        return False
    inherited_color = resolved_group_color(records, group_id)
    record["parent_id"] = parent_id
    if parent:
        parent["expanded"] = True
    if parent_id is None and record.get("color") is None:
        record["color"] = inherited_color
    return True


def remove_group_records(records: list[dict], group_id: str, promote_children: bool) -> list[dict]:
    removed = [record for record in records if record["id"] == group_id]
    children = children_of(records, group_id)
    removed_ids = {group_id}
    if promote_children:
        for child in children:
            child["parent_id"] = None
            if child.get("color") is None:
                child["color"] = resolved_group_color(records, group_id)
    else:
        removed_ids.update(child["id"] for child in children)
        removed.extend(children)
    records[:] = [record for record in records if record["id"] not in removed_ids]
    return removed
