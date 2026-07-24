#!/usr/bin/env python3
"""Interactive first-run helper for a fresh repository clone."""

from temporal_mailbox.keys import setup_key


def main() -> None:
    result = setup_key(save_local=True, write_fingerprint=True, overwrite=False)
    print("\nFG830 local setup completed.\n")
    print("Create this GitHub Actions repository secret:")
    print(f"  Name : {result['name']}")
    print(f"  Value: {result['value']}")
    print("\nThe public fingerprint was written to data/protocol.json.")
    print("Commit data/protocol.json, but never commit .env.local.")


if __name__ == "__main__":
    main()
