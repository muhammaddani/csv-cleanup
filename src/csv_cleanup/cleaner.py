"""Logika pembersihan CSV — fungsi murni, tanpa efek samping.

Semua fungsi di sini menerima dan mengembalikan data; tidak ada yang membaca
atau menulis file. Itu membuatnya mudah diuji dan dipakai ulang.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# Nilai yang dianggap "kosong" meskipun tertulis sesuatu di dalam sel.
# Dibandingkan setelah dirapikan dan dihuruf-kecilkan.
NULL_TOKENS = frozenset({"", "-", "n/a", "na", "null", "none", "nil", "tidak ada"})

# Karakter yang sering menyusup dari ekspor (spasi non-standar, tab, dll.)
HIDDEN_WHITESPACE = {
    "\u00a0": " ",  # non-breaking space
    "\u200b": "",   # zero-width space
    "\t": " ",      # tab
    "\r": " ",
    "\n": " ",
}


class CleanupError(Exception):
    """Kesalahan yang bisa dipahami pengguna (bukan bug)."""


@dataclass
class CleanupReport:
    """Ringkasan apa yang diubah selama pembersihan."""

    rows_in: int = 0
    rows_out: int = 0
    duplicates_removed: int = 0
    cells_trimmed: int = 0
    nulls_normalized: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(
            self.duplicates_removed or self.cells_trimmed or self.nulls_normalized
        )


@dataclass
class CleanupResult:
    """Kolom, baris hasil, dan laporan."""

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, str]] = field(default_factory=list)
    report: CleanupReport = field(default_factory=CleanupReport)


# ---------------------------------------------------------------------------
# Pembersihan tingkat sel
# ---------------------------------------------------------------------------

def clean_cell(value: str, normalize_nulls: bool = True) -> tuple[str, bool, bool]:
    """Bersihkan satu sel.

    Kembalikan (nilai_baru, dirapikan?, dinormalkan?).
    """

    # Ganti karakter tersembunyi dengan spasi biasa lebih dulu.
    cleaned = value
    for bad, good in HIDDEN_WHITESPACE.items():
        if bad in cleaned:
            cleaned = cleaned.replace(bad, good)

    # Rapikan spasi berlebih di ujung dan gandakan di tengah.
    trimmed = " ".join(cleaned.split())
    was_trimmed = trimmed != value

    normalized = False
    if normalize_nulls and trimmed.strip().lower() in NULL_TOKENS:
        if trimmed != "":
            normalized = True
        trimmed = ""

    return trimmed, was_trimmed, normalized


def clean_rows(
    columns: list[str],
    rows: Iterable[dict[str, str]],
    *,
    trim_columns: set[str] | None = None,
    normalize_nulls: bool = True,
    dedupe: bool = False,
    dedupe_by: list[str] | None = None,
) -> CleanupResult:
    """Bersihkan seluruh baris dan kembalikan hasil + laporan."""

    result = CleanupResult(columns=list(columns))
    report = result.report
    seen: set[tuple[str, ...]] = set()

    dedupe_keys = dedupe_by or columns

    for row in rows:
        report.rows_in += 1

        new_row: dict[str, str] = {}
        for column in columns:
            value = row.get(column, "")
            if trim_columns is not None and column not in trim_columns:
                new_row[column] = value
                continue
            cleaned, was_trimmed, was_normalized = clean_cell(value, normalize_nulls)
            new_row[column] = cleaned
            if was_trimmed:
                report.cells_trimmed += 1
            if was_normalized:
                report.nulls_normalized += 1

        if dedupe:
            key = tuple(new_row.get(c, "") for c in dedupe_keys)
            if key in seen:
                report.duplicates_removed += 1
                continue
            seen.add(key)

        result.rows.append(new_row)
        report.rows_out += 1

    return result


# ---------------------------------------------------------------------------
# Baca / tulis
# ---------------------------------------------------------------------------

def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Baca CSV; beri pesan jelas bila file tidak ada atau tanpa header."""

    if not path.exists():
        raise CleanupError(f"File tidak ditemukan: {path}")

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise CleanupError(f"File CSV kosong atau tanpa header: {path}")
            columns = [c.strip() for c in reader.fieldnames]
            rows = [
                {(k or "").strip(): (v if v is not None else "") for k, v in row.items()}
                for row in reader
            ]
    except UnicodeDecodeError as exc:
        raise CleanupError(
            f"File {path} bukan teks UTF-8 yang valid. Coba simpan ulang sebagai UTF-8. ({exc})"
        ) from exc

    return columns, rows


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    """Tulis hasil ke CSV UTF-8."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})