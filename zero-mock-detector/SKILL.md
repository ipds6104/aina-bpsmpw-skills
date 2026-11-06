---
name: zero-mock-detector
description: High-precision static analysis and code-graph AST inspector for detecting mock code, silent mocks, bodyless stubs, fake latency simulators, and agent scratch pollution in production pathways per October 2026 standards. Activate whenever auditing codebase integrity, checking for mock leakage, verifying zero-mock compliance, or managing repo-level technical debt ledgers.
---

# 🛡️ Zero-Mock & Silent Mock Static Detector

Skill ini menyediakan prosedur dan perkakas statis berbasis **AST Code-Graph Intelligence** untuk mendeteksi secara instan kode tiruan (*mock*), *silent mock*, stub fungsi kosong (*bodyless stubs*), simulator latensi jaringan palsu, komentar rasionalisasi halusinasi, dan polusi berkas catatan agen di jalur produksi (*production paths*), sejalan dengan standar rekayasa enterprise **Oktober 2026**.

---

## 🎯 Kapan Menggunakan Skill Ini

1. **Sebelum Menyelesaikan Tugas Koding / Refactoring**:
   - Memastikan bahwa kode baru tidak menggunakan *mock* atau *stub* tersembunyi yang menggantikan logika nyata.
2. **Saat Menjalankan Audit Kepatuhan & Tata Kelola**:
   - Sebagai gerbang penegakan *Zero-Mock Invariant* di pipeline CI/CD atau script tata kelola (`scripts/governance-check.sh`).
3. **Saat Memeriksa Repositori Baru / Adopsi Enterprise**:
   - Menjamin bahwa lapisan repositori/gateway/driver benar-benar terhubung ke I/O fisik (basis data atau jaringan), bukan sekadar mengembalikan data JSON/konstanta statis.
4. **Saat Mengelola Utang Teknis (*Technical Debt*) yang Sah**:
   - Memvalidasi kepatuhan format catatan pengecualian pada *Repository-Level Debt Ledger* (`docs/TECHNICAL_DEBT.md` atau `.zero-mock-allowlist.json`).

---

## 🛠️ CLI Tool Global: `detect-mocks` / `zero-mock-detector`

Tool ini terpasang secara global di `/usr/local/bin/detect-mocks` dan `~/.local/bin/detect-mocks`.

### 1. Perintah Standar (Interaktif / Terminal)
```bash
# Pindai direktori saat ini
detect-mocks

# Pindai workspace spesifik
detect-mocks /path/to/project
```

### 2. Mode Strict (Gagal pada Semua Tingkat Temuan)
```bash
detect-mocks --strict
```

### 3. Mode JSON (Otomasi Agen & CI/CD)
```bash
detect-mocks --json
```

---

## 📐 Taksonomi Pelanggaran Mock (Standar Oktober 2026)

| Tingkat | Kategori Rule | Contoh Deteksi | Aksi Mitigasi |
|---|---|---|---|
| 🚨 **CRITICAL** | `MOCK_IMPORT_*` | `from unittest.mock import MagicMock`, `import { sinon } from 'sinon'`, `use mockall::*` di dalam `src/` | Hapus import pengujian dari berkas produksi. Gunakan dependency injection dengan driver nyata. |
| ⚠️ **HIGH** | `RULE_MOCK_SYMBOL_NAME` | `struct MockUserRepository`, `class FakePaymentGateway` di dalam `src/` | Pindahkan ke direktori `tests/` atau ganti dengan implementasi driver nyata. |
| ⚠️ **HIGH** | `RULE_FAKE_LATENCY` | `tokio::time::sleep()`, `time.sleep()`, `setTimeout()` di dalam repository/service/driver | Hapus simulator jeda waktu palsu. Gunakan panggilan I/O nyata atau backoff terkonfigurasi. |
| ⚠️ **HIGH** | `RULE_STUBBED_CODE` | `todo!()`, `unimplemented!()`, `throw new Error("TODO")`, `raise NotImplementedError` | Tuntaskan implementasi logika bisnis, atau daftarkan ke repo-level ledger jika berupa blokir hardware luar. |
| ⚠️ **HIGH** | `RULE_STUB_BODY_UNTRACKED` | `(void)param; return 0;` (C++), `def fn(): pass` (Python), `fn() -> Ok(())` tanpa I/O (Rust) | Lengkapi logika nyata, atau daftarkan ke *Repo-Level Technical Debt Ledger* disertai alasan arsitektural dan sitasi. |
| ⚠️ **HIGH** | `RULE_SILENT_FALLBACK` | `catch (e) {}`, `except: pass`, swallowed error in production | Hapus penelanan error diam-diam; lempar ulang (rethrow), atau gunakan fault-injection test jika fallback sah. |
| ⚠️ **HIGH** | `RULE_AGENT_NOTE_POLLUTION` | `notes.md`, `agent_notes.*`, `scratch_*.py`, `temp_*.py`, `*.log` di direktori `src/` | Hapus berkas sampah agen sebelum melakukan commit/deploy. |
| 🟡 **MEDIUM** | `RULE_RATIONALIZING_COMMENT` | `// assume success for now`, `// dummy mock for testing`, `// fake return` | Hapus komentar rasionalisasi palsu; ganti dengan implementasi nyata atau tes unit. |
| 🟡 **MEDIUM** | `RULE_MOCK_BYPASS_FLAG` | `if (process.env.NODE_ENV === 'test') { return dummy; }` atau `MOCK_ENABLED` | Pisahkan konfigurasi pengujian via adapter pattern / config injection, hindari bypass hardcoded. |

---

## 🏛️ Arsitektur Dua Level: Repo-Level Ledger vs Global Tooling

> [!IMPORTANT]
> **Pemisahan Tanggung Jawab (*Separation of Concerns*)**:
> - **Level Global (`agent-skills` / global tools)**: Menyediakan mesin scanner, aturan tata bahasa, dan parser AST. Tool global **TIDAK PERNAH** menyimpan pengecualian spesifik proyek di dalam kodenya sendiri.
> - **Level Repo (`docs/TECHNICAL_DEBT.md` / `docs/dev/debt/*.md`)**: Menyimpan daftar stub yang sah, alasan arsitektural, dan sitasi referensi (Issue #, RFC, spesifikasi hardware). Hal ini menjamin repositori 100% mandiri, portabel, dan dapat diaudit di CI/CD runner manapun.

### Format Ledger di Level Repositori

Detector secara otomatis mencari dan mengenali 3 format ledger berikut di direktori proyek:

#### Format 1: Markdown Ledger (`docs/TECHNICAL_DEBT.md` atau `docs/dev/debt/*.md`)
```markdown
# Technical Debt Ledger

### Silent stubs
- `scePadUnknownLotus`: DualSense unmeasured hardware extension register (Citation: PS5 Firmware 13.60 measurements / Issue #3177)
- [sceAgcDriverSpecialOwner](../../src/driver.cpp) - Hardware register unmeasured on consumer silicon (Citation: AMD RDNA2 ISA Table 24)
```

#### Format 2: JSON Allowlist (`.zero-mock-allowlist.json`)
```json
{
  "exemptions": [
    {
      "symbol": "sceAgcDriverSpecialOwner",
      "file": "src/driver.cpp",
      "reason": "Hardware register unmeasured on consumer silicon",
      "citation": "Issue #1234 / AMD RDNA2 ISA Table 24"
    }
  ]
}
```

#### Format 3: Anotasi In-Code Langsung
```cpp
// @allow-stub: Fallback display timing (citation: RFC-8594 Section 3)
void sync_frame() {
    return;
}
```

---

## 🏛️ Arsitektur Verifikasi Dua Lapisan (Dual-Tier Verification Doctrine)

### Lapisan 1 (L1) - Static Gatekeeper (`detect-mocks`)
Filter deterministik cepat (<100ms) untuk menangkap pelanggaran struktural:
- Mock framework import leakage.
- Simbol bernama `Mock*`, `Fake*`, `Stub*`.
- Fungsi kosong (*bodyless stubs*) tanpa pendaftaran di repo-level ledger.
- Simulator latensi palsu (`sleep`).
- Berkas catatan/scratch agen yang tertinggal.

### Lapisan 2 (L2) - Runtime Empirical Proof (Sentinel & Fault Injection)
Bukti tak terbantahkan bahwa sistem benar-benar terhubung ke driver/storage nyata:
1. **Sentinel Round-Trip Invariant**: Menulis nilai acak unik (`sentinel-<uuid>-<ts>`) dan memverifikasi pembacaan langsung dari storage fisik (mock statis pasti gagal).
2. **Fault Injection Probing**: Mematikan koneksi DB sementara atau memicu upstream 500, memastikan API menampilkan error eksplisit (bukan 200 OK dengan silent fallback kosong).

---

## 🧪 Panduan Verifikasi Cepat

Untuk memverifikasi kepatuhan workspace secara 1 baris:
```bash
detect-mocks . && echo "Zero-mock verification passed!"
```
