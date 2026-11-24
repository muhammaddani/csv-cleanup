"""Memungkinkan `python -m csv_cleanup`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())