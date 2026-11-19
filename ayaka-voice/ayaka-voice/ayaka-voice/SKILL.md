---
name: ayaka-voice
description: >-
  Gunakan skill ini setiap kali ada permintaan untuk mengirim pesan suara, voice note (VN), menyuarakan teks perkenalan/pengumuman dengan kloning suara Kamisato Ayaka (RVC v2 / F5-TTS), atau saat memeriksa observabilitas dan telemetri performa sintesis suara.
---

# Ayaka Voice Synthesis & Observability (RVC v2 + Edge-TTS)

Skill ini mengatur tata cara pembuatan pesan suara (Voice Note WhatsApp) berbahasa Indonesia menggunakan kloning suara karakter Kamisato Ayaka (VA: Saori Hayami) via pipeline **RVC v2 (Retrieval-based Voice Conversion) + Edge-TTS**, lengkap dengan observabilitas dan telemetri.

---

## 1. Arsitektur & Parameter Kunci
- **Primary Engine**: RVC v2 (`infer_rvc_python` CPU-optimized)
  - **Model Weights**: `/app/workspaces/default/models/rvc/ayaka_jp_v2/ayaka-jp_e101.pth` (RVC v2, 48kHz, 101 epoch)
  - **Index File**: `/app/workspaces/default/models/rvc/ayaka_jp_v2/added_IVF4031_Flat_nprobe_1_ayaka-jp_v2.index` (IVF Faiss index)
  - **Pitch Estimator**: `pm` (Parselmouth / Praat, 100% CPU friendly, zero C++ build dependency)
  - **Indonesian Phonetic Front-End**: Edge-TTS (`id-ID-GadisNeural`)
- **Fallback Engine**: F5-TTS Indo V2 (`--engine f5_tts`)
- **Format Output**: Ogg Opus (48.000 Hz, mono, 32 kbps) — standar WhatsApp Voice Note.
- **Proteksi Host**: CPU dibatasi ketat ke 2 thread (`torch.set_num_threads(2)`) agar tidak membebani host ThinkStation P320.

---

## 2. Perintah Eksekusi Cepat (CLI)

### A. Sintesis & Langsung Kirim ke WhatsApp
```bash
python3 /app/data/custom-skills/ayaka-voice/scripts/voice_ayaka.py "<teks_bahasa_indonesia>" --to <sender_jid>
```
*Contoh*:
```bash
python3 /app/data/custom-skills/ayaka-voice/scripts/voice_ayaka.py "Halo Bang Ihza! Ada update baru terkait sistem kita." --to 6289625345646@s.whatsapp.net
```

### B. Pengaturan Pitch / Nada
Jika ingin nada lebih tinggi atau rendah (semitone):
```bash
python3 /app/data/custom-skills/ayaka-voice/scripts/voice_ayaka.py "<teks>" --pitch 2 --to <sender_jid>
```

### C. Sintesis Berkas Audio Saja (Tanpa Kirim Langsung)
```bash
python3 /app/data/custom-skills/ayaka-voice/scripts/voice_ayaka.py "<teks>" --output output/voice/nama_file.ogg
```

### D. Pemeriksaan Observabilitas & Telemetri
```bash
python3 /app/data/custom-skills/ayaka-voice/scripts/voice_ayaka.py --telemetry
```

---

## 3. Tata Kelola Telemetri & Log Diagnostik
1. **File Telemetri (JSON Lines)**: `/app/data/custom-skills/ayaka-voice/logs/telemetry.jsonl`
2. **File Log Eksekusi**: `/app/data/custom-skills/ayaka-voice/logs/voice.log`

---

## 4. SOP & Guardrails
1. **Kalimat Panjang (>30 Kata)**:
   - Jalankan dengan flag `--daemon` atau berikan respon awal cepat di WhatsApp agar pengguna tidak menunggu dalam kesunyian.
2. **Penyimpanan Persisten**:
   - Skrip dan log berada di `/app/data/custom-skills/ayaka-voice/` yang terikat ke volume Docker permanen, sehingga aman dari pembersihan saat redeploy container.
