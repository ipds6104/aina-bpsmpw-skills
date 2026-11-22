---
name: agy-ttft
description: >-
  Gunakan skill ini setiap kali ingin mengukur, menganalisis, atau membandingkan Time To First Token (TTFT), latensi panggilan cloud murni, overhead bootstrap lokal AGY CLI, dan kecepatan throughput token dari model Gemini 3.8 Flash High (atau model lainnya) melalui AGY CLI.
---

# AGY CLI TTFT & Cloud Latency Profiler

Skill ini mengukur secara presisi metrik waktu respon model AI (khususnya keluarga **Gemini 3.8 Flash High / Medium / Low**) saat dipanggil via `agy` CLI, dengan pemisahan tegas antara **latensi lokal (CLI/sistem)** dan **latensi murni panggilan cloud (jaringan & inferensi model)**.

---

## 1. Arsitektur Pemisahan Waktu (Timing Breakdown)

Saat menjalankan `agy` CLI dalam mode streaming (`--output-format stream-json`), eksekusi terbagi menjadi fase-fase terpisah:

```text
[ t_proc_start ] ─── (1) Local CLI Overhead ───> [ t_cloud_dispatch ] ─── (2) Pure Cloud TTFT ───> [ t_first_token ] ─── (3) Stream Generation ───> [ t_response_done ]
      │                                                │                                                   │                                                  │
      └─ Bootstrap bin, runtime, plugins, input scan ──┴─ Request terkirim ke Google Cloud (user_input OK) ┴─ Token pertama mengalir kembali (text_delta) ───┴─ Stream selesai
```

1. **Local CLI Overhead**:
   - Selang waktu dari peluncuran biner `agy` hingga event `user_input DONE`.
   - Meliputi bootstrap runtime Go, pemuatan ekstensi/plugin, pembacaan konfigurasi sistem, dan persiapan payload input lokal.
2. **Cloud TTFT (Murni Cloud)**:
   - Selang waktu dari `user_input DONE` (saat request dipancarkan ke Google Cloud endpoint) hingga chunk `text_delta` pertama diterima dari server.
   - Mengukur murni latensi jaringan (RTT), antrian gateway, dan waktu inferensi/thinking awal server AI sebelum token pertama di-stream.
3. **End-to-End CLI TTFT**:
   - Total waktu dari start proses CLI hingga token pertama diterima (`Local Overhead + Cloud TTFT`).
4. **Streaming Duration & Throughput**:
   - Kecepatan streaming token (`output_tokens / streaming_duration`) setelah token pertama diterima.

---

## 2. Standard Operating Procedures (SOP)

### SOP 1: Memeriksa Kesiapan Tool & Daftar Model
```bash
python3 data/custom-skills/agy-ttft/scripts/agy-ttft_tool.py status
```

### SOP 2: Mengukur TTFT Gemini 3.8 Flash High (Single Run)
```bash
python3 data/custom-skills/agy-ttft/scripts/agy-ttft_tool.py measure --model gemini-3.8-flash-high
```
Opsi tambahan:
- `--prompt "<pertanyaan>"`: Menggunakan prompt kustom.
- `--format json`: Mengembalikan raw JSON terstruktur untuk otomasi/analisis script.

### SOP 3: Mengukur Rata-Rata TTFT (Multi-Run Benchmark)
Untuk mendapatkan angka statistik yang stabil (rata-rata, nilai min, dan nilai max):
```bash
python3 data/custom-skills/agy-ttft/scripts/agy-ttft_tool.py measure --model gemini-3.8-flash-high --runs 3
```

### SOP 4: Membandingkan TTFT Antar-Tingkat Model Flash
Membandingkan latensi cloud dan overhead antara `gemini-3.8-flash-low`, `gemini-3.8-flash-medium`, dan `gemini-3.8-flash-high`:
```bash
python3 data/custom-skills/agy-ttft/scripts/agy-ttft_tool.py compare
```

---

## 3. Catatan Teknis & Karakteristik Model
- **Reasoning / Thinking Tokens**: Model `gemini-3.8-flash-high` memiliki mode penalaran (*deep thinking*) aktif secara bawaan yang menghasilkan thinking tokens sebelum memancarkan teks jawaban. Hal ini membuat Cloud TTFT berada di kisaran ~3.5s – 4.0s (termasuk inferensi thinking internal cloud).
- **Perbandingan Tingkat Flash**:
  - `gemini-3.8-flash-low`: Thinking 0 tokens, Cloud TTFT sangat kilat (~1.5s – 1.8s).
  - `gemini-3.8-flash-medium`: Thinking ~40–50 tokens, Cloud TTFT seimbang (~2.2s – 2.5s).
  - `gemini-3.8-flash-high`: Thinking ~120+ tokens, penalaran mendalam, Cloud TTFT (~3.5s – 4.0s).
