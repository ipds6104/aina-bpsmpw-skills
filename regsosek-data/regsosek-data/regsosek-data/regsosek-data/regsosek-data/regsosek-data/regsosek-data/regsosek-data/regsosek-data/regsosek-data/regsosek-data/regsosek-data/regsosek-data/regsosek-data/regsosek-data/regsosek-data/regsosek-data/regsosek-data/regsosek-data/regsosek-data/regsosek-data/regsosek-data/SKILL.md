---
name: regsosek-data
description: >-
  Gunakan skill ini setiap kali ada pertanyaan, pencarian data mikro, tabulasi, atau analisis data Regsosek 2022 (Pendataan Awal Registrasi Sosial Ekonomi) Kabupaten Mempawah (6104), baik tingkat individu (ART) maupun rumah tangga (KK). Menggunakan engine DuckDB berkinerja tinggi terhadap dataset Parquet terpusat di shared_data/regsosek/.
---

# Regsosek 2022 Mempawah Microdata OLAP & Search Skill

Skill ini mengatur tata kelola, pencarian data mikro, dan analisis tabulasi resmi untuk data **Registrasi Sosial Ekonomi (Regsosek 2022)** Kabupaten Mempawah (6104).

---

## 1. Aturan Sumber Data & Kebijakan Penyimpanan Masif

> [!IMPORTANT]
> **Pemisahan Data Masif dari Git & Knowledge Base**:
> - Data mentah CSV Regsosek (>430 MB uncompressed) dan master Parquet **TIDAK DISIMPAN DI KNOWLEDGE BASE ATAU GIT**.
> - Seluruh berkas fisik disimpan secara persisten di:
>   `shared_data/regsosek/` (tertaut ke `/app/data/shared_data/regsosek/`).
> - Menggunakan format kolumnar **Parquet (ZSTD)** yang terkompresi dari 434 MB menjadi hanya ~24 MB, kebal listrik padam, dan mendukung kueri OLAP sub-detik dengan konsumsi RAM sangat rendah (<30 MB) via **DuckDB**.

---

## 2. Struktur Tabel & Dataset Parquet

Tersimpan di `shared_data/regsosek/`:

1. **`data_art_mempawah_labeled.parquet`** (View: `art` / `art_labeled`):
   - **Jumlah Baris**: 249.587 individu (ART).
   - **Ukuran**: 9,68 MB.
   - **Muatan**: Rincian demografi individu lengkap dengan label (nama ART, NIK, jenis kelamin, tanggal lahir, umur, status perkawinan, hubungan keluarga, pendidikan, ketenagakerjaan, kesehatan, kepemilikan usaha, dll).
2. **`data_kk_mempawah_labeled.parquet`** (View: `kk` / `kk_labeled`):
   - **Jumlah Baris**: 70.216 keluarga (KK).
   - **Ukuran**: 1,77 MB.
   - **Muatan**: Data perumahan, aset, dan karakteristik keluarga (nama kepala keluarga, no KK, jumlah ART, status bangunan, jenis lantai/dinding/atap, sumber air minum, sanitasi, sumber penerangan, bahan bakar memasak, aset, bantuan sosial, dll).
3. **`data_art_mempawah_full.parquet`** (View: `art_full`):
   - Master data ART dengan kode numerik mentah (92 kolom).
4. **`data_kk_mempawah.parquet`** (View: `kk_raw`):
   - Master data KK dengan kode numerik mentah (51 kolom).
5. **`Regsosek_2022_extract.zip` & `raw/*.csv`**:
   - Berkas arsip dan CSV asli tersimpan sebagai backup di direktori yang sama.

---

## 3. Cara Menggunakan Tool CLI (`regsosek-data_tool.py`)

Skrip resmi berada di:
`python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py <subcommand>`

### 1. Cek Status Dataset & Observabilitas
```bash
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py status
```

### 2. Pencarian Cepat Individu / Anggota Rumah Tangga (ART)
```bash
# Berdasarkan nama
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py search-art --nama "SITI" --kec "JONGKAT" --limit 10

# Berdasarkan NIK
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py search-art --nik "610208..."

# Berdasarkan No KK
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py search-art --no-kk "610208..."
```

### 3. Pencarian Cepat Keluarga (KK) & Karakteristik Rumah Tangga
```bash
# Berdasarkan nama kepala keluarga
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py search-kk --nama "MATNOH" --limit 5

# Berdasarkan No KK
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py search-kk --no-kk "6102082207110005"
```

### 4. Rekapitulasi Statistik Agregat
```bash
# Rekap jumlah KK dan ART per Kecamatan
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py rekap --by kecamatan

# Rekap desa di kecamatan tertentu
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py rekap --by desa --kec "Jongkat"

# Rekap status kepemilikan bangunan
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py rekap --by status_bangunan
```

### 5. Kueri SQL Bebas (DuckDB Engine)
View bawaan otomatis: `art`, `kk`, `art_full`, `kk_raw`.
```bash
# Format JSON (default)
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py query --sql "SELECT nama_kec, count(*) as jml_kk FROM kk GROUP BY nama_kec ORDER BY jml_kk DESC"

# Format Table (ramah terminal)
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py query --sql "SELECT nama_kec, count(*) as jml_kk FROM kk GROUP BY nama_kec" --format table
```

### 6. Ekspor Hasil Kueri ke Excel (.xlsx) atau CSV
```bash
python3 data/custom-skills/regsosek-data/scripts/regsosek-data_tool.py export \
  --sql "SELECT nama_art, nik, umur, jenis_kelamin_label, nama_desa FROM art WHERE lower(nama_kec) = 'jongkat' LIMIT 1000" \
  --output "output/sampel_regsosek_jongkat.xlsx"
```
File yang diekspor dapat langsung dikirim ke WhatsApp via:
`python3 skills/whatsmeow/scripts/wa_tool.py send-media --to <chat_jid> --file "output/sampel_regsosek_jongkat.xlsx" --caption "<keterangan>"`

---

## 4. Analisis Langsung via Python DuckDB

```python
import duckdb

con = duckdb.connect()
df = con.execute("""
    SELECT 
        nama_kec, 
        nama_desa, 
        count(*) as total_kk,
        sum(try_cast(jumlah_art as integer)) as total_art
    FROM 'shared_data/regsosek/data_kk_mempawah_labeled.parquet'
    GROUP BY nama_kec, nama_desa
    ORDER BY total_kk DESC
    LIMIT 20
""").fetchdf()
print(df)
```

---

## 5. Pedoman Kerahasiaan Data & Format WhatsApp

- **Perlindungan Data Pribadi (NIK & KK)**:
  Jangan pernah menampilkan daftar ratusan NIK/KK secara vulgar di grup WhatsApp umum. Jika rekan kerja membutuhkan daftar detail, ekspor ke file Excel privat.
- **Penyajian di Chat WhatsApp**:
  - Hindari tabel Markdown `| a | b |` (tabel hancur di layar HP).
  - Gunakan daftar butir ringkas: `• *Kecamatan*: Jumlah KK (Jumlah ART)`.
