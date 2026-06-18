"""Generate a bcrypt hash for the admin password.

Uses the SAME hashing configuration as the app (``app.core.security``), so the
output is a valid value for ``ADMIN_PASSWORD_HASH`` in your ``.env``.

Usage (from the project root)::

    python scripts/hash_password.py
    # or
    python -m scripts.hash_password
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

# Ensure the project root is importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password  # noqa: E402


def main() -> None:
    """Prompt for a password (twice) and print its bcrypt hash."""
    password = getpass.getpass("Admin password: ")
    if not password:
        print("Password must not be empty.", file=sys.stderr)
        raise SystemExit(1)
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.", file=sys.stderr)
        raise SystemExit(1)

    print(hash_password(password))


if __name__ == "__main__":
    main()
