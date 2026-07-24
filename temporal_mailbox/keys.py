from __future__ import annotations

import base64
import hashlib
import os
import secrets
from pathlib import Path

from .config import KEY_ID, LOCAL_ENV_FILE, PROTOCOL_FILE, PROTOCOL_VERSION, SOFTWARE_VERSION
from .storage import read_json, write_json

ENV_NAME = "TEMPORAL_KEY"


def decode_secret(value: str) -> bytes:
    value = value.strip().strip('"').strip("'")
    if not value:
        raise ValueError("empty key")

    if len(value) == 64:
        try:
            key = bytes.fromhex(value)
        except ValueError:
            key = b""
        if len(key) == 32:
            return key

    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        key = base64.urlsafe_b64decode(value + padding)
    except Exception as exc:  # pragma: no cover
        raise ValueError("TEMPORAL_KEY must be 64 hex chars or base64url") from exc
    if len(key) != 32:
        raise ValueError("TEMPORAL_KEY must decode to exactly 32 bytes")
    return key


def _read_local_secret(path: Path = LOCAL_ENV_FILE) -> str:
    if not path.exists():
        return ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == ENV_NAME:
            return value.strip()
    return ""


def load_secret() -> bytes:
    value = os.getenv(ENV_NAME, "") or _read_local_secret()
    if not value:
        raise RuntimeError(
            f"{ENV_NAME} is not configured. Run "
            "`python -m temporal_mailbox setup-key --save-local --write-fingerprint`."
        )
    return decode_secret(value)


def key_fingerprint(key: bytes) -> str:
    return hashlib.sha256(b"FG830|key-fingerprint|" + key).hexdigest()


def generate_key() -> tuple[str, str]:
    key = secrets.token_bytes(32)
    encoded = base64.urlsafe_b64encode(key).decode("ascii").rstrip("=")
    return encoded, key_fingerprint(key)


def save_local_secret(encoded: str, overwrite: bool = False) -> Path:
    if LOCAL_ENV_FILE.exists() and not overwrite:
        raise FileExistsError(
            f"{LOCAL_ENV_FILE.name} already exists. Use --overwrite only when rotating the key."
        )
    LOCAL_ENV_FILE.write_text(
        "# Local-only secret. This file is excluded by .gitignore.\n"
        f"{ENV_NAME}={encoded}\n",
        encoding="utf-8",
    )
    try:
        LOCAL_ENV_FILE.chmod(0o600)
    except OSError:
        pass
    return LOCAL_ENV_FILE


def write_public_fingerprint(fingerprint: str) -> None:
    current = read_json(PROTOCOL_FILE, {})
    current.update(
        {
            "protocol_version": PROTOCOL_VERSION,
            "software_version": SOFTWARE_VERSION,
            "key_id": KEY_ID,
            "key_fingerprint": fingerprint,
            "status": "PRE-COMMITTED; PRIVATE KEY NOT STORED IN GIT",
        }
    )
    write_json(PROTOCOL_FILE, current)


def setup_key(save_local: bool, write_fingerprint: bool, overwrite: bool) -> dict[str, str]:
    encoded, fingerprint = generate_key()
    local_path = ""
    if save_local:
        local_path = str(save_local_secret(encoded, overwrite=overwrite))
    if write_fingerprint:
        write_public_fingerprint(fingerprint)
    return {
        "name": ENV_NAME,
        "value": encoded,
        "fingerprint": fingerprint,
        "local_path": local_path,
    }
