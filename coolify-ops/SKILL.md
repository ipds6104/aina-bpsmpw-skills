---
name: coolify-ops
description: >-
  Gunakan skill ini untuk mengelola seluruh siklus operasional aplikasi, services, environment variables,
  deployment, restart, dan pemantauan sistem Coolify di host server Lenovo ThinkStation P320.
  Mendukung resolusi dinamis aplikasi (berdasarkan nama, ID, atau UUID), pengelolaan konfigurasi buildtime/runtime,
  serta otomasi sinkronisasi kredensial (seperti WhatsApp Gateway Aina).
---

# Coolify Ops Skill (Universal Coolify Operations on ThinkStation P320)

Skill ini membekali Aina dengan kontrol penuh atas seluruh aplikasi, layanan (*services*), dan proyek yang di-deploy via **Coolify** pada server host **Lenovo ThinkStation P320**.

Dengan skill ini, pengelolaan variabel lingkungan, siklus rilis (build/deploy), pemantauan kontainer Docker, hingga pembacaan log dapat dilakukan secara universal untuk aplikasi apapun tanpa terbatas pada satu aplikasi tertentu.

---

## 1. Kapan Menggunakan Skill Ini (Trigger Conditions)

Aktifkan skill ini ketika:
1. **Inspeksi & Monitoring Aplikasi Coolify**:
   - Melihat daftar seluruh aplikasi yang terdaftar di Coolify (`apps`).
   - Memeriksa status kesehatan (*healthy/unhealthy*), container aktif, atau antrean rilis aplikasi apapun (`status --app <nama|id|uuid>`).
   - Melihat daftar layanan *one-click* seperti n8n, windmill, phpmyadmin (`services`) atau daftar proyek (`projects`).
2. **Tata Kelola Environment Variables**:
   - Menampilkan variabel lingkungan suatu aplikasi dengan masking nilai sensitif (`get-env`).
   - Menyetel atau memperbarui variabel build-time maupun runtime (`set-env`).
   - Menghapus variabel yang sudah tidak digunakan (`del-env`).
   - Sinkronisasi instan kredensial WhatsApp Gateway Aina ke aplikasi (`sync-aina-wa`).
3. **Pemicu & Pemantauan Deployment (CI/CD)**:
   - Memicu deployment atau *force rebuild* tanpa cache untuk aplikasi tertentu (`deploy`).
   - Memantau antrean build dan melihat log kompilasi rilis (`deployments` atau `logs --deployment`).
4. **Operasional & Troubleshooting Container**:
   - Membaca log runtime aplikasi (`logs --tail <N>`).
   - Merestart container aplikasi secara aman di host Docker (`restart`).

---

## 2. Resolusi Aplikasi Cerdas (Smart Identifier Resolution)

Flag `--app` mendukung pencarian cerdas otomatis tanpa perlu menghafal ID database:
- **Nama atau Kata Kunci**: `--app sipedas`, `--app aina`, `--app cerdas`, `--app cpns`, `--app fintr`
- **ID Numerik Database**: `--app 10`, `--app 25`, `--app 5`
- **Resource UUID Coolify**: `--app v7g6cdbkgsh4aa3xrqsb6u3g`

---

## 3. Panduan Penggunaan CLI (`coolify_ops_tool.py`)

Helper script resmi terletak di:
```bash
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py <subcommand>
```

### SOP 1: Navigasi & Pemeriksaan Daftar Sumber Daya
```bash
# Daftar seluruh aplikasi di Coolify:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py apps

# Filter aplikasi berdasarkan nama atau repository:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py apps --filter sipedas

# Daftar layanan one-click (services):
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py services

# Daftar project Coolify:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py projects
```

### SOP 2: Memeriksa Status & Kesehatan Aplikasi
```bash
# Ringkasan global Coolify & Docker host:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py status

# Status mendalam aplikasi tertentu (Coolify status, container Docker, & 3 deployment terakhir):
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py status --app sipedas
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py status --app aina
```

### SOP 3: Mengelola Variabel Lingkungan (Environment Variables)
```bash
# Lihat variabel lingkungan (nilai rahasia otomatis dimasking):
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py get-env --app sipedas

# Filter variabel tertentu (misal: DATABASE, REDIS, WHATS):
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py get-env --app sipedas --filter WHATS

# Tampilkan nilai sensitif tanpa masking:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py get-env --app sipedas --show-values

# Setel atau perbarui variabel:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py set-env --app sipedas LOG_LEVEL debug

# Setel variabel dan langsung trigger redeploy otomatis:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py set-env --app sipedas LOG_LEVEL info --redeploy

# Hapus variabel:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py del-env --app sipedas UNUSED_KEY
```

### SOP 4: Sinkronisasi WhatsApp Gateway Aina
Untuk menyuntikkan konfigurasi WhatsApp Gateway Aina (`WHATSAPP_PROVIDER=aina`, `WHATSMEOW_BASE_URL`, `WHATSMEOW_API_KEY`) ke aplikasi:
```bash
# Sinkronkan ke aplikasi sipedas (default):
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py sync-aina-wa

# Sinkronkan ke aplikasi lain dan langsung redeploy:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py sync-aina-wa --app <nama_app> --redeploy
```

### SOP 5: Memicu Deployment & Antrean Rilis
```bash
# Memicu deployment standar:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py deploy --app sipedas

# Memicu deployment dengan force rebuild (tanpa cache):
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py deploy --app sipedas --force-rebuild

# Melihat riwayat antrean deployment global atau spesifik aplikasi:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py deployments --limit 5
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py deployments --app sipedas --limit 5
```

### SOP 6: Log Observabilitas & Restart Container
```bash
# Ambil log runtime container aktif:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py logs --app sipedas --tail 100

# Ambil log proses build/deployment terakhir:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py logs --app sipedas --deployment --tail 50

# Restart container aplikasi di host ThinkStation:
python3 data/custom-skills/coolify-ops/scripts/coolify_ops_tool.py restart --app sipedas
```

---

## 4. Keamanan & OpSec
- Akses ke host server ThinkStation P320 menggunakan SSH key terenkripsi via Infisical.
- Masking otomatis diaktifkan pada pembacaan environment variables untuk melindungi token dan kunci API.
- Seluruh mutasi model Coolify dilakukan secara aman via Laravel Eloquent Tinker dan PostgreSQL resmi.
