"""Test untuk csv-cleanup.

Menguji pembersihan sel, alur clean_rows (duplikat, kolom terpilih), kode
keluar CLI, dan mode dry-run.

Jalankan dengan:
    python -m pytest -v
"""

import csv
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from csv_cleanup.cleaner import (  # noqa: E402
    CleanupError,
    clean_cell,
    clean_rows,
    read_csv,
    write_csv,
)
from csv_cleanup.cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Pembersihan sel
# ---------------------------------------------------------------------------

class TestCleanCell:
    def test_trims_surrounding_spaces(self):
        value, trimmed, normalized = clean_cell("  Budi  ")
        assert value == "Budi"
        assert trimmed is True
        assert normalized is False

    def test_collapses_inner_spaces(self):
        value, trimmed, _ = clean_cell("Jakarta    Pusat")
        assert value == "Jakarta Pusat"
        assert trimmed is True

    def test_unchanged_cell_reports_no_trim(self):
        value, trimmed, _ = clean_cell("Budi")
        assert value == "Budi"
        assert trimmed is False

    def test_normalizes_null_tokens(self):
        for token in ["-", "N/A", "na", "null", "NULL", "None", "tidak ada"]:
            value, _, normalized = clean_cell(token)
            assert value == "", f"{token!r} should become empty"
            assert normalized is True, f"{token!r} should count as normalized"

    def test_blank_stays_blank_without_counting(self):
        value, _, normalized = clean_cell("")
        assert value == ""
        assert normalized is False

    def test_null_normalization_can_be_disabled(self):
        value, _, normalized = clean_cell("N/A", normalize_nulls=False)
        assert value == "N/A"
        assert normalized is False

    def test_replaces_hidden_whitespace(self):
        value, _, _ = clean_cell("Budi\u00a0Santoso")
        assert value == "Budi Santoso"

    def test_removes_zero_width_space(self):
        value, _, _ = clean_cell("Bu\u200bdi")
        assert value == "Budi"

    def test_replaces_tab_with_space(self):
        value, _, _ = clean_cell("Budi\tSantoso")
        assert value == "Budi Santoso"


# ---------------------------------------------------------------------------
# clean_rows
# ---------------------------------------------------------------------------

COLUMNS = ["nama", "kota"]


class TestCleanRows:
    def test_no_duplicates_keeps_all(self):
        rows = [{"nama": "A", "kota": "X"}, {"nama": "B", "kota": "Y"}]
        result = clean_rows(COLUMNS, rows)
        assert len(result.rows) == 2
        assert result.report.duplicates_removed == 0

    def test_dedupe_removes_exact_duplicates(self):
        rows = [{"nama": "A", "kota": "X"}, {"nama": "A", "kota": "X"}, {"nama": "B", "kota": "Y"}]
        result = clean_rows(COLUMNS, rows, dedupe=True)
        assert len(result.rows) == 2
        assert result.report.duplicates_removed == 1

    def test_dedupe_happens_after_cleaning(self):
        # Kedua baris sama setelah dirapikan, jadi harus dianggap duplikat.
        rows = [{"nama": "  A  ", "kota": "X"}, {"nama": "A", "kota": "X"}]
        result = clean_rows(COLUMNS, rows, dedupe=True)
        assert len(result.rows) == 1
        assert result.report.duplicates_removed == 1

    def test_dedupe_by_single_column(self):
        rows = [
            {"nama": "A", "kota": "X"},
            {"nama": "A", "kota": "Y"},
            {"nama": "B", "kota": "Z"},
        ]
        result = clean_rows(COLUMNS, rows, dedupe=True, dedupe_by=["nama"])
        assert [r["nama"] for r in result.rows] == ["A", "B"]

    def test_trim_only_selected_columns(self):
        rows = [{"nama": "  A  ", "kota": "  X  "}]
        result = clean_rows(COLUMNS, rows, trim_columns={"nama"})
        assert result.rows[0]["nama"] == "A"
        assert result.rows[0]["kota"] == "  X  "

    def test_report_counts(self):
        rows = [{"nama": "  A  ", "kota": "-"}]
        result = clean_rows(COLUMNS, rows)
        assert result.report.rows_in == 1
        assert result.report.rows_out == 1
        assert result.report.cells_trimmed == 1
        assert result.report.nulls_normalized == 1

    def test_has_changes_flag(self):
        clean = clean_rows(COLUMNS, [{"nama": "A", "kota": "X"}])
        assert clean.report.has_changes is False
        dirty = clean_rows(COLUMNS, [{"nama": "  A  ", "kota": "X"}])
        assert dirty.report.has_changes is True

    def test_missing_column_treated_as_empty(self):
        rows = [{"nama": "A"}]
        result = clean_rows(COLUMNS, rows)
        assert result.rows[0]["kota"] == ""


# ---------------------------------------------------------------------------
# Baca / tulis
# ---------------------------------------------------------------------------

class TestReadWrite:
    def test_read_csv(self, tmp_path):
        path = tmp_path / "a.csv"
        path.write_text("nama,kota\nBudi,Jakarta\n", encoding="utf-8")
        columns, rows = read_csv(path)
        assert columns == ["nama", "kota"]
        assert rows == [{"nama": "Budi", "kota": "Jakarta"}]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(CleanupError, match="tidak ditemukan"):
            read_csv(tmp_path / "nope.csv")

    def test_empty_file_raises(self, tmp_path):
        path = tmp_path / "empty.csv"
        path.write_text("", encoding="utf-8")
        with pytest.raises(CleanupError, match="kosong atau tanpa header"):
            read_csv(path)

    def test_utf8_bom_handled(self, tmp_path):
        path = tmp_path / "bom.csv"
        path.write_text("nama,kota\nA,X\n", encoding="utf-8-sig")
        columns, _ = read_csv(path)
        assert columns == ["nama", "kota"]

    def test_write_then_read_roundtrip(self, tmp_path):
        path = tmp_path / "out.csv"
        write_csv(path, ["nama", "kota"], [{"nama": "A", "kota": "X"}])
        with path.open(encoding="utf-8") as fh:
            assert fh.read() == "nama,kota\nA,X\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def tulis_kotor(tmp_path: Path) -> Path:
    path = tmp_path / "kotor.csv"
    path.write_text(
        "nama,kota\n  Budi  ,  Jakarta \nBudi,Jakarta\nSiti,-\n",
        encoding="utf-8",
    )
    return path


class TestCli:
    def test_dry_run_writes_nothing(self, tmp_path, capsys):
        src = tulis_kotor(tmp_path)
        before = src.read_text(encoding="utf-8")
        code = main([str(src), "--dedupe", "--dry-run"])
        assert code == 0
        out = capsys.readouterr().out
        assert "PREVIEW" in out
        # File sumber tidak berubah dan tidak ada file baru.
        assert src.read_text(encoding="utf-8") == before
        assert not (tmp_path / "kotor_clean.csv").exists()

    def test_writes_default_output(self, tmp_path):
        src = tulis_kotor(tmp_path)
        code = main([str(src), "--dedupe"])
        assert code == 0
        output = tmp_path / "kotor_clean.csv"
        assert output.exists()
        with output.open(encoding="utf-8") as fh:
            content = fh.read()
        assert "  Budi  " not in content
        assert content.count("Budi") == 1  # duplikat dibuang

    def test_custom_output_path(self, tmp_path):
        src = tulis_kotor(tmp_path)
        code = main([str(src), "-o", str(tmp_path / "hasil.csv")])
        assert code == 0
        assert (tmp_path / "hasil.csv").exists()

    def test_missing_input_returns_1(self, tmp_path, capsys):
        code = main([str(tmp_path / "nope.csv")])
        assert code == 1
        assert "Error" in capsys.readouterr().err

    def test_bad_dedupe_column_returns_1(self, tmp_path, capsys):
        src = tulis_kotor(tmp_path)
        code = main([str(src), "--dedupe-by", "tidak_ada"])
        assert code == 1
        assert "tidak ada" in capsys.readouterr().err

    def test_bad_trim_column_returns_1(self, tmp_path, capsys):
        src = tulis_kotor(tmp_path)
        code = main([str(src), "--trim-columns", "xyz"])
        assert code == 1
        assert "xyz" in capsys.readouterr().err

    def test_keep_nulls_preserves_tokens(self, tmp_path):
        src = tmp_path / "n.csv"
        src.write_text("nama,kota\nA,-\n", encoding="utf-8")
        main([str(src), "--keep-nulls", "-o", str(tmp_path / "o.csv")])
        with (tmp_path / "o.csv").open(encoding="utf-8") as fh:
            assert "A,-" in fh.read()