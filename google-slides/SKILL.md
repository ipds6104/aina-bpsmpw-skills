---
name: google-slides
description: >-
  Gunakan skill ini setiap kali pengguna meminta dibuatkan bahan tayang, paparan rapat, slide presentasi, atau Google Slides baru, merapikan/memperindah (enhance) deck yang sudah ada, mengekstrak palet warna dari website, membaca isi slide, mengganti teks secara online, mengekspor ke PDF, atau melakukan verifikasi visual slide (anti-overflow) via render thumbnail. Mendukung tata letak modern 16:9 widescreen, rounded-rectangle card layouts, per-slide icon integration (Icons8), auto-backup sebelum edit, dan integrasi penuh dengan Google Drive & Google Slides API resmi.
---

# Google Slides Architecture 2.0 (Design Principles, Card Layouts & Verification)

Skill ini memberikan kemampuan komprehensif bagi Aina untuk menyusun, merombak, memoles, dan memverifikasi kualitas visual presentasi **Google Slides** profesional secara otomatis langsung dari obrolan WhatsApp atau instruksi teks.

---

## 1. 7 Prinsip Ilmiah Desain Slide & Anti-Overflow (Berdasarkan Riset Standar Industri)

Berdasarkan hasil komparasi rekayasa presentasi modern (termasuk riset agent presentation skill, cognitive load theory, dan Google Slides API internals):

### 1. Prinsip Cognitive Load & 3-Second Scannability
- Penonton tidak dapat membaca teks panjang sambil mendengarkan pembicara secara bersamaan (*Redundancy Effect*).
- Setiap slide harus dapat dipahami substansinya dalam **3 detik**.
- Gunakan **Action Headlines** (judul bermakna konklusif) alih-alih judul kategori pasif.

### 2. Aturan 6x6 & Disiplin Baris Teks
- Maksimal **6 baris teks** per blok/kartu, maksimal **6 kata per baris** (total ~30–36 kata per slide).
- Hindari *paragraph dumps* (paragraf panjang tanpa jeda visual). Pecah menjadi kartu-kartu mandiri dengan *takeaway* jelas.

### 3. Adaptasi Aturan 10/20/30 (Tipografi & Skalabilitas)
- Judul Slide: **24–32 pt** Bold.
- Judul Kartu / Subjudul: **16–20 pt** Bold.
- Teks Badan (Body): **11–14 pt** Regular (Dilarang keras <10 pt karena tidak terbaca di proyektor/layar ponsel).
- Nomor Metrik / Statistik: **36–48 pt** Bold dengan kontras tinggi.

### 4. Blueprint Geometris Grid 16:9 (Canvas 10.0" × 5.625" / 720 × 405 pt)
Untuk menghindari tabrakan (*collision*) dan teks tumpah ke bawah (*downward text warping*), gunakan koordinat baku:
- **Safe Area Outer Margin**: Left/Right: `0.60"`, Top: `0.50"` (Title), Bottom: `0.50"`.
- **Title Box**: Left: `0.60"`, Top: `0.45"`, Width: `7.50"`, Height: `0.65"` (sisakan margin kanan agar tidak menabrak ikon aksen).
- **2-Column Grid**: Card Width `4.20"`, Height `3.80"`, Gap `0.30"` (Col 1: `0.60"`, Col 2: `5.10"`).
- **3-Column Grid**: Card Width `2.73"`, Height `3.80"`, Gap `0.30"` (Col 1: `0.60"`, Col 2: `3.63"`, Col 3: `6.66"`).
- **2×2 Grid (4 Kartu)**: Card Width `4.20"`, Height `1.75"`, Row 1 Top `1.25"`, Row 2 Top `3.20"`.
- **2×3 Grid (6 Kartu)**: Card Width `2.73"`, Height `1.75"`, Row 1 Top `1.25"`, Row 2 Top `3.20"`.

### 5. Anatomi Komponen Kartu (Card Anatomy) & Internal Padding
- Setiap kartu wajib memiliki container shape (*Rounded Rectangle*) dengan warna latar bersih (`#FFFFFF` atau tint lembut), garis batas halus (`#E2E8F0` tebal 1–1.5 pt).
- **Internal Padding**: Sisakan margin dalam minimal `0.20"–0.25"` dari tepi kartu agar teks tidak menyentuh garis batas.
- **Vertical Alignment**: Terapkan `contentAlignment: "TOP"` untuk kartu deskriptif, dan `"MIDDLE"` untuk kartu badge/metrik angka.

### 6. Perangkap Autofit Google Slides API & Budget Karakter
> [!WARNING]
> Google Slides REST API **menolak** pengaturan `autofitType` selain `NONE` (muncul error: *"Autofit types other than NONE are not supported"*). Selain itu, perintah `replaceAllText` otomatis mereset autofit kembali ke `NONE`.
> **Solusi Pasti**: Agen wajib melakukan **Character-Count Budgeting** secara deterministik:
> - Kartu 3 kolom: batas aman teks badan adalah **120–160 karakter**.
> - Kartu 2 kolom: batas aman teks badan adalah **200–280 karakter**.
> - Jika teks melebihi budget, ringkas kalimatnya alih-alih membiarkannya jebol ke bawah kartu.

### 7. Verifikasi Visual Wajib ("Render-and-Look" Loop)
Setiap kali selesai mengubah atau membuat slide, render thumbnail PNG via `slides_tool thumbnail --id <ID> --index <NUM>` dan periksa menggunakan `read_file` sebelum melaporkan ke pengguna.

---

## 2. Pilihan Tema Desain & Palet Warna (16:9 Widescreen)

Tersedia 5 tema warna modern:
- `navy` (*Default*): Biru korporat & slate modern (resmi dinas, rapat BPS, statistik).
- `emerald`: Hijau zamrud elegan (pertumbuhan, ekonomi, lingkungan, pertanian).
- `sunset`: Oranye hangat & terracotta (kreatif, sosialisasi santai, workshop).
- `slate`: Minimalis monokrom abu-abu & indigo (bersih dan to-the-point).
- `midnight`: Dark-mode (latar gelap teks biru langit, cocok untuk IT/sistem).

---

## 4. Standard Operating Procedures (SOP)

### SOP 1: Membuat Google Slides Baru (Dengan Card Patterns & Preview)
```bash
slides_tool create \
  --title "Judul Presentasi" \
  --subtitle "Subjudul / Tanggal" \
  --theme navy \
  --slides-json "workspace/slides_draft.json" \
  --share anyone \
  --role writer \
  --thumbnail
```
*Tipe slide yang didukung di JSON*:
• `cards`: Kartu berjejer (2–4 kartu) dengan judul kartu, deskripsi/poin, dan caption takeaway di bawahnya.
• `two_column`: Perbandingan dua kolom.
• `table`: Tabel data ringkas dengan header warna tema.
• `content`: Kartu teks utama dengan poin-poin padat.

### SOP 2: Memoles & Merapikan Deck yang Ada (`enhance`)
Menerapkan background konsisten, penyesuaian font, dan menambahkan ikon Icons8 otomatis di pojok slide konten:
```bash
slides_tool enhance \
  --url "https://docs.google.com/presentation/d/1BxiMVs.../edit" \
  --theme emerald \
  --icons \
  --verify
```
*Keamanan (Two-Way Door)*: Perintah ini otomatis membuat salinan cadangan bertanggal `[BACKUP YYYY-MM-DD]` di Google Drive sebelum slide disentuh.

### SOP 3: Verifikasi Visual Slide (The "Render-and-Look" Loop)

> [!IMPORTANT]
> **Filosofi Render-and-Look**: API `batchUpdate` Google Slides bersifat "buta" (blind execution)—ia mengembalikan status `200 OK` meskipun teks meluber keluar batas bawah (*overflow*), menabrak shape lain, atau menimpa tabel dummy template.
> Oleh karena itu, **SETIAP KALI** memodifikasi atau membuat slide, agen **WAJIB** merender slide ke PNG (`thumbnail`) dan melihat hasilnya dengan tool pembaca gambar (`read_file`) sebelum menyatakan tugas selesai!

```bash
# Render slide spesifik (misal slide 8)
slides_tool thumbnail --id "1fYkFSJo8W9uvyqj..." --index 8 --out "/tmp/slide_8.png"

# Render seluruh slide sekaligus ke direktori review
slides_tool thumbnail --id "1fYkFSJo8W9uvyqj..." --all --out-dir "/tmp/deck_review"
```

Setelah di-render, periksa gambar via `read_file` untuk mendeteksi:
1. **Vertical Overflow**: Teks judul atau paragraf yang melebihi batas bawah kartu/slide.
2. **Text Collision**: Judul multi-baris yang menabrak sub-judul atau teks pengantar di bawahnya.
3. **Ghost / Dummy Elements**: Tabel dummy, grafik bawaan template, atau watermark yang tertinggal di bawah teks baru.
4. **Spacing Proportions**: Jarak antar-kolom dan kartu yang seimbang.

### SOP 4: Pembersihan Elemen Dummy Template (`delete-element`)
Jika ditemukan tabel atau chart dummy bawaan template yang tertimpa teks:
```bash
slides_tool delete-element --id "1fYkFSJo8W9uvyqj..." --objects "table_id_1" "image_id_2"
```

### SOP 5: Ekstrak Brand Website (`brand-extract`)
Mengekstrak palet warna dominan dan Google Fonts dari website instansi:
```bash
slides_tool brand-extract --url "https://mempawahkab.bps.go.id"
```

### SOP 5: Mengganti Teks Slide Online Secara Realtime
```bash
slides_tool replace-text \
  --url "https://docs.google.com/presentation/d/1BxiMVs.../edit" \
  --find "Draf Awal" \
  --replace "Final Disetujui"
```

### SOP 6: Ekspor Slide ke PDF & Kirim ke WhatsApp
```bash
slides_tool export-pdf \
  --url "https://docs.google.com/presentation/d/1BxiMVs.../edit" \
  --out "workspace/paparan.pdf"

# Kirim ke WhatsApp
python3 skills/whatsmeow/scripts/wa_tool.py send-media \
  --to "<JID>" \
  --file "workspace/paparan.pdf" \
  --caption "Ini berkas PDF paparannya yaa!"
```
