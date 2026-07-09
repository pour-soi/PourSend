from __future__ import annotations

import json
import sys
from pathlib import Path


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


def load_recipients() -> tuple[list[dict], str | None]:
    path = data_path()
    if not path.exists():
        return [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], f"Local data could not be read. A fresh empty list was opened. Details: {exc}"

    if not isinstance(data, list):
        return [], "Local data had an unexpected format. A fresh empty list was opened."

    recipients = []
    for item in data:
        if isinstance(item, dict):
            recipients.append(
                {
                    "name": str(item.get("name", "")),
                    "phone": str(item.get("phone", "")),
                    "selected": bool(item.get("selected", False)),
                }
            )
    return recipients, None


def save_recipients(recipients: list[dict]) -> str | None:
    try:
        data_path().write_text(json.dumps(recipients, indent=2), encoding="utf-8")
    except OSError as exc:
        return f"Could not save local data: {exc}"
    return None
