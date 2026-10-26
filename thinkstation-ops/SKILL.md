---
name: thinkstation-ops
description: >-
  Use this skill whenever inspecting, monitoring, or executing operational tasks on the physical host server
  (Lenovo ThinkStation P320), such as checking host CPU/RAM/disk metrics, listing and restarting Docker containers,
  fetching container logs, or running privileged system commands via SSH and passwordless sudo.
---

# ThinkStation Ops Skill (Lenovo ThinkStation P320 Host Operations)

This skill enables Aina to bridge beyond container boundaries and administer the physical host server (**Lenovo ThinkStation P320**) securely via dedicated Ed25519 SSH keys and passwordless sudo (`NOPASSWD: ALL`).

---

## 1. When to Activate This Skill (Trigger Conditions)

Activate this skill immediately whenever:
1. **Pengguna Meminta Cek Status Fisik Host**:
   - *"Aina, cek beban CPU, RAM, atau sisa disk di ThinkStation"*
   - *"Gimana load server fisik saat ini?"*
2. **Pengguna Meminta Manajemen Docker Host**:
   - *"Aina, coba cek container apa aja yang lagi jalan di server"*
   - *"Coba liat log container OpenObserve / Whatsmeow / Coolify"*
   - *"Aina, tolong restart container X di server"*
3. **Eksekusi Perintah Sistem di Host**:
   - Menjalankan perintah diagnosis jaringan, restart service systemd di host, atau investigasi infrastruktur.

---

## 2. Strict OpSec & Safety Guardrails

> [!CAUTION]
> **ATURAN KEAMANAN & BATASAN SATU ARAH (ONE-WAY DOOR)**:
> 1. **Dilarang Menampilkan Private Key Mentah**:
>    Private key Ed25519 disimpan di brankas Infisical (`SERVER_SSH_PRIVATE_KEY`) dan dilindungi izin berkas `0600`. Jangan pernah mencetak isi private key ke chat WhatsApp!
> 2. **Tindakan Destruktif Wajib Konfirmasi**:
>    Melihat status, membaca log, dan cek ps bersifat aman (*two-way door*). Namun untuk perintah `docker stop`, `docker rm`, `systemctl reboot`, `reboot`, atau modifikasi berkas sistem host, Aina **WAJIB** meminta persetujuan eksplisit dari Admin/Companion terlebih dahulu.

---

## 3. Standard Operating Procedures (SOP)

### SOP 1: Memeriksa Status & Metrik Hardware Host
```bash
python3 data/custom-skills/thinkstation-ops/scripts/thinkstation_ops_tool.py status -m
```
Menampilkan ringkasan WhatsApp-friendly: Hostname, Uptime, Load Average, Jumlah Container Aktif, Penggunaan RAM, dan Sisa Disk Root (`/`).

### SOP 2: Memantau Seluruh Container Docker di Host
```bash
# Menampilkan seluruh container aktif (format ringkas)
python3 data/custom-skills/thinkstation-ops/scripts/thinkstation_ops_tool.py docker-ps -m

# Filter container berdasarkan nama / image (misal: 'openobserve', 'whatsmeow', 'coolify')
python3 data/custom-skills/thinkstation-ops/scripts/thinkstation_ops_tool.py docker-ps --filter whatsmeow -m

# Menampilkan seluruh container termasuk yang berhenti (stopped)
python3 data/custom-skills/thinkstation-ops/scripts/thinkstation_ops_tool.py docker-ps -a -m
```

### SOP 3: Memeriksa Log Container Host
```bash
python3 data/custom-skills/thinkstation-ops/scripts/thinkstation_ops_tool.py docker-logs <nama_container> --tail 50 -m
```

### SOP 4: Merestart Container di Host (Konfirmasi Terlebih Dahulu)
```bash
python3 data/custom-skills/thinkstation-ops/scripts/thinkstation_ops_tool.py docker-restart <nama_container>
```

### SOP 5: Menjalankan Perintah Arbitrer di Host
```bash
# Menjalankan perintah biasa
python3 data/custom-skills/thinkstation-ops/scripts/thinkstation_ops_tool.py exec "free -h"

# Menjalankan perintah dengan hak akses root/sudo
python3 data/custom-skills/thinkstation-ops/scripts/thinkstation_ops_tool.py exec "systemctl status coolify" --sudo
```

---

## 4. Helper Tool Command Reference

| Perintah | Opsi Tambahan | Deskripsi |
| :--- | :--- | :--- |
| `thinkstation_ops_tool.py status` | `-m` (Markdown) | Mengecek status koneksi SSH, load CPU, RAM, dan disk host. |
| `thinkstation_ops_tool.py docker-ps` | `-f <filter>`, `-a`, `-m` | Menampilkan daftar container Docker yang berjalan di ThinkStation. |
| `thinkstation_ops_tool.py docker-logs <nama>` | `--tail <N>`, `--grep <str>`, `-m` | Membaca log terbaru dari container Docker di host. |
| `thinkstation_ops_tool.py docker-restart <nama>` | - | Me-restart container Docker di host. |
| `thinkstation_ops_tool.py exec "<cmd>"` | `--sudo` | Menjalankan perintah terminal di host (opsional hak sudo). |
| `thinkstation_ops_tool.py ensure-auth` | - | Mengunduh private key dari Infisical dan mengonfigurasi SSH jika belum ada. |
