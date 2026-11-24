---
name: github-ops
description: >-
  Use this skill whenever you need to manage GitHub authentication, inspect or switch GitHub accounts
  (between ihkaru and ipds6104), synchronize tokens from Infisical Vault, or troubleshoot git push/pull/PR permissions.
---

# GitHub Multi-Account & Infisical Vault Management Skill

Skill ini mengatur tata kelola akun GitHub multi-identitas (`ihkaru` dan `ipds6104`), sinkronisasi token otomatis dari brankas terpusat **Infisical**, dan pergantian akun aktif (*account switching*) secara transparan untuk GitHub CLI (`gh`) maupun perintah `git` standar.

---

## 1. Kapan Mengaktifkan Skill Ini (Trigger Conditions)

Aktifkan skill ini ketika:
1. **Pergantian Akun GitHub**: Pengguna meminta beralih akun untuk push/PR (misal: *"Aina, switch ke akun ihkaru"* atau *"Gunakan akun ipds6104"*).
2. **Error Izin Git / GitHub**:
   - `Permission to ... denied to <user>` (Error 403 HTTP) saat git push.
   - Penolakan push workflow: `refusing to allow an OAuth App to create or update workflow .github/workflows/... without workflow scope`.
3. **Penyelarasan Kredensial**: Sesi token kedaluwarsa, server baru di-reboot/redeploy, atau token baru telah diperbarui di Infisical Vault.
4. **Pengecekan Status Otorisasi**: Memeriksa akun GitHub mana yang saat ini sedang aktif di container.

---

## 2. Kredensial GitHub di Infisical Vault

Kredensial disimpan secara aman di Infisical Vault (`https://secrets.dvlpid.my.id/api`, Project: `dev`):
- `GH_TOKEN_IHKARU` / `GH_USER_IHKARU`: Akun personal Bang Ihza (`ihkaru`), pemilik upstream repositori utama (memiliki izin push langsung ke repo seperti `ihkaru/sipedas`).
- `GH_TOKEN_IPDS6104` / `GH_USER_IPDS6104`: Akun institusi BPS Kabupaten Mempawah (`ipds6104`), pemilik fork repositori instansi.
- `GH_HOSTS_YML_BASE64`: Berkas konfigurasi multi-akun GitHub CLI siap pakai yang memuat kedua identitas sekaligus.

---

## 3. Perintah Resmi & Cara Penggunaan (Helper Tool)

Helper tool tersedia di:
`python3 data/custom-skills/github-ops/scripts/github_ops_tool.py <subcommand>`  
*(atau `.agents/skills/github-ops/scripts/github_ops_tool.py`)*

### A. Sinkronisasi Kredensial dari Infisical
Mengambil seluruh token GitHub dari Infisical dan memperbarui `~/.config/gh/hosts.yml` serta `/root/.git-credentials`:
```bash
python3 data/custom-skills/github-ops/scripts/github_ops_tool.py sync
```

### B. Melihat Akun yang Sedang Aktif (Status)
```bash
python3 data/custom-skills/github-ops/scripts/github_ops_tool.py status
# atau ringkas:
python3 data/custom-skills/github-ops/scripts/github_ops_tool.py whoami
```

### C. Beralih Akun (Switch Account)
Beralih akun aktif secara instan. Perintah ini otomatis memperbarui konfigurasi `gh` dan `git credential`:

```bash
# Beralih ke akun personal ihkaru (untuk push langsung ke upstream ihkaru/*):
python3 data/custom-skills/github-ops/scripts/github_ops_tool.py switch ihkaru

# Beralih ke akun instansi ipds6104 (untuk push ke fork ipds6104/*):
python3 data/custom-skills/github-ops/scripts/github_ops_tool.py switch ipds6104
```

---

## 4. Cara Beralih Akun Secara Manual (Native GitHub CLI & Git)

Bila ingin berpindah akun tanpa script pembantu:
1. Edit berkas `~/.config/gh/hosts.yml` pada baris `user` dan `oauth_token` sesuai akun yang diinginkan (nilai token masing-masing akun sudah tercatat di bawah blok `users:`).
2. Perbarui `/root/.git-credentials` agar perintah `git push` menggunakan user dan token tersebut:
   ```bash
   echo "https://<USERNAME>:<TOKEN>@github.com" > ~/.git-credentials
   chmod 600 ~/.git-credentials
   ```
3. Verifikasi dengan:
   ```bash
   gh auth status
   ```
