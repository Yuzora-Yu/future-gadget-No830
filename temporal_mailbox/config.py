from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path

PROTOCOL_VERSION = "FG830-ATX-v1"
SOFTWARE_VERSION = "1.1.0"
FRAME_VERSION = 1
KEY_ID = "176248"
JST = timezone(timedelta(hours=9), name="JST")

RECEPTION_TIME = time(9, 0)
RECEPTION_CUTOFF = time(18, 0)
TRANSMISSION_TIME = time(20, 0)
TRANSMISSION_GRACE_END = time(3, 0)

NOISE_BYTES = 262_144
SAMPLES_PER_BIT = 64
CONTROL_COUNT = 127
ACTUATOR_SECONDS = 32.0

MIZUHO_LOTO7_URL = (
    "https://www.mizuhobank.co.jp/takarakuji/check/loto/loto7/index.html"
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RECEPTIONS_DIR = DATA_DIR / "receptions"
TRANSMISSIONS_DIR = DATA_DIR / "transmissions"
NOISE_DIR = DATA_DIR / "noise"
STATUS_FILE = DATA_DIR / "status.json"
PROTOCOL_FILE = DATA_DIR / "protocol.json"
DOCS_DIR = ROOT / "docs"
LOCAL_ENV_FILE = ROOT / ".env.local"


def now_jst() -> datetime:
    return datetime.now(JST)
