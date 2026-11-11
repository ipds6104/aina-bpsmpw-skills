---
name: pok-manager
description: >-
  Gunakan skill ini setiap kali ada pertanyaan atau kebutuhan memeriksa rincian anggaran Petunjuk Operasional Kegiatan (POK)
  BPS Kabupaten Mempawah (T.A. 2026 maupun T.A. 2027), mencari alokasi honor mitra, uang saku/transport lokal (translok),
  paket meeting/hotel, perjalanan dinas, belanja modal, membandingkan alokasi antar-tahun anggaran,
  atau saat menerima dokumen revisi POK baru untuk di-ingest dan dimutakhirkan ke knowledge base.
---

# 📑 Petunjuk Operasional Kegiatan (POK) Manager & Explorer

Skill ini membekali Aina dengan kapabilitas pencarian instan, audit rincian belanja, perbandingan alokasi multi-tahun (2026 vs 2027), serta otomasi pembaruan/ingest revisi dokumen POK SAKTI ke dalam repositori knowledge base.

---

## 1. Kapan Harus Mengaktifkan Skill Ini

Aktifkan skill ini ketika rekan kerja menanyakan hal-hal terkait anggaran:
1. **Pengecekan Alokasi Anggaran Kegiatan Tertentu**:
   - *"Berapa pagu kegiatan SPKRT 2027 di POK?"*
   - *"Ada alokasi untuk Susenas atau Sakernas tahun 2027 nggak?"*
   - *"Cek kode akun 521213 untuk Survei SEEA berapa honornya?"*
2. **Pencarian Komponen Biaya (Honor, Translok, Konsumsi, Perjadin)**:
   - *"Berapa standar honor petugas pencacahan SPKRT di POK?"*
   - *"Cek di POK ada anggaran narasumber atau rapat dinas di mana saja?"*
3. **Perbandingan Antar-Tahun Anggaran**:
   - *"Bandingkan pagu kegiatan 2903 (Harga) antara 2026 dan 2027"*
   - *"Kenapa total pagu 2027 turun dibanding 2026?"*
4. **Pembaruan atau Revisi POK Baru**:
   - Rekan kerja mengirimkan file PDF revisi POK (misal: revisi 1 POK 2027) dan meminta Aina mengupdate knowledge base.

---

## 2. Perintah CLI Resmi (`pok_tool.py`)

Gunakan helper script resmi di `data/custom-skills/pok-manager/scripts/pok_tool.py`:

```bash
# 1. Cari rincian anggaran / komoditas / survei tertentu (bisa filter tahun)
python3 data/custom-skills/pok-manager/scripts/pok_tool.py search "SPKRT"
python3 data/custom-skills/pok-manager/scripts/pok_tool.py search "translok" --year 2027
python3 data/custom-skills/pok-manager/scripts/pok_tool.py search "521213" --year 2027

# 2. Ringkasan Pagu Program & 16-17 Kegiatan
python3 data/custom-skills/pok-manager/scripts/pok_tool.py summary 2027
python3 data/custom-skills/pok-manager/scripts/pok_tool.py summary 2026

# 3. Bandingkan alokasi kegiatan 2026 vs 2027
python3 data/custom-skills/pok-manager/scripts/pok_tool.py compare
python3 data/custom-skills/pok-manager/scripts/pok_tool.py compare --kegiatan 2903

# 4. Ingest draf atau revisi POK baru dari file PDF
python3 data/custom-skills/pok-manager/scripts/pok_tool.py ingest --file "/path/to/revisi_pok.pdf" --year 2027 --rev "Revisi 1"
```

---

## 3. Peta Dokumen & Arsip Master

- **Dokumen POK 2027 Lengkap**: [`knowledge/universal/pok_bps_mempawah_2027.md`](../../knowledge/universal/pok_bps_mempawah_2027.md)
  * Berkas Master PDF: `knowledge/assets/DRAFT_RANCANGAN_POK_TA_2027.pdf`
  * Total Pagu: **Rp 7.693.676.000,-**
  * Program GG (Teknis): **Rp 3.730.139.000,-**
  * Program WA (Manajemen): **Rp 3.963.537.000,-**
  * Kegiatan SPKRT 2027 (Kegiatan 2903): **Rp 2.039.825.000,-**

- **Dokumen POK 2026 Lengkap**: [`knowledge/universal/pok_bps_mempawah_2026.md`](../../knowledge/universal/pok_bps_mempawah_2026.md)
  * Total Pagu: **Rp 9.292.276.000,-** (termasuk pelaksanaan lapangan masif SE2026).

---

## 4. Prosedur Penanganan Revisi POK (Two-Way Door)

Jika ada revisi POK baru dari Kemenkeu/SAKTI:
1. Simpan berkas PDF revisi baru ke `knowledge/assets/POK_BPS_Mempawah_<tahun>_<revisi>.pdf`.
2. Jalankan `python3 data/custom-skills/pok-manager/scripts/pok_tool.py ingest --file ... --year <tahun> --rev "<catatan>"`.
3. Validasi kerapian dengan `aina kb lint --auto-heal`.
4. Sinkronkan dan push perubahan ke GitHub repository `ipds6104/knowledge-base`.
