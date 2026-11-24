# Changelog

Semua perubahan penting pada proyek ini didokumentasikan di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/) dan proyek ini
menganut [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-24

### Ditambahkan
- CLI `csv-cleanup` untuk membersihkan file CSV yang berantakan.
- Buang baris duplikat (`--dedupe`), juga per kolom tertentu (`--dedupe-by`).
- Rapikan spasi berlebih, termasuk ganti karakter tersembunyi (NBSP, tab,
  zero-width).
- Normalkan nilai kosong tak konsisten (`-`, `N/A`, `null`, ...) menjadi sel
  kosong (`--keep-nulls` untuk mematikan).
- Rapikan hanya kolom tertentu (`--trim-columns`).
- Mode preview (`--dry-run`) yang tidak menulis apa pun.
- Hasil ditulis ke file baru secara bawaan, bukan menimpa aslinya.
- Laporan jelas: berapa baris/sel yang diubah.
- 29 test otomatis dengan pytest.
- CI GitHub Actions pada Python 3.10–3.12, termasuk pemeriksaan build paket.