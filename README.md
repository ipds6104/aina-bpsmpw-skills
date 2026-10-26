# Aina BPS Mempawah Custom Skills (`aina-bpsmpw-skills`)

Repositori terpusat untuk seluruh **Custom Skills** agen cerdas Aina yang dikhususkan bagi operasional teknis dan analitis **BPS Kabupaten Mempawah (6104)** serta pendukung infrastruktur lokal.

---

## 📦 Katalog Custom Skills

### 1. Khusus BPS Kabupaten Mempawah
* **`dokter-v`** (alias: `sipedas`): Protokol REST API lengkap untuk mengelola Sistem Manajemen Mitra Statistik (Dokter V), pembuatan alokasi honor mitra berbasis batas SBML bulanan, pencegahan bentrok sensus/survei, penerbitan otomatis SPK bulanan & BAST transaksi, simulasi pra-alokasi (*dry-run*), dan penelusuran riwayat mutasi / rollback audit log.
* **`data-pejabat-progress`**: Monitoring, kalkulasi, dan tabulasi progress pemadanan data pejabat BPS Kabupaten Mempawah untuk persiapan Sensus Ekonomi 2026. Mengintegrasikan live formula Google Sheets, sinkronisasi otomatis tiap jam, dan rendering visual screenshot progres BKSDM.
* **`se-data`**: Direktori dan protokol analitik terpusat Sensus Ekonomi 2026 (SE2026) menggunakan arsitektur dataset biner kolumnar Parquet dan DuckDB OLAP streaming tanpa membebani memori server.

### 2. Utilitas Operasional Host & Pendukung
* **`coolify-ops`**: Manajemen siklus hidup aplikasi, service, variabel lingkungan, deployment queue, dan sinkronisasi kredensial WhatsApp Gateway pada host server Coolify ThinkStation P320.
* **`thinkstation-ops`**: Pemantauan metrik perangkat keras host fisik (CPU, RAM, disk NVMe), inspeksi status container Docker, restart container, dan privileged remote execution.
* **`patchright-pdf`**: Engine konversi HTML/Web ke PDF resolusi tinggi berbasis Patchright headless Chromium dengan kemampuan stealth bypass, CSS print emulation, dan pengiriman otomatis ke WhatsApp.
* **`ayaka-voice`**: Voice note synthesis & voice cloning (Kamisato Ayaka) via RVC v2 / F5-TTS.

---

## 🚀 Prosedur Pemulihan / Restore (Deployment Baru)

Bila Aina dideploy pada container atau server baru, cukup jalankan perintah satu baris berikut untuk memulihkan seluruh custom skills:

```bash
git clone https://github.com/ipds6104/aina-bpsmpw-skills.git /app/data/custom-skills
```

Pastikan `.agents/skills.json` pada workspace mengarah ke `/app/data/custom-skills`:

```json
{
  "entries": [
    { "path": "/app/skills" },
    { "path": "/app/data/custom-skills" }
  ]
}
```

---

## 🔄 Sinkronisasi Pembaruan

Setiap kali ada penambahan atau pembaruan skill di `/app/data/custom-skills`:

```bash
cd /app/data/custom-skills
git add .
git commit -m "feat(skills): update custom skills"
git push origin main
```
