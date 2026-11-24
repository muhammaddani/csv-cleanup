"""Antarmuka baris perintah untuk csv-cleanup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cleaner import CleanupError, CleanupReport, clean_rows, read_csv, write_csv


def _parse_columns(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {c.strip() for c in value.split(",") if c.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-cleanup",
        description="Bersihkan file CSV yang berantakan: duplikat, spasi, nilai kosong.",
    )
    parser.add_argument("csv_file", type=Path, help="File CSV yang akan dibersihkan.")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="File hasil (bawaan: <nama>_clean.csv). Tidak dipakai saat --dry-run.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Tampilkan laporan tanpa menulis file apa pun.",
    )
    parser.add_argument(
        "--dedupe", action="store_true",
        help="Buang baris duplikat.",
    )
    parser.add_argument(
        "--dedupe-by", metavar="KOLOM",
        help="Buang duplikat berdasarkan kolom ini (dipisah koma). Implisit mengaktifkan dedupe.",
    )
    parser.add_argument(
        "--trim-columns", metavar="KOLOM",
        help="Rapikan hanya kolom ini (dipisah koma). Bawaan: semua kolom.",
    )
    parser.add_argument(
        "--keep-nulls", action="store_true",
        help="Jangan normalkan nilai seperti '-', 'N/A', 'null' menjadi kosong.",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Matikan keluaran berwarna.",
    )
    return parser


def print_report(
    report: CleanupReport,
    input_path: Path,
    output_path: Path | None,
    dry_run: bool,
) -> None:
    line = "=" * 60
    print(line)
    print("  LAPORAN PEMBERSIHAN" + (" (PREVIEW — tidak ada file yang ditulis)" if dry_run else ""))
    print(line)
    print(f"  File input : {input_path.name} ({report.rows_in} baris)")
    if output_path is not None:
        print(f"  File output: {output_path}")
    print()
    print(f"  Baris duplikat dibuang   : {report.duplicates_removed}")
    print(f"  Sel dirapikan            : {report.cells_trimmed}")
    print(f"  Nilai kosong dinormalkan : {report.nulls_normalized}")
    print()
    print(f"  Hasil: {report.rows_out} baris bersih.")
    print(line)


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(input_path.stem + "_clean" + input_path.suffix)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        columns, rows = read_csv(args.csv_file)
    except CleanupError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    dedupe_by = None
    if args.dedupe_by:
        dedupe_by = [c.strip() for c in args.dedupe_by.split(",") if c.strip()]
        missing = [c for c in dedupe_by if c not in columns]
        if missing:
            print(
                f"Error: kolom untuk --dedupe-by tidak ada: {', '.join(missing)}. "
                f"Kolom tersedia: {', '.join(columns)}",
                file=sys.stderr,
            )
            return 1

    trim_columns = _parse_columns(args.trim_columns)
    if trim_columns is not None:
        missing = [c for c in trim_columns if c not in columns]
        if missing:
            print(
                f"Error: kolom untuk --trim-columns tidak ada: {', '.join(missing)}. "
                f"Kolom tersedia: {', '.join(columns)}",
                file=sys.stderr,
            )
            return 1

    result = clean_rows(
        columns,
        rows,
        trim_columns=trim_columns,
        normalize_nulls=not args.keep_nulls,
        dedupe=args.dedupe or bool(dedupe_by),
        dedupe_by=dedupe_by,
    )

    output_path = None if args.dry_run else (args.output or default_output_path(args.csv_file))
    print_report(result.report, args.csv_file, output_path, args.dry_run)

    if not args.dry_run and output_path is not None:
        write_csv(output_path, result.columns, result.rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())