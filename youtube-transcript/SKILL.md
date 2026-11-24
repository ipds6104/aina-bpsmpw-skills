---
name: youtube-transcript
description: >-
  Gunakan skill ini untuk mengambil transkrip, subtitle, atau teks percakapan dari video YouTube,
  siaran live recording, maupun Shorts secara instan (< 2 detik) tanpa perlu login dan tanpa kuota API manual.
  Mendukung format teks mengalir (paragraf), teks dengan timestamp [MM:SS], serta penyimpanan langsung ke berkas teks/markdown.
---

# YouTube Transcript Extractor Skill

Skill ini memberikan kemampuan kepada Aina untuk mengekstrak transkrip atau subtitle resmi maupun otomatis (*auto-generated captions*) dari video YouTube secara instan.

---

## 1. Kapan Mengaktifkan Skill Ini (Trigger Conditions)

Aktifkan skill ini setiap kali:
1. **Pengguna Meminta Mengambil Transkrip Video YouTube**:
   - *"Aina, ambilin transkrip dari video youtube ini dong"*
   - *"Tolong ekstrak isi pembicaraan di link youtube ini"*
   - *"Ringkasin webinar/zoom di youtube ini"*
2. **Kebutuhan Analisis / Rangkuman Cepat Video Panjang**:
   - Mengekstrak teks untuk kemudian dirangkum intisari poinnya tanpa perlu memutar video.

---

## 2. Penggunaan CLI Tool

Jalankan skrip menggunakan Python atau symlink `youtube-transcript`:

```bash
# 1. Ambil transkrip teks biasa (plain text mengalir):
python3 /app/data/custom-skills/youtube-transcript/scripts/youtube_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# 2. Ambil transkrip lengkap dengan timestamp waktu [MM:SS]:
python3 /app/data/custom-skills/youtube-transcript/scripts/youtube_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" -f timestamp

# 3. Simpan langsung ke berkas Markdown:
python3 /app/data/custom-skills/youtube-transcript/scripts/youtube_transcript.py "https://youtu.be/VIDEO_ID" -o output/transkrip.md

# 4. Ambil transkrip dengan prioritas bahasa tertentu (misal Bahasa Indonesia lalu Inggris):
python3 /app/data/custom-skills/youtube-transcript/scripts/youtube_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" --lang id,en
```

---

## 3. Opsi CLI

| Argumen | Keterangan |
| :--- | :--- |
| `url` | URL video YouTube (youtube.com/watch?v=..., youtu.be/..., /live/..., /shorts/...) atau 11-digit Video ID |
| `-f`, `--format` | `text` (paragraf mengalir, default), `timestamp` (`[MM:SS] teks`), `json` (data terstruktur) |
| `-o`, `--output` | Path berkas tujuan penyimpanan |
| `--lang` | Prioritas bahasa dipisahkan koma (default: `id,en`) |
| `--max-chars` | Batas maksimum panjang karakter (0 = tanpa batas) |
