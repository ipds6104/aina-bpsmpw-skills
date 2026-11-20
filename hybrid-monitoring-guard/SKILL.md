---
name: hybrid-monitoring-guard
description: >-
  Protokol wajib dan arsitektur pengamanan rekonsiliasi monitoring kegiatan sensus/survei (SPDT NTP, Susenas, Sakernas, SE2026, Pertanian, dll.) yang menggabungkan antara data sistem otomatis (tarikan live Fasih/Cerdas/web BPS ground-truth) dengan isian manual Google Spreadsheet oleh mitra/petugas lapangan. Wajib diaktifkan setiap kali merancang, membuat, merekapitulasi, atau mengonsolidasikan monitoring campuran (hybrid). Mencegah asumsi salah bahwa data manual identik dengan data sistem, mewajibkan edukasi risiko selisih data (discrepancy risk) kepada pembuat/rekan kerja, serta menegakkan arsitektur 3-tier: Live Raw Tab, Manual Input Tab, dan Reconciliation Audit Dashboard.
---

# Hybrid Monitoring Guard: Protokol Rekonsiliasi Sistem & Isian Manual

Skill ini mengatur tata kelola arsitektur, verifikasi faktual, dan mitigasi risiko ketika mengintegrasikan dua sumber data monitoring yang berbeda sifat dalam seluruh kegiatan sensus dan survei statistik:
1. **Sistem Ground-Truth Otomatis** (Tarikan berkala via script dari sistem resmi seperti Fasih, Cerdas, Web Entri, SBR System, dsb.).
2. **Lembar Monitoring Lapangan Mandiri** (Google Spreadsheet yang diisi langsung oleh mitra Pencacah/PPL, Pengawas/PML, atau staf organik).

---

## 1. Aturan Wajib Agen (Mandatory Operational Guardrail)

> [!IMPORTANT]
> **KEWAJIBAN EDUKASI RISIKO SELISIH KEPADA PENGGUNA**:
> Setiap kali ada rekan kerja, koordinator kegiatan, atau pimpinan yang meminta:
> 1. Menggabungkan data tarikan otomatis (Fasih/Cerdas) dengan isian manual Google Spreadsheet mitra.
> 2. Menghitung rincian mikro/subsektor dari sheet monitoring yang dicampur dengan angka submit sistem.
> 3. Membuat lembar monitoring campuran baru.
> 
> **AINA WAJIB SECARA PROAKTIF MENYAMPAIKAN RISIKO SELISIH (DISCREPANCY RISK)** kepada pembuat/pemohon sebelum atau bersamaan dengan penyajian solusi:
> - Jelaskan bahwa data sistem adalah *Ground Truth Server*, sedangkan isian mitra adalah *Self-Reported Lapangan*.
> - Peringatkan potensi *Pelaporan Asinkron (Lag Waktu)*: di sheet manual sudah diisi tapi di Fasih belum di-submit (atau sebaliknya).
> - Larang keras menggabungkan/menimpa data dalam satu sel/kolom yang sama tanpa kolom audit rekonsiliasi.

---

## 2. Mengapa Disparitas Data Selalu Terjadi? (The Nature of Hybrid Monitoring)

Dalam operasi statistik lapangan, disparitas antara sistem web dan spreadsheet manual bukan anomali kebetulan, melainkan konsekuensi alami dari dua proses yang berbeda ritme:

| Dimensi | Tarikan Otomatis Sistem (Fasih / Cerdas) | Isian Manual Lapangan (Google Sheets Mitra) |
| :--- | :--- | :--- |
| **Sifat Data** | *Hard Data / System Ground Truth* | *Soft Data / Self-Reported Estimate* |
| **Pembaruan** | Deterministik & realtime server (misal tarikan tiap 15 menit) | Bergantung kedisiplinan dan sinyal internet mitra di lapangan |
| **Granularitas** | Seringkali hanya di level petugas/wilayah (`OPEN`, `SUBMITTED`, `COMPLETED`) | Mampu mencakup rincian kustom (nama subsektor, komoditas, alasan drop) |
| **Penyebab Selisih** | Belum di-submit di web, masih mode draft, atau PML belum approve | Mitra menganggap wawancara selesai di kuesioner fisik, atau lupa update link sheet |

---

## 3. Standar Arsitektur 3-Tier Rekonsiliasi (Three-Tier Architecture)

Dilarang keras membiarkan skrip otomatis menembak atau menulis langsung ke lembar kerja yang sedang diedit oleh mitra secara bersamaan. Wajib terapkan pemisahan tiga lapis (*separation of concerns*):

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SPREADSHEET MONITORING                         │
├──────────────────────────┬───────────────────────┬──────────────────────┤
│   TIER 1: LIVE SYSTEM    │  TIER 2: INPUT MITRA  │ TIER 3: REKONSILIASI │
│     (Read-Only Lock)     │ (Editable Lembar PPL) │ (Dashboard Kontrol)  │
│                          │                       │                      │
│ • Sinkron PC/Server      │ • Diisi 29 PPL / PML  │ • Kolom Fasih Submit │
│ • Tarikan 15 Menit Sekali│ • Rincian Subsektor   │ • Kolom Monit Mitra  │
│ • OPEN / SUBMIT / COMPL  │ • Catatan Sampel Drop │ • GAP / SELISIH (Δ)  │
│ • Terkunci dari Mitra    │ • Status Lapangan     │ • Early Warning Flag │
└──────────────────────────┴───────────────────────┴──────────────────────┘
```

1. **Tier 1 (`Fasih_Live` / `System_Raw`)**:
   - Tab khusus yang hanya diperbarui oleh skrip otomasi backend/PC rumah.
   - Hak akses disetel *Protected Sheet* (hanya akun otomasi/admin yang bisa edit) agar formula dan datanya kebal dari ketidaksengajaan edit mitra.
2. **Tier 2 (`Input_Monit` / `Progress_Petugas`)**:
   - Tab kerja operasional mitra untuk mencatat hal-hal yang tidak ditangkap oleh agregasi Fasih (misal: rincian subsektor, jenis komoditas, alasan responden tidak eligible/ganti).
3. **Tier 3 (`Dashboard_Rekonsiliasi` / `Rekap_Kontrol`)**:
   - Dashboard analitik yang menyandingkan kedua data per petugas menggunakan rumus komparasi:
     ```excel
     =Fasih_Submit - Laporan_Mitra
     ```
   - Berikan *Conditional Formatting* pewarnaan otomatis:
     - 🟢 **Hijau (MATCH)**: Selisih = 0. Data sinkron sempurna.
     - 🟡 **Kuning (LAG INPUT MITRA)**: Fasih > Mitra. Dokumen sudah aman di web, tapi mitra belum sempat buka Google Sheet.
     - 🔴 **Merah (LAG SUBMIT FASIH)**: Mitra > Fasih. Mitra lapor sudah selesai banyak, tapi di Fasih belum ada submit. Perlu dorongan pengawas (PML) untuk segera submit kuesioner.

---

## 4. Taksonomi Selisih & Panduan Tindakan Mitigasi

Bila koordinator atau pimpinan melihat angka selisih pada rekap kontrol, berikan panduan tindak lanjut berbasis taksonomi berikut:

1. **Status `OVERREPORT_MANUAL` (Laporan Mitra > Sistem Fasih)**:
   - *Arti*: Mitra merasa bebannya sudah selesai di lapangan, tetapi di server Fasih statusnya masih `OPEN` atau belum di-upload.
   - *Tindakan Mitigasi*: Koordinator/PML mengingatkan PPL agar segera melakukan submit di aplikasi Fasih sebelum batas waktu penutupan (closing cut-off).
2. **Status `UNDERREPORT_MANUAL` (Sistem Fasih > Laporan Mitra)**:
   - *Arti*: Kuesioner sudah berhasil di-submit dan valid di server Fasih, namun mitra belum sempat mengisi lembar monitoring sheet.
   - *Tindakan Mitigasi*: Data aman. Minta mitra merapikan catatan subsektor di sheet saat ada waktu senggang tanpa mengganggu pencacahan.
3. **Status `PML_APPROVAL_PENDING` (`SUBMITTED` tinggi, `COMPLETED` rendah)**:
   - *Arti*: PPL sudah menyelesaikan seluruh tugasnya, namun kuesioner tertahan di tahap review Pengawas (PML).
   - *Tindakan Mitigasi*: Ingatkan PML terkait untuk segera memeriksa dan melakukan *Approve / Complete* di sistem Fasih.

---

## 5. Tooling Skrip Pembantu (`reconciliation_tool.py`)

Gunakan skrip pembantu resmi yang terpasang di direktori skill:
`python3 /app/data/custom-skills/hybrid-monitoring-guard/scripts/reconciliation_tool.py <subcommand>`

### Perintah Tersedia:
1. **Analisis Selisih Dua Sheet**:
   ```bash
   python3 /app/data/custom-skills/hybrid-monitoring-guard/scripts/reconciliation_tool.py audit \
     --fasih-sheet "<ID_SHEET_FASIH>" \
     --monit-sheet "<ID_SHEET_MONITORING>" \
     --key-column "Nama PPL"
   ```
2. **Beri Peringatan Resiko Ringkas (Format WhatsApp Siap Forward)**:
   ```bash
   python3 /app/data/custom-skills/hybrid-monitoring-guard/scripts/reconciliation_tool.py format-warning \
     --kegiatan "SPDT NTP 2026"
   ```

---

## 6. Template Komunikasi Risiko Siap Pakai di WhatsApp

Gunakan template komunikasi santun dan profesional berikut saat berbicara dengan rekan kerja / admin:

```text
Catatan Penting terkait Rekap Hybrid (Fasih + Monit):
Perlu diperhatikan yaa, data dari tarikan sistem Fasih adalah real-time ground truth server, sedangkan rincian subsektor di sheet monitoring adalah isian mandiri (self-reported) oleh teman-teman mitra di lapangan.

Pasti ada potensi lag/selisih waktu antara dokumen yang sudah selesai dicacah mitra dengan yang benar-benar sudah di-klik SUBMIT/COMPLETED di web Fasih. Rekap ini Aina sajikan berbasis data pencatatan monitoring lapangan terkini yaa 🙏
```
