#!/usr/bin/env python3
"""
pok_tool.py - Petunjuk Operasional Kegiatan (POK) Manager & Explorer for BPS Kabupaten Mempawah
Supports querying, searching, comparing, and ingesting POK revisions (2026, 2027, etc.).
"""

import sys
import os
import re
import argparse
import subprocess
from pathlib import Path

WORKSPACE_DEFAULT = Path("/app/workspaces/default")
WORKSPACE_BPS = Path("/app/workspaces/bps-mempawah")

def get_pok_file(year: int = 2027, workspace: Path = WORKSPACE_DEFAULT) -> Path:
    f = workspace / f"knowledge/universal/pok_bps_mempawah_{year}.md"
    if not f.is_file() and WORKSPACE_BPS.is_dir():
        f = WORKSPACE_BPS / f"knowledge/universal/pok_bps_mempawah_{year}.md"
    return f

def cmd_summary(args):
    year = args.year
    f = get_pok_file(year)
    if not f.is_file():
        print(f"Error: berkas POK {year} tidak ditemukan di {f}")
        sys.exit(1)

    content = f.read_text(encoding="utf-8")
    print(f"=== RINGKASAN POK BPS KABUPATEN MEMPAWAH TA {year} ===")
    
    # Extract total pagu
    m_total = re.search(r"Total (?:Alokasi Anggaran|Pagu Anggaran).*?\*\*Rp ([\d\.,]+).*?\*\*", content)
    if m_total:
        print(f"Total Pagu Anggaran : Rp {m_total.group(1)}")
    
    # Extract programs
    print("\n--- Program Utama ---")
    for m in re.finditer(r"\d+\.\s+\*\*(Program [^\*]+)\*\*:\s+\*\*Rp ([\d\.,]+).*?\*\*", content):
        print(f"• {m.group(1)}: Rp {m.group(2)}")
        
    # Extract Kegiatan table
    print(f"\n--- Rekapitulasi Kegiatan TA {year} ---")
    in_table = False
    for line in content.split("\n"):
        if "| Kode | Uraian Kegiatan" in line:
            in_table = True
            continue
        if in_table:
            if not line.strip() or line.startswith("---") or line.startswith("##"):
                break
            if line.startswith("|") and not line.startswith("| :---"):
                parts = [p.strip() for p in line.strip().split("|") if p.strip()]
                if len(parts) >= 3:
                    code = parts[0].replace("**", "")
                    name = parts[1].replace("**", "")
                    cost = parts[2].replace("**", "")
                    print(f"[{code:>4}] {name:<65} : Rp {cost:>14}")

def cmd_search(args):
    query = args.query.lower()
    years = [2027] if args.year == 2027 else ([2026] if args.year == 2026 else [2027, 2026])
    
    found_any = False
    for y in years:
        f = get_pok_file(y)
        if not f.is_file():
            continue
        
        content = f.read_text(encoding="utf-8")
        lines = content.split("\n")
        matches = []
        current_section = f"POK {y}"
        
        for i, line in enumerate(lines):
            if line.startswith("### Halaman ") or line.startswith("## "):
                current_section = line.strip("# ").strip()
            
            if query in line.lower():
                # Grab context (surrounding lines)
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                ctx = "\n".join(lines[start:end])
                matches.append((current_section, line.strip(), ctx))
        
        if matches:
            found_any = True
            print(f"=== HASIL PENCARIAN '{args.query}' PADA POK {y} ({len(matches)} temuan) ===")
            for sec, match_line, ctx in matches[:args.limit]:
                print(f"\n📍 Lokasi: {sec}")
                print(f"   Baris : {match_line}")
            if len(matches) > args.limit:
                print(f"\n... dan {len(matches) - args.limit} temuan lainnya (gunakan --limit untuk melihat lebih banyak).")
            print()
            
    if not found_any:
        print(f"Tidak ditemukan rincian dengan kata kunci '{args.query}' pada POK {years}.")

def cmd_compare(args):
    f26 = get_pok_file(2026)
    f27 = get_pok_file(2027)
    
    if not f26.is_file() or not f27.is_file():
        print("Error: berkas POK 2026 atau 2027 belum lengkap.")
        sys.exit(1)
        
    code_filter = args.kegiatan
    print(f"=== PERBANDINGAN ALOKASI KEGIATAN POK 2026 vs 2027 {'(' + code_filter + ')' if code_filter else ''} ===")
    
    # Parse 2026 table
    c26 = {}
    for line in f26.read_text(encoding="utf-8").split("\n"):
        if line.startswith("|") and not line.startswith("| :---") and not line.startswith("| Kode"):
            parts = [p.strip().replace("**", "") for p in line.split("|") if p.strip()]
            if len(parts) >= 3 and parts[0].isdigit():
                c26[parts[0]] = (parts[1], parts[2].replace("Rp", "").replace(",-", "").strip())
                
    # Parse 2027 table
    c27 = {}
    for line in f27.read_text(encoding="utf-8").split("\n"):
        if line.startswith("|") and not line.startswith("| :---") and not line.startswith("| Kode"):
            parts = [p.strip().replace("**", "") for p in line.split("|") if p.strip()]
            if len(parts) >= 3 and parts[0].isdigit():
                c27[parts[0]] = (parts[1], parts[2].replace("Rp", "").replace(",-", "").strip())

    all_codes = sorted(set(list(c26.keys()) + list(c27.keys())))
    if code_filter:
        all_codes = [c for c in all_codes if c == code_filter]

    print(f"{'Kode':<6} | {'Nama Kegiatan':<45} | {'Pagu 2026 (Rp)':<16} | {'Pagu 2027 (Rp)':<16}")
    print("-" * 90)
    for c in all_codes:
        name = (c27.get(c) or c26.get(c) or ("-", ""))[0]
        cost26 = c26.get(c, ("-", "-"))[1]
        cost27 = c27.get(c, ("-", "-"))[1]
        print(f"{c:<6} | {name[:45]:<45} | {cost26:>16} | {cost27:>16}")

def cmd_ingest(args):
    file_path = Path(args.file)
    if not file_path.is_file():
        print(f"Error: File tidak ditemukan: {file_path}")
        sys.exit(1)
        
    year = args.year
    rev_info = args.rev or "Pemutakhiran Revisi"
    print(f"[*] Mengimpor dan mengekstrak POK {year} dari: {file_path}")
    
    cmd = ["pdftotext", "-layout", str(file_path), "-"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error menjalankan pdftotext: {res.stderr}")
        sys.exit(1)
        
    pages = [p for p in res.stdout.split("\x0c") if p.strip()]
    print(f"[+] Berhasil membaca {len(pages)} halaman PDF.")
    
    # Save PDF asset
    asset_target_default = WORKSPACE_DEFAULT / f"knowledge/assets/POK_BPS_Mempawah_{year}_{Path(args.file).name}"
    asset_target_bps = WORKSPACE_BPS / f"knowledge/assets/POK_BPS_Mempawah_{year}_{Path(args.file).name}"
    
    asset_target_default.parent.mkdir(parents=True, exist_ok=True)
    asset_target_bps.parent.mkdir(parents=True, exist_ok=True)
    
    import shutil
    shutil.copy2(file_path, asset_target_default)
    if WORKSPACE_BPS.is_dir():
        shutil.copy2(file_path, asset_target_bps)
    print(f"[+] Berkas master PDF disalin ke {asset_target_default}")
    
    print("[*] Menjalankan grooming index knowledge base...")
    subprocess.run(["aina", "kb", "groom", "--workspace", str(WORKSPACE_DEFAULT)], check=False)
    if WORKSPACE_BPS.is_dir():
        subprocess.run(["aina", "kb", "groom", "--workspace", str(WORKSPACE_BPS)], check=False)
    print("✅ Ingest POK selesai!")

def main():
    parser = argparse.ArgumentParser(description="Aina POK Manager & Explorer")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    
    # search
    p_search = subparsers.add_parser("search", help="Cari item/honor/kegiatan di POK")
    p_search.add_argument("query", help="Kata kunci pencarian (misal: SPKRT, honor, SEEA, 2903, translok)")
    p_search.add_argument("--year", type=int, choices=[2026, 2027], default=None, help="Tahun anggaran (default: semua)")
    p_search.add_argument("--limit", type=int, default=10, help="Maksimal hasil tampil")
    p_search.set_defaults(func=cmd_search)
    
    # summary
    p_sum = subparsers.add_parser("summary", help="Ringkasan pagu program dan kegiatan")
    p_sum.add_argument("year", type=int, nargs="?", default=2027, help="Tahun anggaran (default: 2027)")
    p_sum.set_defaults(func=cmd_summary)
    
    # compare
    p_comp = subparsers.add_parser("compare", help="Bandingkan alokasi kegiatan 2026 vs 2027")
    p_comp.add_argument("--kegiatan", help="Kode kegiatan spesifik (contoh: 2903)")
    p_comp.set_defaults(func=cmd_compare)
    
    # ingest
    p_ing = subparsers.add_parser("ingest", help="Ingest draf/revisi POK baru ke knowledge base")
    p_ing.add_argument("--file", required=True, help="Path ke berkas PDF revisi POK")
    p_ing.add_argument("--year", type=int, default=2027, help="Tahun anggaran")
    p_ing.add_argument("--rev", help="Catatan revisi")
    p_ing.set_defaults(func=cmd_ingest)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
