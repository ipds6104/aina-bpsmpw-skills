---
name: course-deck-builder
description: >-
  Gunakan skill ini setiap kali ada permintaan merancang kurikulum, silabus, atau modul pembelajaran dari nol sampai tuntas berbasis ilmu kognitif & pedagogi (Learning Progression, CPA Sequence, Worked-Example Fading, Dual Coding) dan meng-generate hasilnya langsung menjadi slide presentasi web interaktif (guizang-ppt single-file HTML). Cocok untuk bahan ajar guru/dosen, pelatihan internal tim, workshop teknis, atau micro-learning.
---

# Pedagogical Course Deck Builder Skill

Skill ini mengintegrasikan **sains pembelajaran kognitif (Pedagogical Science)** dengan **arsitektur presentasi web modern (`guizang-ppt-skill`)** untuk secara otonom merancang kurikulum pembelajaran dari nol hingga mahir, lengkap dengan catatan pengajar (*speaker notes*), analogi konkret, pemodelan visual, studi kasus terurai, dan latihan retensi.

---

## 1. Kapan Mengaktifkan Skill Ini (Trigger Conditions)

Aktifkan skill ini ketika:
1. **Permintaan Modul / Kurikulum Belajar**:
   Pengguna berkata:
   - *"Aina, buatkan kurikulum / materi belajar X dari nol sampai mahir"*
   - *"Tolong rancang bahan ajar untuk topik Y"*
   - *"Bikinkan materi presentasi edukasi / modul training Z"*
2. **Permintaan Slide Presentasi Edukasi Berbasis Guizang**:
   Pengguna meminta bahan tayang presentasi pembelajaran berformat web interaktif (`guizang-ppt`).
3. **Penyusunan RPP / Instructional Design**:
   Dibutuhkan materi pengajaran yang memiliki urutan pedagogis bertahap (tidak melompat-lompat dan minim beban kognitif).

---

## 2. Kerangka Kerja Pedagogi 4-Tahap (Cognitive Architecture)

Modul ini mengadopsi 4 pilar dari riset kurikulum internasional (*Cognitive Load Theory, Dual Coding, CPA, Explicit Instruction*):

```text
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│ 1. Learning Progression│ ───> │ 2. CPA & Dual Coding   │ ───> │ 3. Worked Examples     │ ───> │ 4. Retrieval Practice  │
│ (Roadmap & Prasyarat)  │      │ (Konkret -> Visual ->  │      │ (Studi Kasus Lengkap + │      │ (Tantangan Mandiri &   │
│                        │      │  Abstraksi Formal)     │      │  Faded Scaffolding)    │      │  Teach-Back Challenge) │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

1. **Learning Progression & Scope**:
   - Memetakan tangga kompetensi prasyarat (*prerequisite*) secara vertikal agar pembelajar tidak bingung (*scaffolding ladder*).
2. **CPA Sequence (Concrete - Pictorial - Abstract)**:
   - *Concrete*: Dimulai dari fenomena fisik dunia nyata atau metafora analogi yang akrab di kehidupan sehari-hari.
   - *Pictorial*: Model visual, bagan alur, atau arsitektur diagram sistem (Dual Coding).
   - *Abstract*: Terminologi baku, definisi formal, dan sintaks kode terstruktur.
3. **Worked-Example Fading**:
   - Menyajikan studi kasus komprehensif langkah demi langkah (*worked example*), lalu menunjukkan titik rawan bingung (*common misconceptions & stuck points*).
4. **Retrieval Practice & Teach-Back**:
   - Soal tantangan aktif untuk menguji retensi jangka panjang tanpa membuka slide contekan.

---

## 3. Pilihan Gaya Visual Presentasi (`guizang-ppt`)

Skill ini langsung menghasilkan **satu berkas HTML mandiri (*single-file HTML*)** tanpa dependensi server:

| Gaya Visual | Basis Template | Karakteristik Desain | Cocok Digunakan Untuk |
| :--- | :--- | :--- | :--- |
| **`magazine`** *(Default)* | `assets/template.html` | Gaya majalah *Monocle*, font serif judul (Playfair/Noto Serif), fluid WebGL, nada hangat & intelektual. | Humaniora, konsep fundamental, pengenalan umum, workshop santai. |
| **`swiss`** | `assets/template-swiss.html` | *Swiss International Style*, font sans-serif (Inter/Helvetica), layout grid presisi, warna aksen kontras (IKB, Lemon). | Rekayasa perangkat lunak, sistem arsitektur, data science, materi teknis mendalam. |

---

## 4. Panduan Eksekusi CLI (`course-deck-builder`)

Lokasi script helper:
`/app/workspaces/default/data/custom-skills/course-deck-builder/scripts/course-deck-builder_tool.py`

### 1. Pengecekan Kesiapan Modul
```bash
python3 data/custom-skills/course-deck-builder/scripts/course-deck-builder_tool.py status
```

### 2. Generate Slide Deck Kurikulum Baru
```bash
# Contoh 1: Gaya Majalah (Editorial Magazine)
python3 data/custom-skills/course-deck-builder/scripts/course-deck-builder_tool.py generate \
  --title "Level Abstraksi di Computer Science" \
  --topic "Abstraksi Hardware, OS, hingga Cloud" \
  --level "Pemula hingga Menengah" \
  --style magazine \
  --theme indigo-porcelain

# Contoh 2: Gaya Swiss (Swiss Grid Style)
python3 data/custom-skills/course-deck-builder/scripts/course-deck-builder_tool.py generate \
  --title "Arsitektur Microservices & Event-Driven" \
  --topic "Event Sourcing dan CQRS" \
  --level "Lanjutan" \
  --style swiss \
  --theme ikb
```

### 3. Melihat Daftar Deck yang Pernah Dibuat
```bash
python3 data/custom-skills/course-deck-builder/scripts/course-deck-builder_tool.py list
```

---

## 5. Fitur Interaktif Presenter Mode

Setiap deck yang di-generate otomatis dilengkapi dengan:
- **Mode Presenter Interaktif (Tombol `P`)**: Membuka jendela pengajar terpisah berisi *timer*, naskah poin penting (*speaker notes*), preview slide berikutnya, dan kontrol layar audiens.
- **Navigasi Layar Sentuh & Keyboard**: Mendukung tombol panah `←` `→`, roda mouse, dan geser layar HP (*touch swipe*).
- **Ikhtisar Seluruh Slide (Tombol `ESC`)**: Menampilkan kisi grid seluruh modul untuk lompat cepat ke bab tertentu.
- **Validasi Nol Error**: Terverifikasi otomatis menggunakan `validate-presenter-mode.mjs` sebelum disampaikan ke pengguna.
