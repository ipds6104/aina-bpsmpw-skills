---
name: patchright-pdf
description: >-
  Gunakan skill ini untuk mengonversi halaman web atau dokumen HTML menjadi berkas PDF berkualitas tinggi (setara Ctrl + P / Print to PDF) menggunakan Patchright stealth Chromium headless browser. Mendukung bypass anti-bot/Cloudflare, CSS print emulation, pengaturan margin/ukuran kertas (A4, Letter, dsb.), jeda render SPA, dan pengiriman otomatis ke WhatsApp.
---

# Patchright Web-to-PDF Skill

Skill ini menyediakan utilitas cetak halaman web ke format PDF berkualitas tinggi berbasis **Patchright** (stealth fork Playwright). Dirancang khusus untuk skenario pencetakan otomatis (*Save as PDF* / `Ctrl + P`) dengan emulasi media cetak (`@media print`), rendering latar belakang lengkap, dan ketahanan terhadap proteksi bot/Cloudflare.

---

## 1. Kapan Mengaktifkan Skill Ini (Trigger Conditions)

Aktifkan skill ini setiap kali:
1. **Pengguna Meminta Cetak Web / Halaman ke PDF**:
   - *"Tolong simpan halaman web ini ke PDF dong"*
   - *"Bisa print to PDF URL ini?"*
   - *"Coba cetak halaman X pakai Ctrl+P terus kirim PDF-nya ke sini"*
2. **Kebutuhan Bypass Bot / Cloudflare Turnstile Saat Cetak Dokumen**:
   - Mengambil laporan atau halaman dari situs yang memblokir headless browser standar.
3. **Konversi Berkas HTML Lokal ke PDF**:
   - Menghasilkan PDF dari file HTML lokal yang memiliki styling CSS cetak atau tabel rumit.

---

## 2. Perintah CLI Utama (`patchright-pdf`)

Utilitas ini terpasang secara global di sistem dan dapat dipanggil langsung dari terminal:

```bash
# Penggunaan dasar
patchright-pdf <URL_ATAU_FILE_HTML> -o <NAMA_FILE.pdf>

# Contoh: Cetak web ke A4 dan simpan ke workspace
patchright-pdf https://bps.go.id -o output/bps.pdf

# Contoh: Cetak dengan jeda 2 detik (untuk SPA/grafik interaktif)
patchright-pdf https://dashboard.example.com -o output/dashboard.pdf --delay 2

# Contoh: Cetak orientasi landscape tanpa background
patchright-pdf https://example.com -o output/report.pdf --landscape --format A4

# Contoh: Cetak dan langsung kirimkan ke chat WhatsApp pemohon
patchright-pdf https://target-web.com -o output/dokumen.pdf --send-wa "$SENDER_JID" --caption "Ini dokumen PDF yang diminta yaa"
```

---

## 3. Opsi & Parameter Lengkap

| Parameter | Default | Keterangan |
| :--- | :--- | :--- |
| `url` | *(Wajib)* | URL web (`https://...`) atau path file HTML lokal |
| `-o`, `--output` | `output.pdf` | Lokasi berkas PDF hasil render |
| `--format` | `A4` | Ukuran kertas: `A4`, `Letter`, `Legal`, `A3`, `A5`, `Tabloid` |
| `--landscape` | `False` | Orientasi horizontal (landscape) |
| `--no-print-css` | `False` | Matikan emulasi CSS print (gunakan tampilan layar/screen biasa) |
| `--no-background` | `False` | Jangan cetak warna/gambar background |
| `--margin` | `1cm` | Margin seluruh sisi (contoh: `0.5cm`, `15px`) |
| `--wait-until` | `networkidle` | Kondisi selesai muat: `networkidle`, `load`, `domcontentloaded` |
| `--delay` | `0.0` | Jeda detik ekstra sebelum print (berguna untuk chart/animasi) |
| `--wait-selector` | `None` | Menunggu selector CSS spesifik sebelum print |
| `--scale` | `1.0` | Skala rendering halaman (0.1 - 2.0) |
| `--send-wa` | `None` | WhatsApp JID tujuan untuk langsung mengirim berkas |
| `--caption` | `""` | Teks keterangan bila dikirim ke WhatsApp |

---

## 4. Keunggulan Teknis & Anti-Bot Stealth

- **1:1 Playwright API**: Menggunakan library resmi `patchright` dengan stealth patching pada driver protocol CDP.
- **Headless Mode Native**: Menggunakan protokol internal Chromium `Page.printToPDF` yang cepat dan bebas dialog OS print yang memblokir.
- **Persistent Environment**: Script tersimpan di `/app/data/custom-skills/patchright-pdf/` dan terhubung persisten ke Docker volume.
