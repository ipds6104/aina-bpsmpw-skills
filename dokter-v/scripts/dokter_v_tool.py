#!/usr/bin/env python3
"""
dokter_v_tool.py - CLI tool for Dokter V BPS integration (Token-Efficient October 2026 Edition)

Manages honor allocation, pre-flight dry-runs, SPK & BAST document retrieval,
allocation tracking, and audit log rollbacks for BPS partner management (Manmit).
Enforces agent-native best practices with compact mode (~80% token reduction).
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "https://admin.dvlpid.my.id/api/v1"
CONFIG_SECRETS_FILE = Path("/app/data/config/.secrets.env")
TIM_KERJA_WHITELIST_FILE = Path("/app/data/config/tim_kerja_mempawah_whitelist.json")


def check_sender_access(sender_jid: str) -> dict:
    """Verify if sender is an authorized member of Tim Kerja Mempawah."""
    if not sender_jid:
        return {"allowed": False, "reason": "Sender JID tidak disertakan."}

    sender_clean = sender_jid.strip().lower()

    # 1. Check local whitelist file
    if TIM_KERJA_WHITELIST_FILE.is_file():
        try:
            wl = json.loads(TIM_KERJA_WHITELIST_FILE.read_text(encoding="utf-8"))
            lids = {str(x).strip().lower() for x in wl.get("lids", [])}
            phones = {str(x).strip().lower() for x in wl.get("known_phone_jids", [])}
            if sender_clean in lids or sender_clean in phones:
                return {"allowed": True, "sender": sender_clean, "source": "whitelist"}

            # Check digits match for phone numbers
            sender_digits = re.sub(r"\D", "", sender_clean)
            for p in phones:
                p_digits = re.sub(r"\D", "", p)
                if sender_digits and p_digits and (sender_digits == p_digits or sender_digits.endswith(p_digits) or p_digits.endswith(sender_digits)):
                    return {"allowed": True, "sender": sender_clean, "source": "whitelist_phone_match"}
        except Exception:
            pass

    # 2. Check user_profiles in database
    for db_path in ("/app/data/aina.db", "data/aina.db"):
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT name, role, authority_level, notes FROM user_profiles WHERE sender_jid = ?", (sender_clean,))
                row = c.fetchone()
                if row:
                    auth = (row[2] or "").lower()
                    notes = (row[3] or "").lower()
                    role = (row[1] or "").lower()
                    if auth in ("admin", "staff") and ("mempawah" in notes or "mempawah" in role or auth == "admin"):
                        conn.close()
                        return {"allowed": True, "sender": sender_clean, "name": row[0], "source": "user_profiles"}
                conn.close()
            except Exception:
                pass

    # 3. Dynamic check via whatsmeow gateway if connected
    try:
        import subprocess
        res = subprocess.run(
            ["python3", "skills/whatsmeow/scripts/wa_tool.py", "group-info", "--jid", "120363253842861469@g.us"],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            participants = data.get("data", {}).get("participants", [])
            for p in participants:
                p_jid = str(p.get("jid", "")).strip().lower()
                p_phone = str(p.get("phone_number", "")).strip()
                if p_jid and p_jid == sender_clean:
                    return {"allowed": True, "sender": sender_clean, "source": "live_group_info"}
                if p_phone and sender_clean.startswith(p_phone):
                    return {"allowed": True, "sender": sender_clean, "source": "live_group_phone"}
    except Exception:
        pass

    return {
        "allowed": False,
        "sender": sender_clean,
        "reason": "Nomor WhatsApp atau akun ini tidak terdaftar di grup Tim Kerja Mempawah."
    }


def get_credentials():
    """Retrieve Dokter V API key and base URL securely without hardcoding."""
    api_key = os.getenv("DOKTER_V_API_KEY") or os.getenv("SIPEDAS_API_KEY")
    base_url = os.getenv("DOKTER_V_BASE_URL") or os.getenv("SIPEDAS_BASE_URL")

    # Fallback to local secrets store if not present in process environment
    if not api_key and CONFIG_SECRETS_FILE.is_file():
        try:
            content = CONFIG_SECRETS_FILE.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k in ("DOKTER_V_API_KEY", "SIPEDAS_API_KEY") and not api_key:
                        api_key = v
                    elif k in ("DOKTER_V_BASE_URL", "SIPEDAS_BASE_URL") and not base_url:
                        base_url = v
        except Exception as e:
            sys.stderr.write(f"[WARN] Failed to read .secrets.env: {e}\n")

    if not api_key:
        # Check via Infisical / secret_tool helper if available
        try:
            import subprocess
            for secret_name in ("DOKTER_V_API_KEY", "SIPEDAS_API_KEY"):
                res = subprocess.run(
                    ["python3", "/app/skills/infisical/scripts/secret_tool.py", "get", secret_name, "--plain"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                val = res.stdout.strip()
                if res.returncode == 0 and val and not val.startswith("{") and not val.startswith("["):
                    api_key = val
                    break
        except Exception:
            pass

    if not api_key:
        sys.stderr.write("[ERROR] DOKTER_V_API_KEY is not configured in environment, Infisical, or .secrets.env.\n")
        sys.exit(1)

    if not base_url:
        base_url = DEFAULT_BASE_URL

    return api_key.strip(), base_url.strip().rstrip("/")


def api_request(method: str, path: str, params: dict = None, body: dict = None) -> dict:
    """Execute authenticated HTTP request to SIPEDAS REST API."""
    api_key, base_url = get_credentials()
    url = f"{base_url}{path}"

    if params:
        query_string = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        if query_string:
            url = f"{url}?{query_string}"

    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json",
        "User-Agent": "Aina-DokterV/1.0 (compatible; BPS Mempawah Integration)",
    }

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"status": "success", "raw": content}
    except urllib.error.HTTPError as e:
        raw_error = e.read().decode("utf-8")
        try:
            error_json = json.loads(raw_error)
            error_json["http_status"] = e.code
            return error_json
        except Exception:
            return {
                "status": "error",
                "http_status": e.code,
                "message": e.reason,
                "details": raw_error,
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


# =====================================================================
# Commands
# =====================================================================

def cmd_status(args):
    """Check connection and authentication status."""
    res = api_request("GET", "/kegiatan-manmit", params={"limit": 1, "compact": 1})
    if res.get("status") == "success" or "data" in res:
        print(json.dumps({
            "status": "connected",
            "message": "Dokter V API connection and authentication verified successfully.",
            "endpoint": DEFAULT_BASE_URL,
            "has_api_key": True,
        }, indent=2))
        return 0
    else:
        print(json.dumps({
            "status": "error",
            "message": "Failed to connect to Dokter V API.",
            "response": res,
        }, indent=2))
        return 1


def cmd_kegiatan(args):
    """Lookup kegiatan & honor with token efficiency."""
    params = {
        "tahun": args.tahun,
        "bulan": args.bulan,
        "jenis": args.jenis,
        "q": args.q or args.search,
        "page": args.page,
        "limit": args.limit or args.per_page,
        "compact": 1 if args.compact else 0,
        "has_honors": 1 if args.has_honors else None,
        "sort_by": args.sort_by,
        "sort_order": args.sort_order,
    }
    res = api_request("GET", "/kegiatan-manmit", params=params)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_check_access(args):
    """Verify if sender is an authorized member of Tim Kerja Mempawah."""
    auth = check_sender_access(args.sender)
    print(json.dumps(auth, indent=2))
    return 0 if auth.get("allowed") else 1


def cmd_rename_kegiatan(args):
    """Rename / migrate kegiatan ID with cascade-safe handling without breaking SPK/BAST."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    body = {
        "new_id": args.new_id,
        "cascade_honor_ids": args.cascade_honor_ids,
    }
    if args.new_nama:
        body["new_nama"] = args.new_nama

    encoded_id = urllib.parse.quote(str(args.id), safe="")
    res = api_request("POST", f"/kegiatan-manmit/{encoded_id}/rename-id", body=body)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_kegiatan_detail(args):
    """Get single master kegiatan detail with all its child honors."""
    encoded_id = urllib.parse.quote(str(args.id), safe="")
    res = api_request("GET", f"/kegiatan-manmit/{encoded_id}")
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_update_kegiatan(args):
    """Update kegiatan schedule (tgl_mulai_pelaksanaan, tgl_akhir_pelaksanaan) or nama."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    body = {}
    if getattr(args, "json", None):
        try:
            body = json.loads(args.json)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[ERROR] Invalid JSON in --json: {e}\n")
            return 1
    elif getattr(args, "file", None):
        file_path = Path(args.file)
        if not file_path.is_file():
            sys.stderr.write(f"[ERROR] File not found: {args.file}\n")
            return 1
        body = json.loads(file_path.read_text(encoding="utf-8"))

    if getattr(args, "tgl_akhir_pelaksanaan", None):
        body["tgl_akhir_pelaksanaan"] = args.tgl_akhir_pelaksanaan
    if getattr(args, "tgl_mulai_pelaksanaan", None):
        body["tgl_mulai_pelaksanaan"] = args.tgl_mulai_pelaksanaan
    if getattr(args, "nama", None):
        body["nama"] = args.nama

    if not body:
        sys.stderr.write("[ERROR] Tidak ada field yang diubah. Gunakan --tgl-akhir-pelaksanaan, --tgl-mulai-pelaksanaan, --nama, atau --json.\n")
        return 1

    encoded_id = urllib.parse.quote(str(args.id), safe="")
    res = api_request("PATCH", f"/kegiatan-manmit/{encoded_id}", body=body)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_honor(args):
    """Lookup master honors with token efficiency and filters."""
    params = {
        "q": args.q or args.search,
        "kegiatan_id": args.kegiatan_id,
        "tahun": args.tahun,
        "bulan": args.bulan,
        "compact": 1 if args.compact else 0,
        "sort_by": args.sort_by,
        "sort_order": args.sort_order,
        "page": args.page,
        "limit": args.limit or args.per_page,
    }
    res = api_request("GET", "/honors", params=params)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_honor_detail(args):
    """Get single master honor detail."""
    encoded_id = urllib.parse.quote(str(args.id), safe="")
    res = api_request("GET", f"/honors/{encoded_id}")
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_update_honor(args):
    """Update master honor dates or rates (tanggal_akhir_kegiatan, harga_per_satuan, dll)."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    body = {}
    if getattr(args, "json", None):
        try:
            body = json.loads(args.json)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[ERROR] Invalid JSON in --json: {e}\n")
            return 1
    elif getattr(args, "file", None):
        file_path = Path(args.file)
        if not file_path.is_file():
            sys.stderr.write(f"[ERROR] File not found: {args.file}\n")
            return 1
        body = json.loads(file_path.read_text(encoding="utf-8"))

    if getattr(args, "tanggal_akhir_kegiatan", None):
        body["tanggal_akhir_kegiatan"] = args.tanggal_akhir_kegiatan
    if getattr(args, "harga_per_satuan", None) is not None:
        body["harga_per_satuan"] = args.harga_per_satuan
    if getattr(args, "satuan_honor", None):
        body["satuan_honor"] = args.satuan_honor
    if getattr(args, "jabatan", None):
        body["jabatan"] = args.jabatan
    if getattr(args, "jenis_honor", None):
        body["jenis_honor"] = args.jenis_honor

    if not body:
        sys.stderr.write("[ERROR] Tidak ada field yang diubah. Gunakan --tanggal-akhir-kegiatan, --harga-per-satuan, atau --json.\n")
        return 1

    encoded_id = urllib.parse.quote(str(args.id), safe="")
    res = api_request("PATCH", f"/honors/{encoded_id}", body=body)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_pegawai(args):
    """Lookup pegawai BPS directory with filters and compact mode."""
    params = {
        "q": args.q or args.search,
        "unit_kerja": args.unit_kerja,
        "jabatan": args.jabatan,
        "golongan": args.golongan,
        "is_magang": args.is_magang,
        "compact": 1 if args.compact else 0,
        "sort_by": args.sort_by,
        "sort_order": args.sort_order,
        "page": args.page,
        "limit": args.limit or args.per_page,
    }
    res = api_request("GET", "/pegawais", params=params)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_pegawai_detail(args):
    """Get single pegawai detail by NIP or NIP9."""
    res = api_request("GET", f"/pegawais/{args.nip}")
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_create_pegawai(args):
    """Register a new pegawai to Dokter V."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    body = {}
    if getattr(args, "json", None):
        try:
            body = json.loads(args.json)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[ERROR] Invalid JSON in --json: {e}\n")
            return 1
    elif getattr(args, "file", None):
        file_path = Path(args.file)
        if not file_path.is_file():
            sys.stderr.write(f"[ERROR] File not found: {args.file}\n")
            return 1
        body = json.loads(file_path.read_text(encoding="utf-8"))

    for f in ["nama", "nip", "nip9", "panggilan", "golongan", "pangkat", "jabatan", "email", "unit_kerja", "nomor_wa", "atasan_langsung_id"]:
        val = getattr(args, f, None)
        if val is not None:
            body[f] = val

    if not body.get("nama") or not body.get("nip"):
        sys.stderr.write("[ERROR] Field 'nama' dan 'nip' wajib disertakan.\n")
        return 1

    res = api_request("POST", "/pegawais", body=body)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_update_pegawai(args):
    """Update existing pegawai profile."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    body = {}
    if getattr(args, "json", None):
        try:
            body = json.loads(args.json)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[ERROR] Invalid JSON in --json: {e}\n")
            return 1
    elif getattr(args, "file", None):
        file_path = Path(args.file)
        if not file_path.is_file():
            sys.stderr.write(f"[ERROR] File not found: {args.file}\n")
            return 1
        body = json.loads(file_path.read_text(encoding="utf-8"))

    for f in ["nama", "panggilan", "golongan", "pangkat", "jabatan", "email", "unit_kerja", "nomor_wa", "atasan_langsung_id"]:
        val = getattr(args, f, None)
        if val is not None:
            body[f] = val

    if not body:
        sys.stderr.write("[ERROR] Tidak ada atribut pegawai yang diubah.\n")
        return 1

    res = api_request("PATCH", f"/pegawais/{args.nip}", body=body)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_mitra(args):
    """Lookup mitra statistik with token efficiency and SBML availability."""
    params = {
        "tahun": args.tahun,
        "bulan": args.bulan,
        "status": args.status,
        "aktif_only": 1 if args.aktif_only else 0,
        "available_only": 1 if args.available_only else None,
        "with_sbml": 1 if args.with_sbml else None,
        "kecamatan": args.kecamatan,
        "desa": args.desa,
        "jenis_kelamin": args.jenis_kelamin,
        "posisi": args.posisi,
        "has_allocations": args.has_allocations,
        "ids": args.ids,
        "q": args.q or args.search,
        "sort_by": args.sort_by,
        "sort_order": args.sort_order,
        "page": args.page,
        "limit": args.limit or args.per_page,
        "compact": 1 if args.compact else 0,
    }
    res = api_request("GET", "/mitras", params=params)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_mitra_detail(args):
    """Get full mitra details including whatsapp info, domicile, and allocations."""
    params = {}
    if args.with_allocations:
        params["with_allocations"] = 1
    res = api_request("GET", f"/mitras/{args.id}", params=params if params else None)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_update_mitra(args):
    """Update mitra profile / contact info (nomor_wa, telp, email, alamat, catatan, status)."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    body = {}
    if getattr(args, "json", None):
        try:
            body = json.loads(args.json)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[ERROR] Invalid JSON in --json: {e}\n")
            return 1
    elif getattr(args, "file", None):
        file_path = Path(args.file)
        if not file_path.is_file():
            sys.stderr.write(f"[ERROR] File not found: {args.file}\n")
            return 1
        body = json.loads(file_path.read_text(encoding="utf-8"))

    if args.nomor_wa:
        body["nomor_wa"] = args.nomor_wa
    if args.no_telp:
        body["no_telp"] = args.no_telp
    if args.email:
        body["email"] = args.email
    if args.alamat_detail:
        body["alamat_detail"] = args.alamat_detail
    if args.catatan:
        body["catatan"] = args.catatan
    if args.status_kemitraan:
        body["status_kemitraan"] = args.status_kemitraan
    if args.tahun:
        body["tahun"] = args.tahun

    if not body:
        sys.stderr.write("[ERROR] No fields to update specified. Provide --nomor-wa, --no-telp, --email, etc.\n")
        return 1

    res = api_request("PATCH", f"/mitras/{args.id}", body=body)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_alokasi_list(args):
    """List existing honor allocations."""
    params = {
        "tahun": args.tahun,
        "bulan": args.bulan,
        "mitra_id": args.mitra_id,
        "id_sobat": args.id_sobat,
        "kegiatan_id": args.kegiatan_id,
        "honor_id": args.honor_id,
        "q": args.q or args.search,
        "page": args.page,
        "limit": args.limit or args.per_page,
        "compact": 1 if args.compact else 0,
    }
    res = api_request("GET", "/alokasi", params=params)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_check(args):
    """Pre-flight dry-run check."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    payload = {
        "honor_id": args.honor_id,
        "target": args.target,
    }
    if args.mitra_id is not None:
        payload["mitra_id"] = args.mitra_id
    elif args.id_sobat:
        payload["id_sobat"] = args.id_sobat
    else:
        sys.stderr.write("[ERROR] Either --mitra-id or --id-sobat must be specified.\n")
        return 1

    res = api_request("POST", "/alokasi/check", body=payload)
    print(json.dumps(res, indent=2))
    eligible = res.get("data", {}).get("eligible", False)
    return 0 if eligible else 1


def cmd_allocate(args):
    """Create single honor allocation."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    payload = {
        "honor_id": args.honor_id,
        "target": args.target,
    }
    if args.mitra_id is not None:
        payload["mitra_id"] = args.mitra_id
    elif args.id_sobat:
        payload["id_sobat"] = args.id_sobat
    else:
        sys.stderr.write("[ERROR] Either --mitra-id or --id-sobat must be specified.\n")
        return 1

    res = api_request("POST", "/alokasi", body=payload)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") in ("success", 201) or "data" in res else 1


def cmd_batch_allocate(args):
    """Create batch honor allocation."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    allocations = []
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            sys.stderr.write(f"[ERROR] File not found: {args.file}\n")
            return 1
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            allocations = data
        elif isinstance(data, dict) and "allocations" in data:
            allocations = data["allocations"]
        else:
            sys.stderr.write("[ERROR] JSON file must contain a list or an object with 'allocations'.\n")
            return 1
    elif args.json:
        data = json.loads(args.json)
        if isinstance(data, list):
            allocations = data
        elif isinstance(data, dict) and "allocations" in data:
            allocations = data["allocations"]
        else:
            sys.stderr.write("[ERROR] JSON string must contain a list or an object with 'allocations'.\n")
            return 1
    else:
        sys.stderr.write("[ERROR] Either --file or --json must be specified.\n")
        return 1

    payload = {"allocations": allocations}
    res = api_request("POST", "/alokasi", body=payload)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_kontrak(args):
    """Find contract / SPK documents."""
    params = {
        "mitra_id": args.mitra_id,
        "id_sobat": args.id_sobat,
        "kegiatan_id": args.kegiatan_id,
        "bulan": args.bulan,
        "tahun": args.tahun,
        "q": args.q or args.search,
        "page": args.page,
        "limit": args.limit or args.per_page,
        "compact": 1 if args.compact else 0,
    }
    res = api_request("GET", "/kontrak", params=params)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_bast(args):
    """Find BAST documents."""
    params = {
        "mitra_id": args.mitra_id,
        "id_sobat": args.id_sobat,
        "kegiatan_id": args.kegiatan_id,
        "bulan": args.bulan,
        "tahun": args.tahun,
        "q": args.q or args.search,
        "page": args.page,
        "limit": args.limit or args.per_page,
        "compact": 1 if args.compact else 0,
    }
    res = api_request("GET", "/bast", params=params)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_audit_logs(args):
    """List or inspect audit logs."""
    if args.id is not None:
        # Single audit log detail
        res = api_request("GET", f"/audit-logs/{args.id}")
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") != "error" else 1

    params = {
        "page": args.page,
        "limit": args.limit or args.per_page,
        "only_rollbackable": 1 if args.only_rollbackable else None,
        "compact": 1 if args.compact else 0,
    }
    res = api_request("GET", "/audit-logs", params=params)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


def cmd_rollback(args):
    """Rollback mutation via audit log id."""
    if getattr(args, "sender", None):
        auth = check_sender_access(args.sender)
        if not auth.get("allowed"):
            print(json.dumps({
                "status": "error",
                "http_status": 403,
                "message": "Akses Ditolak: Hanya nomor WhatsApp anggota grup Tim Kerja Mempawah yang berhak mengelola data Dokter V.",
                "auth_result": auth,
            }, indent=2))
            return 1

    body = {
        "reason": args.reason or "Dibatalkan oleh AI Agent",
    }
    res = api_request("POST", f"/audit-logs/{args.id}/rollback", body=body)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") != "error" else 1


# =====================================================================
# Main Parser
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Dokter V BPS CLI Tool - Partner Honor Allocation & Document Automation (Oct 2026 Edition)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # status
    subparsers.add_parser("status", help="Test Dokter V connection and authentication status")

    # kegiatan
    p_keg = subparsers.add_parser("kegiatan", help="Lookup master kegiatan and honor items")
    p_keg.add_argument("--tahun", type=int, default=2026, help="Filter budget year")
    p_keg.add_argument("--bulan", type=int, choices=range(1, 13), help="Filter active month (1-12)")
    p_keg.add_argument("--jenis", choices=["SURVEI", "SENSUS"], help="Filter by activity type")
    p_keg.add_argument("--has-honors", action="store_true", default=False, help="Only activities with honors")
    p_keg.add_argument("-q", "--q", type=str, help="Search keyword (name or ID)")
    p_keg.add_argument("--search", type=str, help="Alias for -q/--q")
    p_keg.add_argument("--sort-by", choices=["tgl_mulai_pelaksanaan", "nama", "id"], help="Sort field")
    p_keg.add_argument("--sort-order", choices=["asc", "desc"], default="asc", help="Sort order")
    p_keg.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode (~80%% token savings)")
    p_keg.add_argument("--page", type=int, default=1, help="Page number")
    p_keg.add_argument("--limit", type=int, default=20, help="Items per page")
    p_keg.add_argument("--per-page", type=int, help="Alias for --limit")

    # check-access
    p_auth = subparsers.add_parser("check-access", help="Verify if WhatsApp sender is an authorized member of Tim Kerja Mempawah")
    p_auth.add_argument("--sender", type=str, required=True, help="Sender WhatsApp JID (phone @s.whatsapp.net or LID @lid)")

    # rename-kegiatan / rename-id
    p_rename = subparsers.add_parser("rename-kegiatan", help="Rename/migrate kegiatan ID safely without breaking SPK/BAST")
    p_rename.add_argument("--id", type=str, required=True, help="Current Kegiatan ID (e.g. SERUTI26)")
    p_rename.add_argument("--new-id", type=str, required=True, help="New Kegiatan ID (e.g. SERUTI26-TW3)")
    p_rename.add_argument("--new-nama", type=str, help="Optional new activity name")
    p_rename.add_argument("--cascade-honor-ids", action=argparse.BooleanOptionalAction, default=True, help="Cascade update honor IDs prefix")
    p_rename.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    p_rename_alias = subparsers.add_parser("rename-id", help="Alias for rename-kegiatan")
    p_rename_alias.add_argument("--id", type=str, required=True, help="Current Kegiatan ID (e.g. SERUTI26)")
    p_rename_alias.add_argument("--new-id", type=str, required=True, help="New Kegiatan ID (e.g. SERUTI26-TW3)")
    p_rename_alias.add_argument("--new-nama", type=str, help="Optional new activity name")
    p_rename_alias.add_argument("--cascade-honor-ids", action=argparse.BooleanOptionalAction, default=True, help="Cascade update honor IDs prefix")
    p_rename_alias.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # kegiatan-detail / kegiatan-get
    p_keg_det = subparsers.add_parser("kegiatan-detail", help="Get single master kegiatan detail with child honors")
    p_keg_det.add_argument("--id", type=str, required=True, help="Kegiatan ID (e.g. SERUTI26-TW3)")
    p_keg_det_alias = subparsers.add_parser("kegiatan-get", help="Alias for kegiatan-detail")
    p_keg_det_alias.add_argument("--id", type=str, required=True, help="Kegiatan ID")

    # update-kegiatan / kegiatan-update
    p_keg_up = subparsers.add_parser("update-kegiatan", help="Update kegiatan schedule (tgl_mulai_pelaksanaan, tgl_akhir_pelaksanaan) or nama")
    p_keg_up.add_argument("--id", type=str, required=True, help="Kegiatan ID")
    p_keg_up.add_argument("--tgl-akhir-pelaksanaan", "--tgl-akhir", dest="tgl_akhir_pelaksanaan", type=str, help="End date (YYYY-MM-DD)")
    p_keg_up.add_argument("--tgl-mulai-pelaksanaan", "--tgl-mulai", dest="tgl_mulai_pelaksanaan", type=str, help="Start date (YYYY-MM-DD)")
    p_keg_up.add_argument("--nama", type=str, help="New activity name")
    p_keg_up.add_argument("--json", type=str, help="JSON payload")
    p_keg_up.add_argument("--file", type=str, help="JSON file payload")
    p_keg_up.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    p_keg_up_alias = subparsers.add_parser("kegiatan-update", help="Alias for update-kegiatan")
    p_keg_up_alias.add_argument("--id", type=str, required=True, help="Kegiatan ID")
    p_keg_up_alias.add_argument("--tgl-akhir-pelaksanaan", "--tgl-akhir", dest="tgl_akhir_pelaksanaan", type=str, help="End date (YYYY-MM-DD)")
    p_keg_up_alias.add_argument("--tgl-mulai-pelaksanaan", "--tgl-mulai", dest="tgl_mulai_pelaksanaan", type=str, help="Start date (YYYY-MM-DD)")
    p_keg_up_alias.add_argument("--nama", type=str, help="New activity name")
    p_keg_up_alias.add_argument("--json", type=str, help="JSON payload")
    p_keg_up_alias.add_argument("--file", type=str, help="JSON file payload")
    p_keg_up_alias.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # honor / honor-list
    p_hnr = subparsers.add_parser("honor", help="Lookup master honors with token efficiency and filters")
    p_hnr.add_argument("-q", "--q", type=str, help="Search keyword (honor ID, jabatan, kegiatan, dll)")
    p_hnr.add_argument("--search", type=str, help="Alias for -q/--q")
    p_hnr.add_argument("--kegiatan-id", type=str, help="Filter by Kegiatan ID")
    p_hnr.add_argument("--tahun", type=int, help="Filter budget year")
    p_hnr.add_argument("--bulan", type=int, choices=range(1, 13), help="Filter month (1-12)")
    p_hnr.add_argument("--sort-by", type=str, help="Sort field")
    p_hnr.add_argument("--sort-order", choices=["asc", "desc"], default="asc", help="Sort order")
    p_hnr.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode")
    p_hnr.add_argument("--page", type=int, default=1, help="Page number")
    p_hnr.add_argument("--limit", type=int, default=20, help="Items per page")
    p_hnr.add_argument("--per-page", type=int, help="Alias for --limit")

    p_hnr_alias = subparsers.add_parser("honor-list", help="Alias for honor")
    p_hnr_alias.add_argument("-q", "--q", type=str, help="Search keyword")
    p_hnr_alias.add_argument("--search", type=str, help="Alias for -q/--q")
    p_hnr_alias.add_argument("--kegiatan-id", type=str, help="Filter by Kegiatan ID")
    p_hnr_alias.add_argument("--tahun", type=int, help="Filter budget year")
    p_hnr_alias.add_argument("--bulan", type=int, choices=range(1, 13), help="Filter month (1-12)")
    p_hnr_alias.add_argument("--sort-by", type=str, help="Sort field")
    p_hnr_alias.add_argument("--sort-order", choices=["asc", "desc"], default="asc", help="Sort order")
    p_hnr_alias.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode")
    p_hnr_alias.add_argument("--page", type=int, default=1, help="Page number")
    p_hnr_alias.add_argument("--limit", type=int, default=20, help="Items per page")
    p_hnr_alias.add_argument("--per-page", type=int, help="Alias for --limit")

    # honor-detail / honor-get
    p_hnr_det = subparsers.add_parser("honor-detail", help="Get single master honor detail")
    p_hnr_det.add_argument("--id", type=str, required=True, help="Honor ID")
    p_hnr_det_alias = subparsers.add_parser("honor-get", help="Alias for honor-detail")
    p_hnr_det_alias.add_argument("--id", type=str, required=True, help="Honor ID")

    # update-honor / honor-update
    p_hnr_up = subparsers.add_parser("update-honor", help="Update master honor dates or rates (tanggal_akhir_kegiatan, harga, dll)")
    p_hnr_up.add_argument("--id", type=str, required=True, help="Honor ID")
    p_hnr_up.add_argument("--tanggal-akhir-kegiatan", "--tgl-akhir", dest="tanggal_akhir_kegiatan", type=str, help="End date (YYYY-MM-DD)")
    p_hnr_up.add_argument("--harga-per-satuan", type=float, help="Rate per unit")
    p_hnr_up.add_argument("--satuan-honor", type=str, help="Unit of honor (Dokumen, Responden, dll)")
    p_hnr_up.add_argument("--jabatan", type=str, help="Job title (PCL, PML, dll)")
    p_hnr_up.add_argument("--jenis-honor", type=str, help="Type of honor")
    p_hnr_up.add_argument("--json", type=str, help="JSON payload")
    p_hnr_up.add_argument("--file", type=str, help="JSON file payload")
    p_hnr_up.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    p_hnr_up_alias = subparsers.add_parser("honor-update", help="Alias for update-honor")
    p_hnr_up_alias.add_argument("--id", type=str, required=True, help="Honor ID")
    p_hnr_up_alias.add_argument("--tanggal-akhir-kegiatan", "--tgl-akhir", dest="tanggal_akhir_kegiatan", type=str, help="End date (YYYY-MM-DD)")
    p_hnr_up_alias.add_argument("--harga-per-satuan", type=float, help="Rate per unit")
    p_hnr_up_alias.add_argument("--satuan-honor", type=str, help="Unit of honor")
    p_hnr_up_alias.add_argument("--jabatan", type=str, help="Job title")
    p_hnr_up_alias.add_argument("--jenis-honor", type=str, help="Type of honor")
    p_hnr_up_alias.add_argument("--json", type=str, help="JSON payload")
    p_hnr_up_alias.add_argument("--file", type=str, help="JSON file payload")
    p_hnr_up_alias.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # pegawai / pegawai-list
    p_peg = subparsers.add_parser("pegawai", help="Lookup BPS pegawai directory with filters")
    p_peg.add_argument("-q", "--q", type=str, help="Search keyword (name, NIP, email, dll)")
    p_peg.add_argument("--search", type=str, help="Alias for -q/--q")
    p_peg.add_argument("--unit-kerja", type=str, help="Filter by unit kerja")
    p_peg.add_argument("--jabatan", type=str, help="Filter by jabatan")
    p_peg.add_argument("--golongan", type=str, help="Filter by golongan")
    p_peg.add_argument("--is-magang", type=int, choices=[0, 1], help="Filter intern status")
    p_peg.add_argument("--sort-by", type=str, help="Sort field")
    p_peg.add_argument("--sort-order", choices=["asc", "desc"], default="asc", help="Sort order")
    p_peg.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode")
    p_peg.add_argument("--page", type=int, default=1, help="Page number")
    p_peg.add_argument("--limit", type=int, default=20, help="Items per page")
    p_peg.add_argument("--per-page", type=int, help="Alias for --limit")

    p_peg_alias = subparsers.add_parser("pegawai-list", help="Alias for pegawai")
    p_peg_alias.add_argument("-q", "--q", type=str, help="Search keyword")
    p_peg_alias.add_argument("--search", type=str, help="Alias for -q/--q")
    p_peg_alias.add_argument("--unit-kerja", type=str, help="Filter by unit kerja")
    p_peg_alias.add_argument("--jabatan", type=str, help="Filter by jabatan")
    p_peg_alias.add_argument("--golongan", type=str, help="Filter by golongan")
    p_peg_alias.add_argument("--is-magang", type=int, choices=[0, 1], help="Filter intern status")
    p_peg_alias.add_argument("--sort-by", type=str, help="Sort field")
    p_peg_alias.add_argument("--sort-order", choices=["asc", "desc"], default="asc", help="Sort order")
    p_peg_alias.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode")
    p_peg_alias.add_argument("--page", type=int, default=1, help="Page number")
    p_peg_alias.add_argument("--limit", type=int, default=20, help="Items per page")
    p_peg_alias.add_argument("--per-page", type=int, help="Alias for --limit")

    # pegawai-detail / pegawai-get
    p_peg_det = subparsers.add_parser("pegawai-detail", help="Get single pegawai detail by NIP or NIP9")
    p_peg_det.add_argument("--nip", type=str, required=True, help="NIP or NIP9")
    p_peg_det_alias = subparsers.add_parser("pegawai-get", help="Alias for pegawai-detail")
    p_peg_det_alias.add_argument("--nip", type=str, required=True, help="NIP or NIP9")

    # create-pegawai / pegawai-create
    p_peg_cr = subparsers.add_parser("create-pegawai", help="Register a new pegawai to Dokter V")
    p_peg_cr.add_argument("--nama", type=str, help="Full name")
    p_peg_cr.add_argument("--nip", type=str, help="18-digit NIP")
    p_peg_cr.add_argument("--nip9", type=str, help="9-digit NIP")
    p_peg_cr.add_argument("--panggilan", type=str, help="Nickname")
    p_peg_cr.add_argument("--golongan", type=str, help="Golongan (III/a, dll)")
    p_peg_cr.add_argument("--pangkat", type=str, help="Pangkat")
    p_peg_cr.add_argument("--jabatan", type=str, help="Jabatan")
    p_peg_cr.add_argument("--email", type=str, help="Official email")
    p_peg_cr.add_argument("--unit-kerja", type=str, help="Unit kerja")
    p_peg_cr.add_argument("--nomor-wa", type=str, help="WhatsApp number")
    p_peg_cr.add_argument("--atasan-langsung-id", type=str, help="NIP of direct supervisor")
    p_peg_cr.add_argument("--json", type=str, help="JSON payload")
    p_peg_cr.add_argument("--file", type=str, help="JSON file payload")
    p_peg_cr.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    p_peg_cr_alias = subparsers.add_parser("pegawai-create", help="Alias for create-pegawai")
    p_peg_cr_alias.add_argument("--nama", type=str, help="Full name")
    p_peg_cr_alias.add_argument("--nip", type=str, help="18-digit NIP")
    p_peg_cr_alias.add_argument("--nip9", type=str, help="9-digit NIP")
    p_peg_cr_alias.add_argument("--panggilan", type=str, help="Nickname")
    p_peg_cr_alias.add_argument("--golongan", type=str, help="Golongan")
    p_peg_cr_alias.add_argument("--pangkat", type=str, help="Pangkat")
    p_peg_cr_alias.add_argument("--jabatan", type=str, help="Jabatan")
    p_peg_cr_alias.add_argument("--email", type=str, help="Email")
    p_peg_cr_alias.add_argument("--unit-kerja", type=str, help="Unit kerja")
    p_peg_cr_alias.add_argument("--nomor-wa", type=str, help="WhatsApp number")
    p_peg_cr_alias.add_argument("--atasan-langsung-id", type=str, help="NIP of supervisor")
    p_peg_cr_alias.add_argument("--json", type=str, help="JSON payload")
    p_peg_cr_alias.add_argument("--file", type=str, help="JSON file payload")
    p_peg_cr_alias.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # update-pegawai / pegawai-update
    p_peg_up = subparsers.add_parser("update-pegawai", help="Update existing pegawai profile")
    p_peg_up.add_argument("--nip", type=str, required=True, help="NIP or NIP9")
    p_peg_up.add_argument("--nama", type=str, help="Full name")
    p_peg_up.add_argument("--panggilan", type=str, help="Nickname")
    p_peg_up.add_argument("--golongan", type=str, help="Golongan")
    p_peg_up.add_argument("--pangkat", type=str, help="Pangkat")
    p_peg_up.add_argument("--jabatan", type=str, help="Jabatan")
    p_peg_up.add_argument("--email", type=str, help="Email")
    p_peg_up.add_argument("--unit-kerja", type=str, help="Unit kerja")
    p_peg_up.add_argument("--nomor-wa", type=str, help="WhatsApp number")
    p_peg_up.add_argument("--atasan-langsung-id", type=str, help="NIP of supervisor")
    p_peg_up.add_argument("--json", type=str, help="JSON payload")
    p_peg_up.add_argument("--file", type=str, help="JSON file payload")
    p_peg_up.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    p_peg_up_alias = subparsers.add_parser("pegawai-update", help="Alias for update-pegawai")
    p_peg_up_alias.add_argument("--nip", type=str, required=True, help="NIP or NIP9")
    p_peg_up_alias.add_argument("--nama", type=str, help="Full name")
    p_peg_up_alias.add_argument("--panggilan", type=str, help="Nickname")
    p_peg_up_alias.add_argument("--golongan", type=str, help="Golongan")
    p_peg_up_alias.add_argument("--pangkat", type=str, help="Pangkat")
    p_peg_up_alias.add_argument("--jabatan", type=str, help="Jabatan")
    p_peg_up_alias.add_argument("--email", type=str, help="Email")
    p_peg_up_alias.add_argument("--unit-kerja", type=str, help="Unit kerja")
    p_peg_up_alias.add_argument("--nomor-wa", type=str, help="WhatsApp number")
    p_peg_up_alias.add_argument("--atasan-langsung-id", type=str, help="NIP of supervisor")
    p_peg_up_alias.add_argument("--json", type=str, help="JSON payload")
    p_peg_up_alias.add_argument("--file", type=str, help="JSON file payload")
    p_peg_up_alias.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # mitra
    p_mitra = subparsers.add_parser("mitra", help="Lookup BPS partner directory")
    p_mitra.add_argument("--tahun", type=int, default=2026, help="Filter partnership year")
    p_mitra.add_argument("--bulan", type=int, choices=range(1, 13), help="Target month for SBML calculation (1-12)")
    p_mitra.add_argument("--status", type=str, choices=["AKTIF", "TIDAK_AKTIF", "BLACKLISTED"], help="Filter by specific partnership status")
    p_mitra.add_argument("--kecamatan", type=str, help="Filter by subdistrict / kecamatan")
    p_mitra.add_argument("--desa", type=str, help="Filter by village / desa")
    p_mitra.add_argument("--jenis-kelamin", type=str, choices=["L", "P", "Lk", "Pr"], help="Filter by gender")
    p_mitra.add_argument("--posisi", type=str, help="Filter by position (e.g. PCL, PML)")
    p_mitra.add_argument("--has-allocations", type=int, choices=[0, 1], help="Filter partners with (1) or without (0) allocations")
    p_mitra.add_argument("--ids", type=str, help="Batch lookup IDs or ID Sobat separated by comma (e.g. 105,108,61041001)")
    p_mitra.add_argument("--aktif-only", action=argparse.BooleanOptionalAction, default=True, help="Only active partners")
    p_mitra.add_argument("--available-only", action="store_true", default=False, help="Only partners with remaining SBML quota > 0")
    p_mitra.add_argument("--with-sbml", action="store_true", default=False, help="Include SBML quota calculation")
    p_mitra.add_argument("-q", "--q", type=str, help="Search keyword (Name, NIK, ID Sobat)")
    p_mitra.add_argument("--search", type=str, help="Alias for -q/--q")
    p_mitra.add_argument("--sort-by", choices=["nama", "nama_1", "id", "id_sobat", "nik", "created_at"], help="Sort field")
    p_mitra.add_argument("--sort-order", choices=["asc", "desc"], default="asc", help="Sort order")
    p_mitra.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode (~80%% token savings)")
    p_mitra.add_argument("--page", type=int, default=1, help="Page number")
    p_mitra.add_argument("--limit", type=int, default=20, help="Items per page")
    p_mitra.add_argument("--per-page", type=int, help="Alias for --limit")

    # mitra-detail / mitra-get
    p_mitra_detail = subparsers.add_parser("mitra-detail", help="Get full partner detail (supports ID, ID Sobat, or NIK)")
    p_mitra_detail.add_argument("--id", type=str, required=True, help="Partner identifier (ID, ID Sobat, or NIK)")
    p_mitra_detail.add_argument("--with-allocations", action="store_true", default=False, help="Include historical / current allocations")

    p_mitra_get = subparsers.add_parser("mitra-get", help="Alias for mitra-detail")
    p_mitra_get.add_argument("--id", type=str, required=True, help="Partner identifier (ID, ID Sobat, or NIK)")
    p_mitra_get.add_argument("--with-allocations", action="store_true", default=False, help="Include historical / current allocations")

    # update-mitra / mitra-update
    p_update_mitra = subparsers.add_parser("update-mitra", help="Update partner profile and WhatsApp/contact info")
    p_update_mitra.add_argument("--id", type=str, required=True, help="Partner identifier (ID, ID Sobat, or NIK)")
    p_update_mitra.add_argument("--nomor-wa", type=str, help="Latest WhatsApp number (e.g. 0812...)")
    p_update_mitra.add_argument("--no-telp", type=str, help="Phone number")
    p_update_mitra.add_argument("--email", type=str, help="Email address")
    p_update_mitra.add_argument("--alamat-detail", "--alamat", type=str, help="Detailed residential address")
    p_update_mitra.add_argument("--catatan", type=str, help="Notes about the partner")
    p_update_mitra.add_argument("--status-kemitraan", choices=["AKTIF", "TIDAK_AKTIF", "BLACKLISTED"], help="Partnership status")
    p_update_mitra.add_argument("--tahun", type=int, help="Partnership year")
    p_update_mitra.add_argument("--json", type=str, help="Raw JSON string containing update fields")
    p_update_mitra.add_argument("--file", type=str, help="JSON file containing update fields")
    p_update_mitra.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    p_mitra_up = subparsers.add_parser("mitra-update", help="Alias for update-mitra")
    p_mitra_up.add_argument("--id", type=str, required=True, help="Partner identifier (ID, ID Sobat, or NIK)")
    p_mitra_up.add_argument("--nomor-wa", type=str, help="Latest WhatsApp number (e.g. 0812...)")
    p_mitra_up.add_argument("--no-telp", type=str, help="Phone number")
    p_mitra_up.add_argument("--email", type=str, help="Email address")
    p_mitra_up.add_argument("--alamat-detail", "--alamat", type=str, help="Detailed residential address")
    p_mitra_up.add_argument("--catatan", type=str, help="Notes about the partner")
    p_mitra_up.add_argument("--status-kemitraan", choices=["AKTIF", "TIDAK_AKTIF", "BLACKLISTED"], help="Partnership status")
    p_mitra_up.add_argument("--tahun", type=int, help="Partnership year")
    p_mitra_up.add_argument("--json", type=str, help="Raw JSON string containing update fields")
    p_mitra_up.add_argument("--file", type=str, help="JSON file containing update fields")
    p_mitra_up.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # alokasi (list)
    p_alok = subparsers.add_parser("alokasi", help="List existing honor allocations")
    p_alok.add_argument("--tahun", type=int, default=2026, help="Filter budget year")
    p_alok.add_argument("--bulan", type=int, choices=range(1, 13), help="Filter month (1-12)")
    p_alok.add_argument("--mitra-id", type=int, help="Filter by partner ID")
    p_alok.add_argument("--id-sobat", type=str, help="Filter by partner ID Sobat")
    p_alok.add_argument("--kegiatan-id", type=str, help="Filter by activity ID")
    p_alok.add_argument("--honor-id", type=str, help="Filter by honor ID")
    p_alok.add_argument("-q", "--q", type=str, help="Search keyword (mitra, sobat, NIK, kegiatan, no SPK/BAST)")
    p_alok.add_argument("--search", type=str, help="Alias for -q/--q")
    p_alok.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode")
    p_alok.add_argument("--page", type=int, default=1, help="Page number")
    p_alok.add_argument("--limit", type=int, default=20, help="Items per page")
    p_alok.add_argument("--per-page", type=int, help="Alias for --limit")

    # check
    p_check = subparsers.add_parser("check", help="Pre-flight dry-run check (SBML, schedule, active status)")
    p_check.add_argument("--mitra-id", type=int, help="Partner database ID")
    p_check.add_argument("--id-sobat", type=str, help="Partner ID Sobat")
    p_check.add_argument("--honor-id", type=str, required=True, help="Honor ID to allocate")
    p_check.add_argument("--target", type=float, required=True, help="Volume / target amount")
    p_check.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # allocate
    p_alloc = subparsers.add_parser("allocate", help="Create single honor allocation (emits SPK & BAST)")
    p_alloc.add_argument("--mitra-id", type=int, help="Partner database ID")
    p_alloc.add_argument("--id-sobat", type=str, help="Partner ID Sobat")
    p_alloc.add_argument("--honor-id", type=str, required=True, help="Honor ID to allocate")
    p_alloc.add_argument("--target", type=float, required=True, help="Volume / target amount")
    p_alloc.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # batch-allocate
    p_batch = subparsers.add_parser("batch-allocate", help="Create batch honor allocations")
    p_batch.add_argument("--file", type=str, help="Path to JSON file containing allocations")
    p_batch.add_argument("--json", type=str, help="JSON string containing allocations")
    p_batch.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    # kontrak
    p_kontrak = subparsers.add_parser("kontrak", help="Lookup SPK contract documents and PDF download URLs")
    p_kontrak.add_argument("--mitra-id", type=int, help="Filter by partner ID")
    p_kontrak.add_argument("--id-sobat", type=str, help="Filter by partner ID Sobat")
    p_kontrak.add_argument("--kegiatan-id", type=str, help="Filter by activity ID")
    p_kontrak.add_argument("--bulan", type=int, choices=range(1, 13), help="Filter by month (1-12)")
    p_kontrak.add_argument("--tahun", type=int, default=2026, help="Filter by year")
    p_kontrak.add_argument("-q", "--q", type=str, help="Search document number or partner name")
    p_kontrak.add_argument("--search", type=str, help="Alias for -q/--q")
    p_kontrak.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode")
    p_kontrak.add_argument("--page", type=int, default=1, help="Page number")
    p_kontrak.add_argument("--limit", type=int, default=20, help="Items per page")
    p_kontrak.add_argument("--per-page", type=int, help="Alias for --limit")

    # bast
    p_bast = subparsers.add_parser("bast", help="Lookup BAST documents and PDF download URLs")
    p_bast.add_argument("--mitra-id", type=int, help="Filter by partner ID")
    p_bast.add_argument("--id-sobat", type=str, help="Filter by partner ID Sobat")
    p_bast.add_argument("--kegiatan-id", type=str, help="Filter by activity ID")
    p_bast.add_argument("--bulan", type=int, choices=range(1, 13), help="Filter by month (1-12)")
    p_bast.add_argument("--tahun", type=int, default=2026, help="Filter by year")
    p_bast.add_argument("-q", "--q", type=str, help="Search document number or partner name")
    p_bast.add_argument("--search", type=str, help="Alias for -q/--q")
    p_bast.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode")
    p_bast.add_argument("--page", type=int, default=1, help="Page number")
    p_bast.add_argument("--limit", type=int, default=20, help="Items per page")
    p_bast.add_argument("--per-page", type=int, help="Alias for --limit")

    # audit-logs
    p_audit = subparsers.add_parser("audit-logs", help="Lookup or inspect mutation audit logs")
    p_audit.add_argument("--id", type=int, help="View detail state diff for specific audit log ID")
    p_audit.add_argument("--only-rollbackable", action="store_true", default=False, help="Only show rollbackable logs")
    p_audit.add_argument("--compact", action=argparse.BooleanOptionalAction, default=True, help="Enable compact mode")
    p_audit.add_argument("--page", type=int, default=1, help="Page number")
    p_audit.add_argument("--limit", type=int, default=20, help="Items per page")
    p_audit.add_argument("--per-page", type=int, help="Alias for --limit")

    # rollback
    p_rollback = subparsers.add_parser("rollback", help="Undo/rollback an allocation mutation")
    p_rollback.add_argument("--id", type=int, required=True, help="Audit log ID to rollback")
    p_rollback.add_argument("--reason", type=str, default="Dibatalkan oleh AI Agent", help="Rollback reason")
    p_rollback.add_argument("--sender", type=str, help="WhatsApp sender JID for authorization check")

    args = parser.parse_args()

    handlers = {
        "status": cmd_status,
        "check-access": cmd_check_access,
        "kegiatan": cmd_kegiatan,
        "rename-kegiatan": cmd_rename_kegiatan,
        "rename-id": cmd_rename_kegiatan,
        "mitra": cmd_mitra,
        "mitra-detail": cmd_mitra_detail,
        "mitra-get": cmd_mitra_detail,
        "update-mitra": cmd_update_mitra,
        "mitra-update": cmd_update_mitra,
        "alokasi": cmd_alokasi_list,
        "check": cmd_check,
        "allocate": cmd_allocate,
        "batch-allocate": cmd_batch_allocate,
        "kontrak": cmd_kontrak,
        "bast": cmd_bast,
        "audit-logs": cmd_audit_logs,
        "rollback": cmd_rollback,
        "kegiatan-detail": cmd_kegiatan_detail,
        "kegiatan-get": cmd_kegiatan_detail,
        "update-kegiatan": cmd_update_kegiatan,
        "kegiatan-update": cmd_update_kegiatan,
        "honor": cmd_honor,
        "honor-list": cmd_honor,
        "honor-detail": cmd_honor_detail,
        "honor-get": cmd_honor_detail,
        "update-honor": cmd_update_honor,
        "honor-update": cmd_update_honor,
        "pegawai": cmd_pegawai,
        "pegawai-list": cmd_pegawai,
        "pegawai-detail": cmd_pegawai_detail,
        "pegawai-get": cmd_pegawai_detail,
        "create-pegawai": cmd_create_pegawai,
        "pegawai-create": cmd_create_pegawai,
        "update-pegawai": cmd_update_pegawai,
        "pegawai-update": cmd_update_pegawai,
    }

    return handlers[args.subcommand](args)


if __name__ == "__main__":
    sys.exit(main())
