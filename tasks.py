#!/usr/bin/env python3
"""Tugas pengembangan lintas-platform untuk csv-cleanup.

Contoh:
    python tasks.py            # daftar tugas
    python tasks.py test       # jalankan test
    python tasks.py demo       # contoh pembersihan (dry-run)
    python tasks.py build      # buat paket distribusi
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


def install() -> int:
    code = _run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    if code:
        return code
    return _run([sys.executable, "-m", "pip", "install", "-e", ".[test]"])


def test() -> int:
    return _run([sys.executable, "-m", "pytest", "-v"])


def demo() -> int:
    """Contoh pembersihan pada data sampel (aman, tanpa menulis file)."""
    return _run([sys.executable, "-m", "csv_cleanup", "data/messy_sample.csv", "--dedupe", "--dry-run"])


def build() -> int:
    """Buat paket distribusi (wheel + sdist)."""
    code = _run([sys.executable, "-m", "pip", "install", "--quiet", "build"])
    if code:
        return code
    return _run([sys.executable, "-m", "build"])


def clean() -> int:
    for target in [".pytest_cache", "build", "dist", "out", "src/csv_cleanup.egg-info"]:
        shutil.rmtree(ROOT / target, ignore_errors=True)
    for pyc in ROOT.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)
    shutil.rmtree(ROOT / "src" / "csv_cleanup" / "__pycache__", ignore_errors=True)
    shutil.rmtree(ROOT / "tests" / "__pycache__", ignore_errors=True)
    print("Bersih.")
    return 0


TASKS = {
    "install": (install, "Pasang paket secara editable + pytest"),
    "test": (test, "Jalankan seluruh test"),
    "demo": (demo, "Contoh pembersihan pada data sampel (dry-run)"),
    "build": (build, "Buat paket distribusi (wheel + sdist)"),
    "clean": (clean, "Hapus artefak build dan cache"),
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        print("Tugas yang tersedia:\n")
        for name, (_, desc) in TASKS.items():
            print(f"  python tasks.py {name:<8} {desc}")
        return 0
    name = sys.argv[1]
    if name not in TASKS:
        print(f"Tugas tidak dikenal: {name}", file=sys.stderr)
        return 1
    return TASKS[name][0]()


if __name__ == "__main__":
    raise SystemExit(main())