from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from .keys import setup_key
from .service import doctor, receive, transmission_due, transmit, verify
from .site import build_site


def parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def _print_key(result: dict[str, str]) -> None:
    print("GitHub Actions secret")
    print(f"  name : {result['name']}")
    print(f"  value: {result['value']}")
    print()
    print("Public fingerprint (safe to commit)")
    print(f"  {result['fingerprint']}")
    if result["local_path"]:
        print()
        print(f"Local secret file written: {result['local_path']}")
    print()
    print("Store the value in a password manager and GitHub Actions Secrets.")
    print("Never commit .env.local or paste the secret into Issues or logs.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="temporal_mailbox")
    sub = parser.add_subparsers(dest="command", required=True)

    key_parser = sub.add_parser("setup-key", help="generate a private temporal key")
    key_parser.add_argument("--save-local", action="store_true")
    key_parser.add_argument("--write-fingerprint", action="store_true")
    key_parser.add_argument("--overwrite", action="store_true")

    sub.add_parser("receive", help="capture and decode the current Friday's noise")
    sub.add_parser("due", help="print true when an automatic transmission is due")

    transmit_parser = sub.add_parser("transmit", help="fetch, encode, and actuate a result")
    transmit_parser.add_argument("--date", type=parse_day)
    transmit_parser.add_argument("--fixture", type=Path)
    transmit_parser.add_argument("--force", action="store_true")
    transmit_parser.add_argument("--actuator-seconds", type=float)
    transmit_parser.add_argument("--dry-run", action="store_true")

    simulate_parser = sub.add_parser("simulate", help="offline fixture test; writes no data")
    simulate_parser.add_argument(
        "--date", type=parse_day, default=date(2026, 7, 24)
    )
    simulate_parser.add_argument(
        "--fixture", type=Path, default=Path("tests/fixtures/mizuho_687.html")
    )

    verify_parser = sub.add_parser("verify", help="reproduce a saved reception")
    verify_parser.add_argument("--date", required=True, type=parse_day)

    doctor_parser = sub.add_parser("doctor", help="check configuration")
    doctor_parser.add_argument("--allow-missing-key", action="store_true")

    sub.add_parser("build-site", help="copy public JSON into docs/")

    args = parser.parse_args(argv)
    if args.command == "setup-key":
        _print_key(
            setup_key(
                save_local=args.save_local,
                write_fingerprint=args.write_fingerprint,
                overwrite=args.overwrite,
            )
        )
        return 0
    if args.command == "due":
        print("true" if transmission_due() else "false")
        return 0
    if args.command == "receive":
        print(json.dumps(receive(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "transmit":
        fixture = args.fixture.read_text(encoding="utf-8") if args.fixture else None
        result = transmit(
            day=args.date,
            fixture_text=fixture,
            force=args.force,
            actuator_seconds=args.actuator_seconds,
            dry_run=args.dry_run,
        )
        if result is None:
            print("PENDING: official result is not published yet")
            return 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "simulate":
        fixture = args.fixture.read_text(encoding="utf-8")
        # A deterministic demo key makes simulation possible before setup.
        from . import service as service_module

        original = service_module.load_secret
        service_module.load_secret = lambda: hashlib.sha256(b"FG830|demo-key").digest()
        try:
            result = service_module.transmit(
                day=args.date,
                fixture_text=fixture,
                force=True,
                actuator_seconds=0,
                dry_run=True,
            )
        finally:
            service_module.load_secret = original
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "verify":
        print(json.dumps(verify(args.date), ensure_ascii=False, indent=2))
        return 0
    if args.command == "doctor":
        print(
            json.dumps(
                doctor(allow_missing_key=args.allow_missing_key),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "build-site":
        build_site()
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
