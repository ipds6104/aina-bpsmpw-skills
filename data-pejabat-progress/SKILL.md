---
name: data-pejabat-progress
description: >-
  Gunakan skill ini untuk memantau, menghitung, dan mentabulasi progress pemadanan data pejabat BPS Kabupaten Mempawah (6104)
  pada Google Spreadsheet 'Data Pejabat Mempawah 6104 - Pemadanan Pendapatan SE2026' (Sheet 'Data OPEN Match').
  Mendukung sinkronisasi tab 'Rekap_Progress_BKSDM' dengan FORMULA LIVE (otomatis berubah secara realtime saat sumber diupdate tiap 1 jam),
  Conditional Formatting pewarnaan visual otomatis di Google Sheets, kalkulasi per Instansi BKSDM (kolom AT), serta rendering screenshot dashboard visual.
---

# Data Pejabat Progress Skill (Monitoring Pemadanan Pejabat Mempawah 6104)

Skill ini memberikan kemampuan khusus bagi Aina untuk memantau dan mentabulasi perkembangan penugasan pemadanan data pejabat Pemerintah Kabupaten Mempawah pada kegiatan SE2026 berdasarkan lembar kerja Google Sheets resmi:
- **Spreadsheet**: `Data Pejabat Mempawah 6104 - Pemadanan Pendapatan SE2026`
- **Spreadsheet ID**: `1ZpwvQLXJUCwB5yqp7Y5mFMFv1JnHWw3WYP1ebcNsI1U`
- **Tab Sumber**: `Data OPEN Match` (di-update otomatis tiap 1 jam sekali)
- **Tab Tabulasi Hasil**: `Rekap_Progress_BKSDM` (Live Formula & Real-Time Auto-Updating)

---

## 1. Arsitektur Formula Live (Real-Time Auto-Updating)

Karena tab sumber `'Data OPEN Match'` diperbarui secara berkala (tiap 1 jam sekali), tab `'Rekap_Progress_BKSDM'` dibangun menggunakan **FORMULA ASLI GOOGLE SHEETS** (bukan angka statis), sehingga:
1. **Otomatis Berubah Sendiri (Zero Maintenance)**: Begitu data di `'Data OPEN Match'` bertambah atau status assignment berubah, angka di `'Rekap_Progress_BKSDM'` seketika terkalkulasi ulang di browser tanpa perlu mengeksekusi script.
2. **Conditional Formatting Dinamis**: Pewarnaan cell progress (hijau, kuning, oranye, merah) diterapkan menggunakan aturan *Conditional Formatting* Google Sheets (`addConditionalFormatRule`), sehingga warna otomatis menyesuaikan capaian persentase terbaru.

### Rumus & Formula yang Diterapkan:
- **Total Baris Target**: `=COUNTA('Data OPEN Match'!A2:A)`
- **Belum Diproses (Open/Draft)**: `=COUNTIF('Data OPEN Match'!BD:BD; "open") + COUNTIF('Data OPEN Match'!BD:BD; "draft")`
- **Sudah Diproses**: `=B6 - B8` (atau rumus COUNTIFS selain open & draft)
- **Persentase Progress**: `=B7 / B6` (Format persentase `0,00%`)
- **Per Instansi BKSDM**:
  - Target: `=COUNTIF('Data OPEN Match'!AT:AT; B{row})`
  - Selesai: `=COUNTIFS('Data OPEN Match'!AT:AT; B{row}; 'Data OPEN Match'!BD:BD; "<>"; 'Data OPEN Match'!BD:BD; "<>open"; 'Data OPEN Match'!BD:BD; "<>draft")`
  - Belum: `=C{row} - D{row}`
  - Progress: `=IF(C{row}>0; D{row}/C{row}; 0)`

---

## 2. Panduan Penggunaan CLI (`data_pejabat_progress_tool.py`)

Helper script resmi terletak di:
```bash
python3 data/custom-skills/data-pejabat-progress/scripts/data_pejabat_progress_tool.py <subcommand>
```

### SOP 1: Memeriksa Ringkasan Angka Progress (Terminal / Text)
```bash
# Ringkasan cepat ke layar:
python3 data/custom-skills/data-pejabat-progress/scripts/data_pejabat_progress_tool.py summary

# Output dalam format JSON untuk integrasi otomasi:
python3 data/custom-skills/data-pejabat-progress/scripts/data_pejabat_progress_tool.py summary --json
```

### SOP 2: Sinkronisasi Tab Sheet & Formula Live di Google Sheets
```bash
# Menulis ulang grid formula live dan conditional formatting jika diperlukan struktur baru:
python3 data/custom-skills/data-pejabat-progress/scripts/data_pejabat_progress_tool.py sync-sheet
```

### SOP 3: Generate Screenshot Dashboard Visual
```bash
# Simpan gambar dashboard PNG resolusi tinggi:
python3 data/custom-skills/data-pejabat-progress/scripts/data_pejabat_progress_tool.py screenshot -o output/progress_pemadanan_bksdm.png

# Generate dan langsung kirimkan ke chat WhatsApp pemohon:
python3 data/custom-skills/data-pejabat-progress/scripts/data_pejabat_progress_tool.py screenshot --send-wa "$SENDER_JID"
```
