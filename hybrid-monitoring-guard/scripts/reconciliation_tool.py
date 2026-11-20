#!/usr/bin/env python3
"""
reconciliation_tool.py - Hybrid Monitoring Reconciliation & Risk Guard Utility
Performs deterministic discrepancy auditing between automated system scraping (Fasih/Cerdas)
and field-reported manual Google Sheets for statistical surveys.
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

def get_sheets_token() -> str:
    """Retrieve Google Sheets access token from gdrive skill helper or environment."""
    token = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if token:
        return token
    
    # Try importing from standard gdrive skill paths
    candidates = [
        "/app/workspaces/default/.agents/skills/gdrive/scripts",
        "/app/data/custom-skills/gdrive/scripts",
        "skills/gdrive/scripts"
    ]
    for p in candidates:
        if os.path.exists(p) and p not in sys.path:
            sys.path.append(p)
            
    try:
        from gdrive_tool import get_valid_access_token
        return get_valid_access_token()
    except Exception as e:
        sys.stderr.write(f"Warning: Could not get token via gdrive_tool: {e}\n")
        return ""

def format_risk_warning(kegiatan: str, sistem_name: str = "Fasih", sheet_name: str = "Google Sheets Monitoring") -> str:
    """Generate standardized, polite, and actionable risk disclosure for WhatsApp."""
    return (
        f"⚠️ *Catatan Penting terkait Rekap Hybrid ({kegiatan})*\n\n"
        f"Perlu diperhatikan yaa, data dari tarikan sistem *{sistem_name}* adalah _ground truth server_ (realtime sistem), "
        f"sedangkan rincian di *{sheet_name}* merupakan isian mandiri (_self-reported_) oleh teman-teman mitra di lapangan.\n\n"
        f"• *Potensi Selisih (Lag Waktu)*: Sangat wajar jika ada perbedaan angka antara dokumen yang sudah selesai diwawancarai mitra "
        f"dengan yang statusnya benar-benar sudah di-klik `SUBMIT` atau `COMPLETED` di web {sistem_name}.\n"
        f"• *Saran Tindak Lanjut*: Jika angka monitoring manual lebih tinggi dari {sistem_name}, mohon PML segera mengingatkan PPL "
        f"untuk mengunggah dan men-submit kuesioner sebelum batas akhir penutupan yaa 🙏"
    )

def compare_data(fasih_records: List[Dict[str, Any]], manual_records: List[Dict[str, Any]], key_field: str = "nama") -> Dict[str, Any]:
    """Compare two sets of officer records and identify discrepancies."""
    fasih_map = {r[key_field].strip().lower(): r for r in fasih_records if key_field in r}
    manual_map = {r[key_field].strip().lower(): r for r in manual_records if key_field in r}
    
    all_keys = sorted(list(set(fasih_map.keys()) | set(manual_map.keys())))
    
    results = []
    total_fasih = 0
    total_manual = 0
    total_gap = 0
    
    for k in all_keys:
        f_val = fasih_map.get(k, {}).get("submit", 0)
        m_val = manual_map.get(k, {}).get("submit", 0)
        gap = f_val - m_val
        
        status = "MATCH"
        if gap > 0:
            status = "UNDERREPORT_MANUAL"  # Fasih higher than sheet
        elif gap < 0:
            status = "OVERREPORT_MANUAL"   # Sheet higher than Fasih
            
        total_fasih += f_val
        total_manual += m_val
        total_gap += gap
        
        results.append({
            "key": k,
            "nama_resmi": manual_map.get(k, {}).get("nama_resmi") or fasih_map.get(k, {}).get("nama_resmi") or k,
            "fasih_submit": f_val,
            "manual_report": m_val,
            "gap": gap,
            "status": status
        })
        
    return {
        "summary": {
            "total_petugas": len(results),
            "total_fasih_submit": total_fasih,
            "total_manual_report": total_manual,
            "net_gap": total_gap,
            "discrepancy_count": sum(1 for r in results if r["status"] != "MATCH")
        },
        "details": results
    }

def cmd_format_warning(args):
    print(format_risk_warning(args.kegiatan, args.sistem, args.sheet))

def cmd_audit_example(args):
    print("Hybrid Monitoring Reconciliation Audit - Ready")
    print(json.dumps({
        "status": "ready",
        "description": "Engine audit rekonsiliasi aktif untuk membandingkan tarikan otomatis vs input manual mitra."
    }, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Hybrid Monitoring Reconciliation Guard CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")
    
    # format-warning
    p_warn = subparsers.add_parser("format-warning", help="Format WhatsApp risk disclaimer")
    p_warn.add_argument("--kegiatan", default="SPDT NTP 2026", help="Nama kegiatan survei/sensus")
    p_warn.add_argument("--sistem", default="Fasih", help="Nama sistem otomatis (Fasih/Cerdas)")
    p_warn.add_argument("--sheet", default="Google Sheets Monitoring", help="Nama lembar manual")
    p_warn.set_defaults(func=cmd_format_warning)
    
    # audit
    p_audit = subparsers.add_parser("audit", help="Audit rekonsiliasi selisih")
    p_audit.set_defaults(func=cmd_audit_example)
    
    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        sys.exit(1)
        
    args.func(args)

if __name__ == "__main__":
    main()
