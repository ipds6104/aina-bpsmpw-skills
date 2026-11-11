---
name: browser-screenshot
description: >-
  Gunakan skill ini untuk mengambil tangkapan layar (screenshot) berkualitas tinggi (HiDPI / Retina 2x) dari URL web apa pun,
  Google Sheets/Docs, dashboard SPA interaktif, maupun berkas HTML lokal menggunakan Patchright Chromium headless browser.
  Mendukung kustomisasi ukuran viewport, jeda rendering, scroll full-page, penangkapan elemen/selector spesifik,
  serta pengiriman otomatis via WhatsApp Gateway.
---

# Browser Screenshot Skill (Context-Agnostic Headless Browser)

Skill ini menyediakan utilitas pengambilan tangkapan layar (screenshot) serbaguna dan fleksibel berbasis **Patchright Chromium Headless Browser**. Dirancang untuk menangkap antarmuka web apa pun (Google Sheets live, portal berita, dashboard analitik, web internal/intranet) tanpa perlu menyusun ulang kode HTML.

---

## 1. Kapan Mengaktifkan Skill Ini (Trigger Conditions)

Aktifkan skill ini setiap kali:
1. **Pengguna Meminta Screenshot Web / Tautan / URL**:
   - *"Coba screenshot web ini dong"*
   - *"Tolong tangkap tampilan dashboard/halaman ini"*
   - *"Ambil screenshot Google Sheet ini terus kirim ke grup/DM"*
2. **Kebutuhan Tangkapan Layar Otomatis di Jadwal (Scheduler)**:
   - Rutinitas pemantauan visual berkala untuk dashboard metrik atau lembar kerja.
3. **Screenshot Elemen atau Full-Page Web**:
   - Menangkap seluruh halaman web panjang (*full page*) atau hanya tabel/grafik tertentu via selector.

---

## 2. Penggunaan CLI Tool (`browser-screenshot`)

Perintah utama dapat dijalankan via path skrip atau symlink global `browser-screenshot`:

```bash
# 1. Screenshot standar URL web (disimpan ke output/screenshot.png)
browser-screenshot https://example.com -o output/example.png

# 2. Screenshot Google Spreadsheet asli (otomatis deteksi canvas & HiDPI)
browser-screenshot "https://docs.google.com/spreadsheets/d/<ID>/edit#gid=<GID>" \
  --width 1360 --height 1200 --delay 4 -o output/gsheet.png

# 3. Screenshot dan langsung kirim ke WhatsApp (Grup atau DM)
browser-screenshot https://bps.go.id \
  -o output/bps.png \
  --send-wa "6289625345646@s.whatsapp.net" \
  --caption "Tangkapan layar portal BPS yaa"

# 4. Tangkapan layar seluruh halaman panjang (Full-Page)
browser-screenshot https://news.ycombinator.com --full-page -o output/hackernews.png

# 5. Tangkap elemen tertentu saja berdasarkan CSS Selector
browser-screenshot https://example.com --selector "#main-table" -o output/tabel.png
```

---

## 3. Opsi & Parameter Lengkap

| Parameter | Default | Keterangan |
| :--- | :--- | :--- |
| `url` | *(Wajib)* | URL target (`http://`, `https://`, atau path file HTML lokal) |
| `-o`, `--output` | `output/screenshot.png` | Jalur penyimpanan berkas gambar (PNG/JPEG) |
| `--width` | `1360` | Lebar viewport browser dalam piksel |
| `--height` | `900` | Tinggi viewport browser dalam piksel |
| `--scale` | `2` | Device Scale Factor untuk ketajaman HiDPI / Retina (anti-buram) |
| `--full-page` | `False` | Mengambil seluruh panjang halaman (*full-page scrolling*) |
| `--selector` | `None` | CSS selector elemen spesifik yang ingin ditangkap |
| `--wait-selector`| `canvas` *(khusus gsheet)* | Menunggu elemen tertentu muncul sebelum screenshot |
| `--delay` | `2.0` | Waktu tunggu (detik) setelah loading agar font/animasi stabil |
| `--timeout` | `30` | Batas waktu tunggu navigasi halaman (detik) |
| `--dark-mode` | `False` | Mengaktifkan emulasi prefers-color-scheme: dark |
| `--send-wa` | `None` | Nomor JID WhatsApp penerima gambar |
| `--caption` | `""` | Keterangan teks caption pengiriman WhatsApp |
