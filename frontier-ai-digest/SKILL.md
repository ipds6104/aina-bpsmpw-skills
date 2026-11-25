---
name: frontier-ai-digest
description: >-
  Gunakan skill ini untuk memantau, merangkum, dan mempublikasikan paper riset AI frontier terbaru
  dari repositori 'LikeACloud7/awesome-frontier-ai-papers' ke Status WhatsApp Story (media gambar screenshot + caption 1-2 paragraf padat Problem-Solution).
  Mendukung anti-duplikasi otomatis via state tracker, pengambilan abstrak via ArXiv API,
  tangkapan layar HiDPI via Patchright browser-screenshot, serta integrasi scheduler harian.
---

# Frontier AI Papers Digest & WhatsApp Status Story Skill

Skill ini memungkinkan Aina secara mandiri (maupun dipicu oleh jadwal / scheduler) untuk mengurasi paper frontier AI terbaru dari lab-lab dunia (OpenAI, DeepMind, NVIDIA, Anthropic, Meta FAIR, Apple, Baidu, Qwen, dll.), mengekstrak intisari masalah dan solusinya, mengambil tangkapan layar beresolusi tinggi, dan mengunggahnya sebagai WhatsApp Status Story.

---

## 1. Kapan Mengaktifkan Skill Ini (Trigger Conditions)

Aktifkan skill ini ketika:
1. **Admin / Pengguna Meminta Status Paper AI**:
   - *"Aina, buatkan status WhatsApp tentang paper AI terbaru"*
   - *"Coba share salah satu paper dari repo frontier AI papers"*
   - *"Tolong ringkas paper X jadi status WA"*
2. **Pemicu Otomatis dari Scheduler Native**:
   - Scheduler harian mentrigger posting rutin status teknologi/riset AI.
3. **Pemeriksaan Daftar Paper Baru**:
   - Mengecek paper apa saja yang baru dirilis oleh lab AI frontier global.

---

## 2. Penggunaan CLI Tool (`frontier-ai-digest`)

Jalankan perintah menggunakan python atau symlink global `frontier-ai-digest`:

```bash
# 1. Menampilkan daftar paper terbaru dan statusnya ([NEW] vs [POSTED]):
frontier-ai-digest list

# 2. Mengambil metadata & abstrak paper baru berikutnya (format JSON untuk dianalisis agen):
frontier-ai-digest next

# 3. Pratinjau draf caption dan tangkapan layar tanpa memposting (Dry-Run):
frontier-ai-digest preview --index 1

# 4. Memposting status story ke WhatsApp secara langsung (otomatis ambil paper teratas yang belum dipost):
frontier-ai-digest post

# 5. Memposting paper tertentu dengan caption narasi kustom buatan Aina:
frontier-ai-digest post --index 1 --caption "*🔬 Frontier AI Paper Digest*..."

# 6. Menampilkan riwayat paper yang sudah pernah diposting:
frontier-ai-digest history
```

---

## 3. Integrasi Scheduler Otomatis

Untuk menjadwalkan postingan rutin setiap pagi hari (misal pukul 08:30 WIB):

```bash
aina schedule add \
  --title "Frontier AI Digest Status" \
  --type agent \
  --target "status@broadcast" \
  --when daily \
  --time "08:30" \
  --payload "Jalankan frontier-ai-digest post untuk mempublikasikan status paper AI frontier terbaru hari ini"
```

---

## 4. Arsitektur & Efisiensi Sistem

- **Zero Heavy Crawling**: Membaca tabel markdown mentah langsung dari GitHub (< 100 KB) tanpa mendownload dataset 54 MB.
- **Ultra-Fast Abstract**: Menggunakan endpoint REST ArXiv Atom API (< 300 ms) untuk paper ArXiv.
- **State Tracker Anti-Duplikasi**: Seluruh tautan paper yang sudah diposting dicatat permanen di `/app/data/frontier_ai_history.json`.
- **Viewport Optimal Mobile**: Menggunakan `browser-screenshot` pada resolusi 1080x1200 dengan jeda 2 detik dan Retina HiDPI scale.
- **Anti-Cloudflare Challenge & Zero Bad Screenshot Guarantee**: Dilengkapi verifikasi mandiri sebelum memposting status. Jika target web memicu Cloudflare bot challenge, paywall, atau CAPTCHA ("Just a moment...", "Security verification", 403), sistem otomatis menolak screenshot tersebut dan beralih ke engine perender kartu visual (Paper Digest Card) beresolusi tinggi (1080x1200 dark aesthetic) sehingga status yang diposting selalu bersih dan terbaca sempurna.
