---
name: file-seeker
description: >-
  Gunakan skill ini setiap kali ada permintaan mencari berkas, dokumen, buku, publikasi ilmiah, atau torrent di internet, menginspeksi metadata dan mirror Libgen/BitTorrent, serta mengunduh file secara headless/asinkron menggunakan engine libtorrent dan HTTP stream.
---

# File Seeker Skill (Multi-Source Internet File & Book Discovery)

Skill ini memberikan kemampuan kepada Aina untuk mencari, menginspeksi, dan mengunduh berbagai berkas dari internet (buku, dokumen, PDF, ePub, dataset, maupun berkas torrent/magnet) secara otomatis tanpa perlu membuka browser GUI interaktif.

Skill ini mengadopsi dan menyempurnakan engine BitTorrent modern (seperti yang digunakan pada `torrra` via `libtorrent`), dikombinasikan dengan multi-sumber katalog buku (Libgen / Shadow Libraries) dan scraper indexer publik non-interaktif (Bitsearch & Apibay).

---

## 1. Kapan Mengaktifkan Skill Ini (Trigger Conditions)

Aktifkan skill ini ketika:
1. **Pengguna Meminta Mencari File atau Buku di Internet**:
   - *"Aina, coba cari buku Disciplined Entrepreneurship Workbook"*
   - *"Cari jurnal / PDF tentang X di internet"*
   - *"Tolong cari file torrent untuk software / ISO / buku ini"*
2. **Pengguna Meminta Mengunduh File / Magnet Link**:
   - *"Aina, coba download magnet link ini"*
   - *"Download berkas torrent ini ke folder downloads/"*
3. **Pencarian Multi-Sumber Alternatif**:
   - Ketika link direct download biasa mati, cari hash MD5 atau magnet link alternatifnya.

---

## 2. Standard Operating Procedures (SOP) & Penggunaan Tool

Gunakan CLI resmi yang terletak di `data/custom-skills/file-seeker/scripts/file_seeker.py`:

### SOP 1: Mencari Buku & Dokumen Akademik (Libgen Catalog)
Mencari buku berdasarkan judul, pengarang, atau ISBN di katalog Libgen:
```bash
python3 data/custom-skills/file-seeker/scripts/file_seeker.py search-book "<kata_kunci_buku>" --limit 5
```
Output menyediakan: Judul, Pengarang, Tahun, Penerbit, Format (PDF/EPUB), Ukuran, Hash MD5, dan tautan info download.

### SOP 2: Mencari Berkas Torrent & Magnet Links
Mencari berkas umum, ISO, buku, atau media via indexer torrent publik (BitSearch & Apibay):
```bash
python3 data/custom-skills/file-seeker/scripts/file_seeker.py search-torrent "<kata_kunci>" --limit 5
```
Output menyediakan: Nama berkas, Info Hash, dan Magnet URI lengkap beserta tracker.

### SOP 3: Mengunduh Berkas Torrent Headless (`libtorrent`)
Mengunduh berkas langsung dari Magnet URI atau berkas `.torrent` lokal tanpa TUI/dialog interaktif:
```bash
python3 data/custom-skills/file-seeker/scripts/file_seeker.py download-torrent "<magnet_uri_atau_path_torrent>" --save-path "downloads" --timeout 120
```

### SOP 4: Mengunduh Berkas HTTP/HTTPS Langsung
Mengunduh berkas direct stream secara aman dengan progress chunking:
```bash
python3 data/custom-skills/file-seeker/scripts/file_seeker.py download-http "<url_langsung>" --out "downloads/<nama_file>"
```

---

## 3. Batasan Keamanan & Etika (Guardrails)
1. **Non-Interactive Environment**: Jangan pernah memanggil tool dengan antarmuka TUI interaktif (seperti Textual TUI pada `torrra` langsung) karena akan memblokir stdin dan memicu timeout. Gunakan selalu engine headless `file_seeker.py`.
2. **Tugas Panjang & Download Besar**: Bila berkas berukuran besar (>50 MB) atau proses download memakan waktu >10 detik, jalankan secara background (`IsDaemon: true` atau `nohup`) dan kirimkan update progres bertahap ke ruang chat pemohon.
3. **Anti-CAPTCHA Compliance**: Jangan pernah mencoba membypass atau menunggu CAPTCHA/Cloudflare Turnstile yang terpasang pada situs file-sharing. Gunakan jalur API resmi, mirror terbuka, atau magnet link.
