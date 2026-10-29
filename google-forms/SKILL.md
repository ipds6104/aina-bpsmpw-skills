---
name: google-forms
description: >-
  Gunakan skill ini untuk membuat Google Form baru, menambahkan berbagai tipe pertanyaan (pilihan ganda, isian singkat, paragraf, checkbox, dropdown, skala, tanggal), mengambil link form (responder & editor), serta mengunduh respon jawaban secara otomatis melalui Google Forms API v1.
---

# Google Forms API Integration Skill

Skill ini memberikan kemampuan bagi Aina untuk mengelola dan membuat formulir daring Google Forms langsung dari ruang obrolan melalui Google Forms API v1 resmi.

---

## 1. Kapan Mengaktifkan Skill Ini (Trigger Conditions)

Aktifkan skill ini setiap kali:
1. **Pembuatan Google Form**: Rekan kerja meminta dibuatkan formulir pendaftaran, survei, absensi, evaluasi, atau kuesioner Google Form.
2. **Penambahan Pertanyaan**: Menambahkan daftar pertanyaan, pilihan ganda, atau opsi jawaban ke Google Form yang sudah ada.
3. **Pemeriksaan Respon**: Mengunduh dan merekap jawaban yang telah diisi oleh responden.
4. **Pemeriksaan Status API**: Memeriksa kesiapan dan aktivasi Google Forms API di Google Cloud Project.

---

## 2. Kredensial & Autentikasi

Skill ini terintegrasi langsung dengan token OAuth Google terpusat (`ipds6104@gmail.com`):
- Memanfaatkan token refresh otomatis dari `gdrive_tool`.
- Menggunakan scope `https://www.googleapis.com/auth/drive` yang mencakup pengelolaan berkas form di Google Drive.
- **Prasyarat**: Google Forms API wajib diaktifkan pada Google Cloud Project `169071183041` melalui tautan konsol:
  `https://console.developers.google.com/apis/api/forms.googleapis.com/overview?project=169071183041`

---

## 3. Panduan Perintah Helper CLI (`google-forms_tool.py`)

Lokasi script: `data/custom-skills/google-forms/scripts/google-forms_tool.py`

### A. Cek Status Kesiapan API
```bash
python3 data/custom-skills/google-forms/scripts/google-forms_tool.py status
```
Menampilkan apakah API sudah aktif di GCP atau masih mengembalikan error `SERVICE_DISABLED`.

### B. Membuat Form Baru
```bash
python3 data/custom-skills/google-forms/scripts/google-forms_tool.py create \
  --title "Kuesioner Evaluasi SE2026" \
  --desc "Mohon mengisi data evaluasi kegiatan sensus ekonomi berikut ini."
```
Output mengembalikan:
- `form_id`: ID form Google
- `responder_url`: Tautan yang dibagikan ke responden untuk mengisi form
- `edit_url`: Tautan editor untuk pemilik/kolaborator form

### C. Menambahkan Pertanyaan ke Form
Format pertanyaan berupa array JSON atau file JSON:
```bash
python3 data/custom-skills/google-forms/scripts/google-forms_tool.py add-questions \
  --form-id "<FORM_ID>" \
  --json '[
    {"title": "Nama Lengkap", "type": "text", "required": true},
    {"title": "Instansi / Unit Kerja", "type": "text", "required": true},
    {"title": "Kecamatan Penugasan", "type": "dropdown", "options": ["Mempawah Hilir", "Sungai Pinyuh", "Sungai Kunyit", "Segedong", "Siantan", "Toho", "Anjongan", "Sadaniang", "Mempawah Timur"], "required": true},
    {"title": "Apakah ada kendala lapangan?", "type": "radio", "options": ["Tidak ada", "Ada kendala teknis", "Ada kendala responden"], "required": true},
    {"title": "Jelaskan kendala yang dialami", "type": "paragraph", "required": false},
    {"title": "Tingkat Kepuasan Koordinasi", "type": "scale", "low": 1, "high": 5, "low_label": "Sangat Buruk", "high_label": "Sangat Baik"}
  ]'
```

**Tipe Pertanyaan yang Didukung**:
- `text` / `short`: Isian singkat
- `paragraph`: Isian panjang / teks bebas
- `radio` / `multiple_choice`: Pilihan ganda (1 jawaban)
- `checkbox`: Pilihan kotak centang (bisa lebih dari 1)
- `dropdown`: Menu pilihan tarik-turun
- `scale`: Skala linier (1 s.d. 5 atau 1 s.d. 10)
- `date`: Isian tanggal

### D. Mengambil Struktur & Info Form
```bash
python3 data/custom-skills/google-forms/scripts/google-forms_tool.py get --form-id "<FORM_ID>"
```

### E. Memeriksa / Mengunduh Jawaban Responden
```bash
python3 data/custom-skills/google-forms/scripts/google-forms_tool.py responses --form-id "<FORM_ID>"
```

---

## 4. Validasi Sintaks
Pastikan setiap modifikasi script diuji dengan:
```bash
python3 -m py_compile data/custom-skills/google-forms/scripts/google-forms_tool.py
```
