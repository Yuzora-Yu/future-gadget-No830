from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .config import DOCS_DIR, PROTOCOL_FILE, RECEPTIONS_DIR, STATUS_FILE, TRANSMISSIONS_DIR


def _records(directory: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(directory.glob("????-??-??.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return records


def _digest(path: Path) -> dict[str, object]:
    content = path.read_bytes()
    return {
        "file": path.name,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def build_site() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    status_target = DOCS_DIR / "status.json"
    protocol_target = DOCS_DIR / "protocol.json"
    history_target = DOCS_DIR / "history.json"
    integrity_target = DOCS_DIR / "integrity.json"

    if STATUS_FILE.exists():
        shutil.copyfile(STATUS_FILE, status_target)
    else:
        status_target.write_text("{}\n", encoding="utf-8")
    if PROTOCOL_FILE.exists():
        shutil.copyfile(PROTOCOL_FILE, protocol_target)
    else:
        protocol_target.write_text("{}\n", encoding="utf-8")

    history_target.write_text(
        json.dumps(
            {
                "receptions": _records(RECEPTIONS_DIR),
                "transmissions": _records(TRANSMISSIONS_DIR),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    integrity_target.write_text(
        json.dumps(
            {
                "generated_from": [
                    _digest(status_target),
                    _digest(protocol_target),
                    _digest(history_target),
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
