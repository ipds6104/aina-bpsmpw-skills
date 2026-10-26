---
name: dokter-v
description: >-
  Gunakan skill ini setiap kali berinteraksi dengan sistem Dokter V BPS (Sistem Informasi Manajemen Mitra, Alokasi Honor, SPK & BAST),
  seperti mengelola alokasi honor mitra statistik, simulasi pra-alokasi SBML (dry-run), pengecekan bentrok jadwal survei/sensus,
  pencarian dokumen Kontrak Kerja (SPK) dan BAST, serta audit log rollback.
---

# SYSTEM DIRECTIVE & API SPECIFICATION: DOKTER V BPS INTEGRATION PROTOCOL

Skill ini membekali Aina dengan protokol lengkap untuk mengelola alokasi honor mitra statistik serta penerbitan dan pengecekan dokumen Kontrak Kerja (**SPK**) dan Berita Acara Serah Terima (**BAST**) pada sistem **Dokter V** (Sistem Manajemen Mitra & Alokasi Honor BPS Kabupaten Mempawah).

Gunakan panduan instruksi, aturan bisnis, efisiensi token, dan spesifikasi REST API di bawah ini untuk berinteraksi dengan sistem secara deterministik, presisi, dan aman.

---

## 1. KREDENSIAL API & KONEKSI SISTEM

Sistem ini menggunakan autentikasi berbasis REST API Key (Murni HTTP, Bukan MCP):

- **Base Endpoint URL**: `https://admin.dvlpid.my.id/api/v1`
- **Kredensial API Key**: Tersimpan aman di **Infisical Vault** (`DOKTER_V_API_KEY`, dengan alias `SIPEDAS_API_KEY`)
- **Nama Kunci Agen**: `Aina`
- **Pemilik Akun**: `Ihza Fikri Zaki Karunia, S.Tr.Stat.` (`ihzakarunia@bps.go.id`)
- **Tahun Anggaran Berjalan**: `2026`

### Header HTTP Wajib pada Setiap Permintaan:
Setiap pemanggilan HTTP (GET, POST, DELETE) WAJIB menyertakan header berikut:
```http
X-API-KEY: <DOKTER_V_API_KEY>
Content-Type: application/json
Accept: application/json
User-Agent: Aina-DokterV/1.0 (compatible; BPS Mempawah Integration)
```

> [!CAUTION]
> **STRICT OPSEC**: Dilarang membocorkan nilai API key mentah ke chat WhatsApp atau layar log. Gunakan selalu `dokter_v_tool` yang otomatis menginjeksi kredensial via Infisical/environment.

---

## 2. ARSITEKTUR DOMAIN & ATURAN BISNIS MUTLAK (HARD RULES)

Pahami hubungan antar-entitas di Dokter V sebelum memanggil endpoint mutasi:
1. **KegiatanManmit**: Master kegiatan BPS (contoh: Survei Angkatan Kerja Nasional, Survei Biaya Hidup, Sensus Pertanian). Memiliki jenis `SURVEI` atau `SENSUS` serta rentang tanggal pelaksanaan.
2. **Honor**: Posisi/jabatan tugas dalam suatu kegiatan (contoh: Petugas Pencacah Lapangan / PML, Pengawas Lapangan, Petugas Editing/Coding). Memiliki atribut `harga_per_satuan`, `satuan_honor` (misal: Dokumen, Rumah Tangga, Responden), serta tanggal mulai dan akhir kegiatan.
3. **Mitra**: Petugas mitra eksternal BPS yang terdaftar dengan ID Sobat (`id_sobat`), NIK, dan Nama. Setiap mitra memiliki relasi kemitraan tahunan (`Kemitraan`).
4. **AlokasiHonor**: Hubungan antara `Mitra` dan `Honor` dengan volume `target` (`total_honor = target * harga_per_satuan`).
5. **NomorSurat (SPK & BAST)**:
   - **Kaidah Otomasi**: Dokumen SPK dan BAST BUKAN entitas yang Anda buat secara manual atau terpisah! Saat Anda membuat `AlokasiHonor`, sistem secara otomatis menerbitkan dokumen SPK dan BAST serta menyematkan nomor resminya.
   - **SPK Survei Terkonsolidasi**: Jika jenis kegiatan adalah `SURVEI`, sistem akan menggunakan kembali (*reuse*) nomor SPK yang sudah ada untuk mitra tersebut di bulan yang sama (1 SPK per bulan per jenis survei).
   - **BAST Individual**: BAST selalu dibuat unik per transaksi alokasi honor.
6. **Kaidah Tautan Cetak Dokumen (SOP URL Cetak)**:
   - **Tautan Cetak SPK (Kontrak Bulanan)**: Gunakan tautan bersih TANPA parameter `id_kegiatan_manmit`:
     `https://<domain>/cetak/kontrak?tahun={tahun}&bulan={bulan}&mitra_id={mitra_id}`
     *(Alasan: 1 SPK adalah konsolidasi seluruh kegiatan survei mitra di bulan tersebut. Jika ditambahkan filter kegiatan, lampiran kegiatan lain mitra di bulan yang sama akan terpotong).*
   - **Tautan Cetak BAST**: Menggunakan filter kegiatan karena BAST bersifat spesifik per alokasi/kegiatan:
     `https://<domain>/cetak/bast?tahun={tahun}&bulan={bulan}&id_kegiatan_manmit={id_kegiatan}&mitra_id={mitra_id}`

### 5 Aturan Validasi Ketat (Penyebab Error 403 / 422 jika Dilanggar):
1. **Otorisasi Mutlak Anggota Grup Tim Kerja Mempawah (Strict Group Whitelist)**:
   - **HANYA nomor/akun WhatsApp yang terdaftar di grup Tim Kerja Mempawah (`120363253842861469@g.us`) atau Admin yang berhak meminta Aina mengeksekusi operasi Dokter V** (alokasi honor, cek SBML, buat/edit SPK & BAST, rollback, rename kegiatan, update kontak mitra).
   - Jalankan verifikasi pengirim via: `dokter_v_tool check-access --sender "$SENDER_JID"`.
   - **Jika Ditolak (`allowed: false`)**: Tolak secara santun bahwa kewenangan akses Dokter V dibatasi untuk anggota Tim Kerja Mempawah, dan arahkan pemohon untuk berkoordinasi dengan PIC Tim Teknis (Bang Ihza).
2. **Keaktifan Kemitraan Tahunan (Active Status Constraint)**:
   - Mitra HARUS terdaftar dan berstatus `AKTIF` pada tahun anggaran pelaksanaan kegiatan (`kemitraans.tahun == tahun_kegiatan` dan `kemitraans.status == 'AKTIF'`).
3. **Pencegahan Tumpang-Tindih Jadwal Sensus (Strict Sensus Collision Prevention)**:
   - Jika suatu kegiatan bertipe `SENSUS`, rentang tanggal pelaksanaannya sama sekali **TIDAK BOLEH** beririsan dengan jadwal kontrak Sensus lain maupun Survei lain di bulan yang sama bagi mitra tersebut.
   - Jika kedua kegiatan bertipe `SURVEI`, tanggal boleh beririsan asalkan akumulasi honor tidak melampaui plafon SBML bulanan.
4. **Plafon Proporsional SBML (Standar Biaya Masukan Lainnya Bulanan)**:
   - Batas SBML Sensus: **Rp 4.694.000** per bulan kalender.
   - Batas SBML Survei: **Rp 3.353.000** per bulan kalender.
   - Honor dihitung secara proporsional per hari kalender aktif jika suatu kegiatan berjalan lintas bulan. Akumulasi penerimaan mitra pada seluruh bulan terdampak tidak boleh melewati batas SBML ini.
5. **Validasi Target Positif**:
   - Nilai `target` wajib berupa angka positif lebih dari nol (`target > 0`).

### 5 Informasi Wajib Sebelum Memproses Kontrak & BAST (Mandatory Intake Checklist):
> [!IMPORTANT]
> Jangan berasumsi sepihak! Bila ada pegawai kantor yang meminta pembuatan SPK dan BAST namun informasinya belum lengkap, **WAJIB tanyakan/konfirmasi ulang** sebelum mengeksekusi ke Dokter V:
> 1. **Nama Kegiatan & Tahapan Spesifik**: Nama survei/sensus serta tahapannya (*Listing*, *Pencacahan Lapangan PPL/PML*, atau *Pengolahan/Entri Data*).
> 2. **Posisi Petugas & Satuan Beban Kerja**: Jabatan yang diemban serta satuan beban (Dokumen, SLS, Rumah Tangga) beserta target kuota per mitra.
> 3. **Bulan Kalender Kontrak (SPK)**: Bulan resmi penerbitan kontrak (misal: September atau Oktober). Di Dokter V, tanggal akhir kegiatan pada master honor wajib berada di bulan target agar nomor SPK dan BAST diterbitkan pada bulan yang benar.
> 4. **Identitas Mitra**: Nama lengkap dan ID Sobat (atau NIK) yang valid dan aktif di tahun berjalan.
> 5. **Alokasi Lain di Bulan yang Sama (Cek SBML)**: Memastikan apakah mitra sudah ada penugasan survei lain pada bulan tersebut agar total honor gabungan tidak melampaui pagu SBML bulanan (maks Rp 3.353.000/bulan).

---

## 3. ATURAN EMAS EFISIENSI TOKEN AI (AGENT-NATIVE BEST PRACTICES - OKTOBER 2026)

Untuk menghemat context window, mempercepat reasoning, dan menghindari payload bloat:

1. **Selalu Gunakan Parameter `compact=1`**:
   - Seluruh endpoint GET (`/kegiatan-manmit`, `/mitras`, `/alokasi`, `/kontrak`, `/bast`, `/audit-logs`) mendukung parameter `compact=1`.
   - Menghemat hingga **80% token** dengan memangkas metadata timestamps dan relasi berulang yang tidak esensial. CLI `dokter_v_tool` menyalakan mode ini secara bawaan (*default*).
2. **Lakukan Filtering di Server (Server-Side Heavy Lifting)**:
   - Jangan pernah mengambil seluruh data lalu memfilter di dalam prompt. Gunakan query parameters:
     - `bulan={1..12}`: Menyaring data hanya pada bulan yang sedang diproses.
     - `q={keyword}` atau `search={keyword}`: Pencarian instan (nama, ID Sobat, NIK, nama kegiatan, no surat).
     - `has_honors=1`: Pada kegiatan, hanya ambil kegiatan yang sudah memiliki slot honor.
     - `ids={id1,id2,...}`: Pada mitra, lakukan batch lookup sekaligus (*Fetch-Once, Process-Locally*).
     - `with_sbml=1` & `available_only=1`: Pada mitra, server langsung menghitung dan menyaring mitra yang sisa pagu SBML-nya masih cukup.
3. **Paginasi Terukur**:
   - Gunakan `limit=10` atau `limit=20` jika hanya membutuhkan sampel verifikasi.
4. **Audit Trail Pruning**:
   - Gunakan `only_rollbackable=1` untuk langsung menemukan mutasi yang dapat di-undo tanpa membanjiri konteks dengan log lawas.

---

## 4. ALUR KERJA STANDAR AGENT (RECOMMENDED AGENTIC PIPELINE)

```text
[Phase 1: Token-Efficient Discovery]
   ├──► dokter_v_tool kegiatan --bulan 3 --has-honors
   └──► dokter_v_tool mitra --bulan 3 --available-only
         │
[Phase 2: Pre-Flight Simulation]
   └──► dokter_v_tool check --honor-id <ID> --target <N> --id-sobat <SOBAT>
         ├── Jika eligible == false ──► AI evaluasi alasan penolakan & sesuaikan input
         └── Jika eligible == true  ──► Lanjut eksekusi
               │
[Phase 3: Execution]
   └──► dokter_v_tool allocate --honor-id <ID> --target <N> --id-sobat <SOBAT>
         │ (Atomic write: Buat Alokasi + Terbitkan SPK & BAST)
         │
[Phase 4: Document Verification]
   ├──► dokter_v_tool kontrak --mitra-id <ID> --bulan 3
   └──► dokter_v_tool bast --mitra-id <ID> --bulan 3
         │
[Phase 5: Self-Correction / Undo (Opsional)]
   ├──► dokter_v_tool audit-logs --only-rollbackable
   └──► dokter_v_tool rollback --id <AUDIT_LOG_ID> --reason "<alasan>"
```

---

## 5. KATALOG REST API ENDPOINTS & SPESIFIKASI TEKNIS

| Method | Endpoint Path | Fungsi Utama | Parameter Kunci |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/kegiatan-manmit` | Lookup kegiatan & honor | `tahun`, `bulan`, `jenis`, `has_honors=1`, `compact=1`, `q`, `sort_by`, `sort_order` |
| `GET` | `/api/v1/kegiatan-manmit/{id}` | Detail kegiatan & child honors | Path: `{id}` |
| `PATCH` | `/api/v1/kegiatan-manmit/{id}` | Update nama/tanggal pelaksanaan kegiatan | Path: `{id}`, Body: `nama`, `tgl_mulai_pelaksanaan`, `tgl_akhir_pelaksanaan` |
| `POST` | `/api/v1/kegiatan-manmit/{id}/rename-id` | Rename / migrasi ID kegiatan (Cascade-Safe) | Body: `new_id`, `new_nama`, `cascade_honor_ids=true` |
| `GET` | `/api/v1/honors` | Lookup master honor & perpanjangan tgl | `tahun`, `bulan`, `kegiatan_id`, `compact=1`, `q` |
| `GET` | `/api/v1/honors/{id}` | Detail item master honor | Path: `{id}` |
| `PATCH` | `/api/v1/honors/{id}` | Update honor (tgl akhir, harga, satuan) | Path: `{id}`, Body: `tanggal_akhir_kegiatan`, `harga_per_satuan`, etc. |
| `GET` | `/api/v1/pegawais` | Lookup direktori pegawai BPS | `compact=1`, `q` (nama, NIP, panggilan, email), `unit_kerja` |
| `GET` | `/api/v1/pegawais/{nip}` | Detail pegawai BPS | Path: `{nip}` |
| `POST` | `/api/v1/pegawais` | Tambah pegawai BPS baru | Body: `nip`, `nip9`, `nama`, `panggilan`, `jabatan`, `nomor_wa`, etc. |
| `PATCH` | `/api/v1/pegawais/{nip}` | Update data pegawai BPS | Path: `{nip}`, Body: fields to update |
| `GET` | `/api/v1/mitras` | Lookup direktori mitra | `tahun`, `bulan`, `ids`, `aktif_only=1`, `available_only=1`, `with_sbml=1`, `kecamatan`, `desa`, `jenis_kelamin`, `posisi`, `has_allocations`, `compact=1`, `q` |
| `GET` | `/api/v1/mitras/{id}` | Detail profil lengkap mitra | Path: `{id}` (ID/Sobat/NIK), `with_allocations=1` |
| `PATCH` | `/api/v1/mitras/{id}` | Update profil & kontak WhatsApp mitra | Path: `{id}`, Body: `nomor_wa`, `no_telp`, `email`, `alamat_detail`, `catatan`, `status_kemitraan` |
| `POST` | `/api/v1/alokasi/check` | Dry-run simulasi SBML & jadwal | Body: `mitra_id`/`id_sobat`, `honor_id`, `target` |
| `POST` | `/api/v1/alokasi` | Eksekusi single alokasi | Body: `mitra_id`/`id_sobat`, `honor_id`, `target` |
| `POST` | `/api/v1/alokasi` | Eksekusi batch alokasi | Body: `{"allocations": [...]}` |
| `GET` | `/api/v1/alokasi` | Daftar alokasi berjalan | `mitra_id`, `id_sobat`, `kegiatan_id`, `honor_id`, `bulan`, `compact=1`, `q` |
| `GET` | `/api/v1/kontrak` | Lookup SPK & URL cetak PDF | `mitra_id`, `id_sobat`, `kegiatan_id`, `bulan`, `tahun`, `compact=1`, `q` |
| `GET` | `/api/v1/bast` | Lookup BAST & URL cetak PDF | `mitra_id`, `id_sobat`, `kegiatan_id`, `bulan`, `tahun`, `compact=1`, `q` |
| `GET` | `/api/v1/audit-logs` | Lookup jejak mutasi & rollbackable | `only_rollbackable=1`, `compact=1`, `limit` |
| `GET` | `/api/v1/audit-logs/{id}` | Detail diff state mutasi | Path: `{id}` |
| `POST` | `/api/v1/audit-logs/{id}/rollback` | Rollback universal mutasi | Body: `{"reason": "..."}` |

### SOP 2 Langkah: Perpanjangan Waktu Kegiatan & Master Honor
Jika ada kegiatan survei yang masa pencacahan lapangannya diperpanjang:
1. **Langkah 1**: Perbarui tanggal akhir di Master Kegiatan jika tanggal akhir honor melebihi rentang kegiatan:
   ```bash
   dokter_v_tool update-kegiatan --id "SERUTI26-TW3" --tgl-akhir "2026-09-25"
   ```
2. **Langkah 2**: Perbarui tanggal akhir master honor terkait:
   ```bash
   dokter_v_tool update-honor --id "SERUTI26-TW3-PPL-PENDATAAN" --tgl-akhir "2026-09-25"
   ```
   *Efek Otomatis*: Backend Dokter V akan otomatis meregenerasi tanggal BAST dan SPK yang terhubung tanpa perlu menginput ulang alokasi!

### Detail Endpoint Khusus: Rename / Migrasi ID Kegiatan (Cascade Safe)
- **Method & Path**: `POST /api/v1/kegiatan-manmit/{id}/rename-id`
- **Tujuan**: Memperbaiki / menstandarisasi ID kegiatan (contoh: `SERUTI26` menjadi `SERUTI26-TW3`) secara aman tanpa merusak dokumen yang sudah terbit.
- **Request Body (JSON)**:
```json
{
  "new_id": "SERUTI26-TW3",
  "new_nama": "Survei Ekonomi Rumah Tangga Triwulan III",
  "cascade_honor_ids": true
}
```
- **Karakteristik Keamanan**:
  - Mengubah primary key `kegiatan_manmits.id` secara atomik.
  - Meng-cascade seluruh `honors` (menyesuaikan prefix ID) dan `alokasi_honors` (`honor_id`).
  - **100% AMAN**: Nomor surat SPK dan BAST yang sudah terbit TIDAK BERUBAH dan TIDAK DIHAPUS. Tautan cetak SPK bulanan tetap utuh.
  - Tercatat di Audit Log dan dapat di-rollback sewaktu-waktu via endpoint rollback.

### Detail Endpoint Khusus: Profil & Kontak WhatsApp Mitra
- **Lookup Detail**: `GET /api/v1/mitras/{id}?with_allocations=1`
- **Update Profil / Nomor WA**: `PATCH /api/v1/mitras/{id}`
  - Kolom `nomor_wa` terpisah dari `no_telp` (data asli SOBAT) agar data master tetap aman dan kontak WhatsApp aktif lapangan tersimpan rapi.
  - Nomor otomatis dinormalisasi (`0812...` -> `62812...`).
  - Tercatat di Audit Log (`action: UPDATE_MITRA`) dan 100% reversible (bisa di-rollback).

### Detail Endpoint Khusus: Master Pegawai BPS
- **Lookup Direktori**: `GET /api/v1/pegawais?compact=1&q=ihza`
- **Lookup Detail**: `GET /api/v1/pegawais/{nip}`
- **Create Pegawai**: `POST /api/v1/pegawais`
- **Update Pegawai**: `PATCH /api/v1/pegawais/{nip}`
- **Universal Rollback**: Tindakan `CREATE_PEGAWAI` dan `UPDATE_PEGAWAI` otomatis tercatat di audit log dan dapat di-rollback secara utuh.

---

## 6. PANDUAN LENGKAP CLI `dokter_v_tool` (Alias: `sipedas_tool`)

Helper tool `dokter_v_tool` telah terpasang di sistem (`/usr/local/bin/dokter_v_tool`, alias: `/usr/local/bin/sipedas_tool`):

```bash
# 1. Cek Koneksi & Autentikasi
dokter_v_tool status

# 2. Verifikasi Hak Akses Pengirim (Whitelist Tim Kerja Mempawah)
dokter_v_tool check-access --sender "6289625345646@s.whatsapp.net"

# 3. Cari Kegiatan Aktif di Bulan Tertentu (Mode Compact Aktif Default)
dokter_v_tool kegiatan --bulan 3 --has-honors
dokter_v_tool kegiatan -q "SUSENAS" --jenis SURVEI

# 4. Rename / Standarisasi ID Kegiatan (Cascade Safe)
dokter_v_tool rename-kegiatan --id "SERUTI26" --new-id "SERUTI26-TW3" --new-nama "(SERUTI26) SURVEI EKONOMI RUMAH TANGGA TRIWULANAN TAHUN 2026 Triwulan III"

# 5. Detail & Update Rentang Tanggal Kegiatan
dokter_v_tool kegiatan-detail --id "SERUTI26-TW3"
dokter_v_tool update-kegiatan --id "SERUTI26-TW3" --tgl-akhir "2026-09-25"

# 6. Master Honor & Perpanjangan Tanggal Honor (SOP 2 Langkah)
dokter_v_tool honor -q "SERUTI" --bulan 9
dokter_v_tool honor-detail --id "SERUTI26-TW3-PPL-PENDATAAN"
dokter_v_tool update-honor --id "SERUTI26-TW3-PPL-PENDATAAN" --tgl-akhir "2026-09-25"

# 7. Master Pegawai BPS (Lookup, Tambah & Perbarui)
dokter_v_tool pegawai -q "Ihza"
dokter_v_tool pegawai-detail --nip "199910282023021005"
dokter_v_tool update-pegawai --nip "199910282023021005" --nomor-wa "6289625345646"

# 8. Cari Mitra (Tersedia dengan Pagu SBML Cukup / Filter Wilayah & Posisi)
dokter_v_tool mitra --bulan 3 --available-only
dokter_v_tool mitra --kecamatan "MEMPAWAH HILIR" --posisi "Mitra Pendataan"
dokter_v_tool mitra --ids "601,320,559"
dokter_v_tool mitra -q "SOLEHA"

# 9. Detail Profil & Update Kontak WhatsApp Mitra
dokter_v_tool mitra-detail --id 54 --with-allocations
dokter_v_tool update-mitra --id 54 --nomor-wa "081258306655" --catatan "Mitra aktif responsif lapangan"

# 10. Lihat Daftar Alokasi Berjalan
dokter_v_tool alokasi --bulan 3 --limit 10
dokter_v_tool alokasi -q "SOLEHA"

# 11. Simulasi Pre-Flight Dry-Run
dokter_v_tool check --id-sobat "610426050125" --honor-id "VHTS-FEBRUARI-februari-PPL-PENDATAAN" --target 5

# 12. Eksekusi Alokasi Honor
dokter_v_tool allocate --id-sobat "610426050125" --honor-id "VHTS-FEBRUARI-februari-PPL-PENDATAAN" --target 5
dokter_v_tool batch-allocate --file alokasi.json

# 13. Cari Dokumen SPK & BAST (Beserta Link Unduh PDF Bersih)
dokter_v_tool kontrak --mitra-id 601 --bulan 8
dokter_v_tool bast --mitra-id 601 --bulan 8

# 14. Audit Log & Rollback Universal (Alokasi, Mitra, Kegiatan, Honor, Pegawai)
dokter_v_tool audit-logs --only-rollbackable
dokter_v_tool rollback --id 312 --reason "Salah input volume target"
```

---

## 7. PANDUAN PENANGANAN ERROR & SELF-HEALING AI

- **`401 Unauthorized`**: Token API Key tidak valid / nonaktif. Pastikan `DOKTER_V_API_KEY` terkonfigurasi di Infisical atau `.secrets.env`.
- **`404 Not Found`**: ID Kegiatan / Honor / Mitra tidak ada. Gunakan pencarian `-q "..."`.
- **`422 Unprocessable Content`**:
  - *Mitra tidak aktif*: Ganti mitra dengan yang berstatus `AKTIF` via `dokter_v_tool mitra --aktif-only`.
  - *Bentrok jadwal SENSUS*: Mitra bertabrakan tanggal dengan jadwal lain di bulan tersebut. Alokasikan mitra lain.
  - *Melampaui SBML*: Kurangi `target` volume atau gunakan `dokter_v_tool mitra --bulan X --available-only`.
