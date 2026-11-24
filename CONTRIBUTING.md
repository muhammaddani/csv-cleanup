# Contributing

Terima kasih atas minatmu!

## Menjalankan proyek secara lokal

```bash
git clone https://github.com/muhammaddani/csv-cleanup.git
cd csv-cleanup
python tasks.py install
python tasks.py test
python tasks.py demo
```

## Alur kontribusi

1. Buat branch baru: `git checkout -b feat/nama-fitur`
2. Tulis kode dan **tambahkan test** untuk perubahan tersebut.
3. Pastikan semua test lulus: `python tasks.py test`
4. Commit dengan pesan yang jelas (lihat gaya di bawah).
5. Buka Pull Request.

## Gaya commit

- `feat: ...` — fitur baru
- `fix: ...` — perbaikan bug
- `docs: ...` — perubahan dokumentasi
- `test: ...` — menambah atau memperbaiki test
- `chore: ...` — pekerjaan rumah tangga

## Prinsip

- **Aman secara bawaan:** jangan pernah menimpa file input tanpa diminta
  eksplisit. Mode `--dry-run` harus selalu benar-benar tidak menulis.
- Logika pembersihan berada di `cleaner.py` sebagai fungsi murni tanpa efek
  samping; CLI (`cli.py`) hanya mengatur input/output.
- Setiap perubahan perilaku harus disertai test.
- Jaga agar alat tetap hanya memakai standard library.