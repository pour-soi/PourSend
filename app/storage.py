from __future__ import annotations

import json
import sys
from pathlib import Path

from core.groups import collect_groups, normalize_group_names, normalize_recipients


APP_FOLDER = "ringcentral_recipient_prep_data"
DATA_FILE = "recipients.json"


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
        recipients = normalize_recipients(data)
        return recipients, collect_groups(recipients)

    if isinstance(data, dict):
        recipients = normalize_recipients(data.get("recipients", []))
        groups = normalize_group_names(data.get("groups", []))
        return recipients, collect_groups(recipients, groups)

    raise ValueError("unexpected format")


def make_saved_data(recipients: list[dict], groups: list[str]) -> dict:
    normalized_recipients = normalize_recipients(recipients)
    return {
        "version": 2,
        "groups": collect_groups(normalized_recipients, groups),
        "recipients": normalized_recipients,
    }


def load_recipient_data() -> tuple[list[dict], list[str], str | None]:
    path = data_path()
    if not path.exists():
        return [], [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [], f"Local data could not be read. A fresh empty list was opened. Details: {exc}"

    try:
        recipients, groups = parse_saved_data(data)
    except ValueError:
        return [], [], "Local data had an unexpected format. A fresh empty list was opened."

    return recipients, groups, None


def load_recipients() -> tuple[list[dict], str | None]:
    recipients, _groups, error = load_recipient_data()
    return recipients, error


def save_recipient_data(recipients: list[dict], groups: list[str]) -> str | None:
    try:
        data_path().write_text(json.dumps(make_saved_data(recipients, groups), indent=2), encoding="utf-8")
    except OSError as exc:
        return f"Could not save local data: {exc}"
    return None


def save_recipients(recipients: list[dict]) -> str | None:
    return save_recipient_data(recipients, collect_groups(recipients))
