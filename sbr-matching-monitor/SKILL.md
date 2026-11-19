---
name: sbr-matching-monitor
description: >-
  Gunakan skill ini untuk memantau, merekapitulasi, dan merender tangkapan layar (screenshot) visual live
  progress matching prelist SBR SE2026 BPS Kabupaten Mempawah (6104) langsung dari Google Spreadsheet 'Lembar Kerja Matching SBR SE2026'.
  Mendukung capture screenshot tampilan Google Sheet asli via Patchright Chromium, pengiriman berkala ke WhatsApp,
  formula verifikasi otomatis, serta sinkronisasi identitas pengusaha/NIK dari Parquet SE2026.
---

# SBR Matching Monitor Skill (BPS Kabupaten Mempawah 6104)

Skill ini memberikan kemampuan terpadu bagi Aina untuk mengawal dan memonitor proses pemadanan (*matching & cleaning*) temuan anomali prelist SBR SE2026 di BPS Kabupaten Mempawah langsung dengan antarmuka Google Sheet yang familiar.

---

## 1. Referensi Berkas & Lembar Kerja

1. **Lembar Kerja Matching & Monitoring (Action Sheet)**:
   - **Spreadsheet ID**: `1tgXYr4dagc4LlDffJXNu7Q389uGh_HDBQWrMleTv2FA`
   - **Tab Monitoring**: `Rekap Monitoring` (Live formula realtime, GID: `393620021`)
   - **6 Tab Temuan**:
     - `Duplikat Usaha SBR` (17 kasus)
     - `NIK Duplikat >3 Usaha` (211 kasus)
     - `Nama Usaha Tanpa Bracket` (487 kasus)
     - `Alamat <5 Karakter` (8 kasus)
     - `Nama Usaha Umum` (487 kasus)
     - `Nama Usaha <5 Karakter` (16 kasus)

2. **Master Referensi Seluruh Usaha (Reference Sheet)**:
   - **Spreadsheet ID**: `1SYCQ1_nVUhnQ_9kopVnUaSvNJTz6yvf3uMl4DCjFxJQ`
   - **Tab Acuan**: `Semua Usaha (20 Okt)` (40.907 baris lengkap dengan Kolom AL: Nama Pemilik Usaha & Kolom AM: NIK Pemilik Usaha).

---

## 2. Penggunaan CLI Tool (`sbr_monitor_tool.py`)

Skrip utama berada di:
`data/custom-skills/sbr-matching-monitor/scripts/sbr_monitor_tool.py`

### 1. Cetak Ringkasan Singkat (Summary):
```bash
python3 data/custom-skills/sbr-matching-monitor/scripts/sbr_monitor_tool.py summary
```

### 2. Render Tangkapan Layar (Screenshot) Langsung Google Sheet:
```bash
python3 data/custom-skills/sbr-matching-monitor/scripts/sbr_monitor_tool.py screenshot -o output/rekap_monitoring_sbr.png
```

### 3. Render & Langsung Kirim ke WhatsApp Grup / DM:
```bash
python3 data/custom-skills/sbr-matching-monitor/scripts/sbr_monitor_tool.py screenshot --send-wa 120363433281094659@g.us
```

---

## 3. Jadwal Rutin Harian (Scheduler)

Telah didaftarkan jadwal otomatis di Aina Scheduler:
- **ID Tugas**: `#80` (*Monitoring Harian Matching SBR SE2026*)
- **Waktu**: Setiap hari pukul 07:00 WIB (s.d. 11 Desember 2026)
- **Target**: Grup WhatsApp `120363433281094659@g.us`
- **Mekanisme**: Membuka langsung Google Sheet via Patchright Chromium, mengambil screenshot tampilan grid live, dan mengirimkannya ke WhatsApp.
