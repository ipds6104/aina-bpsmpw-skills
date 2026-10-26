#!/usr/bin/env python3
"""
data_pejabat_progress_tool.py - CLI Tool untuk Monitoring & Tabulasi Progress Pemadanan Data Pejabat Mempawah 6104
Membaca sheet 'Data OPEN Match', menghitung progress kolom BD (selain open & draft) vs total,
menghitung per Instansi BKSDM (kolom AT), memperbarui tab sheet 'Rekap_Progress_BKSDM' dengan FORMULA LIVE & pewarnaan otomatis,
serta mengenerate visual dashboard screenshot via Patchright.
"""

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# Setup path to import gdrive_tool
GDRIVE_TOOL_PATH = Path("/app/skills/gdrive/scripts")
if str(GDRIVE_TOOL_PATH) not in sys.path:
    sys.path.insert(0, str(GDRIVE_TOOL_PATH))

try:
    from gdrive_tool import get_valid_access_token, SHEETS_API_BASE
except ImportError:
    fallback_gdrive = Path(__file__).resolve().parent.parent.parent.parent / "skills" / "gdrive" / "scripts"
    sys.path.insert(0, str(fallback_gdrive))
    from gdrive_tool import get_valid_access_token, SHEETS_API_BASE

import requests
from patchright.async_api import async_playwright

SPREADSHEET_ID = os.getenv("PEJABAT_SPREADSHEET_ID", "1ZpwvQLXJUCwB5yqp7Y5mFMFv1JnHWw3WYP1ebcNsI1U")
SOURCE_TAB = "Data OPEN Match"
TARGET_TAB = "Rekap_Progress_BKSDM"


def fetch_open_match_data(spreadsheet_id=SPREADSHEET_ID):
    """Ambil seluruh data dari sheet 'Data OPEN Match'."""
    token = get_valid_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/'{SOURCE_TAB}'!A2:BD"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise RuntimeError(f"Gagal mengambil data dari Google Sheets: {res.text}")
    return res.json().get("values", [])


def compute_statistics(rows):
    """Hitung statistik keseluruhan dan per-Instansi BKSDM."""
    total_rows = len(rows)
    instansi_dict = defaultdict(lambda: {"total": 0, "done": 0, "open": 0, "statuses": defaultdict(int)})
    status_counter = defaultdict(int)

    for r in rows:
        instansi = r[45].strip() if len(r) > 45 and r[45] else "(Tanpa Instansi BKSDM)"
        st = r[55].strip().lower() if len(r) > 55 and r[55] else "open"

        status_counter[st] += 1
        instansi_dict[instansi]["total"] += 1
        instansi_dict[instansi]["statuses"][st] += 1

        if st in ["open", "draft", ""]:
            instansi_dict[instansi]["open"] += 1
        else:
            instansi_dict[instansi]["done"] += 1

    total_done = sum(v["done"] for v in instansi_dict.values())
    total_open = sum(v["open"] for v in instansi_dict.values())
    overall_pct = (total_done / total_rows * 100) if total_rows > 0 else 0

    with_instansi = [item for item in instansi_dict.items() if item[0] != "(Tanpa Instansi BKSDM)"]
    with_instansi.sort(key=lambda x: (-x[1]["total"], -(x[1]["done"] / x[1]["total"] if x[1]["total"] > 0 else 0)))
    without_instansi = [item for item in instansi_dict.items() if item[0] == "(Tanpa Instansi BKSDM)"]

    sorted_instansi = with_instansi + without_instansi

    return {
        "total_rows": total_rows,
        "total_done": total_done,
        "total_open": total_open,
        "overall_pct": overall_pct,
        "status_counter": status_counter,
        "sorted_instansi": sorted_instansi,
    }


def cmd_summary(args):
    """Tampilkan ringkasan teks progress ke terminal."""
    rows = fetch_open_match_data(args.spreadsheet_id)
    stats = compute_statistics(rows)

    if args.json:
        print(json.dumps({
            "total_rows": stats["total_rows"],
            "total_done": stats["total_done"],
            "total_open": stats["total_open"],
            "overall_pct": stats["overall_pct"],
            "status_breakdown": stats["status_counter"],
            "instansi_count": len(stats["sorted_instansi"])
        }, indent=2))
        return

    print("=== RINGKASAN PROGRESS PEMADANAN PEJABAT MEMPAWAH (DATA OPEN MATCH) ===")
    print(f"• Total Target Penugasan : {stats['total_rows']:,} baris")
    print(f"• Sudah Diproses         : {stats['total_done']:,} baris ({stats['overall_pct']:.2f}%) [Selain open & draft]")
    print(f"• Belum Diproses         : {stats['total_open']:,} baris ({100-stats['overall_pct']:.2f}%) [Masih open/draft]")
    print("\n=== RINCIAN STATUS ASSIGNMENT (KOLOM BD) ===")
    for s, cnt in sorted(stats["status_counter"].items(), key=lambda x: -x[1]):
        print(f"• {s:<30} : {cnt:>4} baris ({cnt/stats['total_rows']*100:.2f}%)")

    print(f"\n=== TOP 10 INSTANSI BKSDM (DARI TOTAL {len(stats['sorted_instansi'])}) ===")
    for inst, d in stats["sorted_instansi"][:10]:
        pct = (d["done"] / d["total"] * 100) if d["total"] > 0 else 0
        print(f"• {inst[:40]:<40} | Target: {d['total']:>3} | Selesai: {d['done']:>3} | Progress: {pct:>6.2f}%")


def ensure_target_sheet_exists(token, spreadsheet_id):
    """Pastikan tab TARGET_TAB ada di Google Sheets, jika belum buat baru."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    meta_res = requests.get(f"{SHEETS_API_BASE}/{spreadsheet_id}", headers=headers)
    sheets = meta_res.json().get("sheets", [])
    for s in sheets:
        if s["properties"]["title"] == TARGET_TAB:
            return s["properties"]["sheetId"]

    body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": TARGET_TAB,
                        "gridProperties": {"rowCount": 250, "columnCount": 10}
                    }
                }
            }
        ]
    }
    res = requests.post(f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate", headers=headers, json=body)
    return res.json()["replies"][0]["addSheet"]["properties"]["sheetId"]


def cmd_sync_sheet(args):
    """
    Sinkronkan tab 'Rekap_Progress_BKSDM' di Google Sheets menggunakan LIVE FORMULAS.
    Karena formula merujuk langsung ke tab 'Data OPEN Match', setiap kali sumber data
    diperbarui setiap jam, tab ini akan otomatis mengkalkulasi ulang secara realtime tanpa perlu run script lagi.
    """
    token = get_valid_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    spreadsheet_id = args.spreadsheet_id

    rows = fetch_open_match_data(spreadsheet_id)
    stats = compute_statistics(rows)
    sheet_id = ensure_target_sheet_exists(token, spreadsheet_id)

    # Susun list instansi unik (diurutkan berdasarkan total terbesar)
    instansi_list = [item[0] for item in stats["sorted_instansi"]]

    # 1. Bangun Grid dengan Live Formulas (Semicolon delimiter untuk locale id_ID)
    grid = []
    grid.append(["REKAPITULASI PROGRESS PEMADANAN PEJABAT MEMPAWAH (SE2026 - DATA OPEN MATCH)", "", "", "", "", "", ""])
    grid.append(["Formula Dinamis (Live Real-Time) • Otomatis Terkalkulasi Ulang Saat Sheet 'Data OPEN Match' Berubah", "", "", "", "", "", ""])
    grid.append([])

    # SECTION A: Ringkasan Progress Keseluruhan (Live Formula)
    grid.append(["A. RINGKASAN PROGRESS KESELURUHAN (LIVE FORMULA)", "", "", "", "", "", ""])
    grid.append(["Indikator", "Jumlah (Baris)", "Persentase", "Keterangan", "", "", ""])
    # Row 6: Total Baris
    grid.append(["Total Baris Target", "=COUNTA('Data OPEN Match'!A2:A)", "=1", "Semua baris target penugasan di Data OPEN Match", "", "", ""])
    # Row 7: Selesai / Selain Open & Draft
    grid.append(["Sudah Diproses (Selain Open & Draft)", "=B6-B8", "=B7/B6", "Baris selain status open dan draft", "", "", ""])
    # Row 8: Masih Open / Draft
    grid.append(["Belum Diproses (Masih Open/Draft)", "=COUNTIF('Data OPEN Match'!BD:BD; \"open\") + COUNTIF('Data OPEN Match'!BD:BD; \"draft\")", "=B8/B6", "Baris dengan status open atau draft", "", "", ""])
    grid.append([])

    # SECTION B: Rincian Status Assignment (Live Formula)
    grid.append(["B. RINCIAN STATUS ASSIGNMENT (KOLOM BD - LIVE FORMULA)", "", "", "", "", "", ""])
    grid.append(["Status Assignment", "Jumlah", "Persentase", "Kategori", "", "", ""])
    statuses = [
        ("open", "Belum Diproses"),
        ("submitted respondent", "Sudah Diproses"),
        ("approved by pengawas", "Sudah Diproses"),
        ("edited by admin kabupaten", "Sudah Diproses"),
        ("completed by admin kabupaten", "Sudah Diproses")
    ]
    for idx, (st, kat) in enumerate(statuses, start=12):
        grid.append([st, f"=COUNTIF('Data OPEN Match'!BD:BD; \"{st}\")", f"=B{idx}/$B$6", kat, "", "", ""])
    grid.append([])

    # SECTION C: Progress per Instansi BKSDM (Live Formula)
    grid.append(["C. PROGRESS PER INSTANSI BKSDM (KOLOM AT - LIVE FORMULA)", "", "", "", "", "", ""])
    grid.append(["No", "Instansi BKSDM", "Total Target", "Selesai (Selain Open/Draft)", "Belum (Open/Draft)", "Progress (%)", "Kategori Status"])

    start_row = 20
    for i, inst in enumerate(instansi_list):
        row_num = start_row + i
        if inst == "(Tanpa Instansi BKSDM)":
            c_formula = "=COUNTIFS('Data OPEN Match'!BD:BD; \"<>\"; 'Data OPEN Match'!AT:AT; \"\")"
            d_formula = "=COUNTIFS('Data OPEN Match'!AT:AT; \"\"; 'Data OPEN Match'!BD:BD; \"<>\"; 'Data OPEN Match'!BD:BD; \"<>open\"; 'Data OPEN Match'!BD:BD; \"<>draft\")"
        else:
            clean_inst = inst.replace('"', '""')
            c_formula = f"=COUNTIF('Data OPEN Match'!AT:AT; \"{clean_inst}\")"
            d_formula = f"=COUNTIFS('Data OPEN Match'!AT:AT; \"{clean_inst}\"; 'Data OPEN Match'!BD:BD; \"<>\"; 'Data OPEN Match'!BD:BD; \"<>open\"; 'Data OPEN Match'!BD:BD; \"<>draft\")"

        e_formula = f"=C{row_num}-D{row_num}"
        f_formula = f"=IF(C{row_num}>0; D{row_num}/C{row_num}; 0)"
        g_formula = f"=IF(F{row_num}>=0,75; \"Sangat Tinggi (>= 75%)\"; IF(F{row_num}>=0,5; \"Tinggi (50% - 74%)\"; IF(F{row_num}>=0,25; \"Sedang (25% - 49%)\"; IF(F{row_num}>0; \"Rendah (1% - 24%)\"; \"Belum Berjalan (0%)\"))))"

        grid.append([i + 1, inst, c_formula, d_formula, e_formula, f_formula, g_formula])

    # Total Row
    last_data_row = start_row + len(instansi_list) - 1
    tot_row_num = last_data_row + 1
    grid.append([
        "",
        "TOTAL KESELURUHAN",
        f"=SUM(C{start_row}:C{last_data_row})",
        f"=SUM(D{start_row}:D{last_data_row})",
        f"=SUM(E{start_row}:E{last_data_row})",
        f"=IF(C{tot_row_num}>0; D{tot_row_num}/C{tot_row_num}; 0)",
        f"=IF(F{tot_row_num}>=0,75; \"Sangat Tinggi\"; IF(F{tot_row_num}>=0,5; \"Tinggi\"; IF(F{tot_row_num}>=0,25; \"Sedang\"; \"Rendah\")))"
    ])

    # 2. Bersihkan & Tulis Nilai ke Google Sheets
    requests.post(f"{SHEETS_API_BASE}/{spreadsheet_id}/values/'{TARGET_TAB}'!A1:Z500:clear", headers=headers)
    put_res = requests.put(
        f"{SHEETS_API_BASE}/{spreadsheet_id}/values/'{TARGET_TAB}'!A1?valueInputOption=USER_ENTERED",
        headers=headers,
        json={"values": grid}
    )
    if put_res.status_code != 200:
        raise RuntimeError(f"Gagal menulis nilai: {put_res.text}")

    # 3. Format Penataan Tampilan & Conditional Formatting
    requests_list = []

    # Title styling (Row 1-2)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 7},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 12, "foregroundColor": {"red": 0.1, "green": 0.2, "blue": 0.5}}}},
            "fields": "userEnteredFormat(textFormat)"
        }
    })

    # Table headers (Navy background, White text, Bold)
    for hrow in [4, 10, 18]:
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": hrow, "endRowIndex": hrow + 1, "startColumnIndex": 0, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.12, "green": 0.23, "blue": 0.54},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        })

    # Section headers (Light slate background)
    for srow in [3, 9, 17]:
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": srow, "endRowIndex": srow + 1, "startColumnIndex": 0, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.90, "green": 0.92, "blue": 0.95},
                        "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": {"red": 0.1, "green": 0.2, "blue": 0.3}}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        })

    # Number Formats: Persentase (0,00%)
    percent_ranges = [
        {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": 8, "startColumnIndex": 2, "endColumnIndex": 3},
        {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 16, "startColumnIndex": 2, "endColumnIndex": 3},
        {"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": tot_row_num, "startColumnIndex": 5, "endColumnIndex": 6},
    ]
    for pr in percent_ranges:
        requests_list.append({
            "repeatCell": {
                "range": pr,
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "PERCENT", "pattern": "0.00%"},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"
            }
        })

    # Number Formats: Integer (#,##0)
    number_ranges = [
        {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": 8, "startColumnIndex": 1, "endColumnIndex": 2},
        {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 16, "startColumnIndex": 1, "endColumnIndex": 2},
        {"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": tot_row_num, "startColumnIndex": 2, "endColumnIndex": 5},
    ]
    for nr in number_ranges:
        requests_list.append({
            "repeatCell": {
                "range": nr,
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "NUMBER", "pattern": "#,##0"},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"
            }
        })

    # Total Row styling (Bold & Highlight)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": tot_row_num - 1, "endRowIndex": tot_row_num, "startColumnIndex": 0, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.88, "green": 0.92, "blue": 0.98},
                    "textFormat": {"bold": True}
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)"
        }
    })

    # 4. CONDITIONAL FORMATTING RULES (LIVE COLORING):
    # Rule 1: >= 75% -> Dark Soft Green
    requests_list.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": tot_row_num - 1, "startColumnIndex": 5, "endColumnIndex": 6}],
                "booleanRule": {
                    "condition": {"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": "0,75"}]},
                    "format": {
                        "backgroundColor": {"red": 0.82, "green": 0.94, "blue": 0.86},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 0.06, "green": 0.38, "blue": 0.20}}
                    }
                }
            },
            "index": 0
        }
    })
    # Rule 2: 50% - 74% -> Light Green
    requests_list.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": tot_row_num - 1, "startColumnIndex": 5, "endColumnIndex": 6}],
                "booleanRule": {
                    "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "0,50"}, {"userEnteredValue": "0,7499"}]},
                    "format": {
                        "backgroundColor": {"red": 0.88, "green": 0.96, "blue": 0.88},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 0.08, "green": 0.40, "blue": 0.15}}
                    }
                }
            },
            "index": 1
        }
    })
    # Rule 3: 25% - 49% -> Amber Yellow
    requests_list.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": tot_row_num - 1, "startColumnIndex": 5, "endColumnIndex": 6}],
                "booleanRule": {
                    "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "0,25"}, {"userEnteredValue": "0,4999"}]},
                    "format": {
                        "backgroundColor": {"red": 1.00, "green": 0.95, "blue": 0.80},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 0.50, "green": 0.35, "blue": 0.02}}
                    }
                }
            },
            "index": 2
        }
    })
    # Rule 4: 1% - 24% -> Light Orange
    requests_list.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": tot_row_num - 1, "startColumnIndex": 5, "endColumnIndex": 6}],
                "booleanRule": {
                    "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "0,0001"}, {"userEnteredValue": "0,2499"}]},
                    "format": {
                        "backgroundColor": {"red": 1.00, "green": 0.90, "blue": 0.82},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 0.60, "green": 0.25, "blue": 0.02}}
                    }
                }
            },
            "index": 3
        }
    })
    # Rule 5: 0% -> Soft Rose/Red
    requests_list.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": tot_row_num - 1, "startColumnIndex": 5, "endColumnIndex": 6}],
                "booleanRule": {
                    "condition": {"type": "NUMBER_EQ", "values": [{"userEnteredValue": "0"}]},
                    "format": {
                        "backgroundColor": {"red": 0.96, "green": 0.88, "blue": 0.88},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 0.55, "green": 0.15, "blue": 0.15}}
                    }
                }
            },
            "index": 4
        }
    })

    # Auto resize columns
    requests_list.append({
        "autoResizeDimensions": {
            "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 7}
        }
    })

    b_res = requests.post(f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate", headers=headers, json={"requests": requests_list})
    print(f"Tab '{TARGET_TAB}' berhasil diperbarui dengan FORMULA LIVE dan Conditional Formatting otomatis.")


def generate_html_dashboard(stats):
    """Hasilkan kode HTML visual modern untuk di-screenshot."""
    rows_tr = ""
    for inst, d in stats["sorted_instansi"][:15]:
        pct = (d["done"] / d["total"] * 100) if d["total"] > 0 else 0
        if pct >= 75:
            badge_cls, bar_color = "badge-emerald", "#10b981"
        elif pct >= 50:
            badge_cls, bar_color = "badge-green", "#10b981"
        elif pct >= 25:
            badge_cls, bar_color = "badge-amber", "#f59e0b"
        elif pct > 0:
            badge_cls, bar_color = "badge-orange", "#ea580c"
        else:
            badge_cls, bar_color = "badge-rose", "#ef4444"

        is_bold = "<strong>" if inst != "(Tanpa Instansi BKSDM)" else "<em>"
        is_bold_end = "</strong>" if inst != "(Tanpa Instansi BKSDM)" else "</em>"

        rows_tr += f"""
          <tr>
            <td>{is_bold}{inst}{is_bold_end}</td>
            <td style="text-align: center;">{d['total']}</td>
            <td style="text-align: center; color: #10b981; font-weight: 700;">{d['done']}</td>
            <td>
              <div class="mini-bar"><div class="mini-fill" style="width: {min(pct, 100):.1f}%; background: {bar_color};"></div></div>
              <span class="badge {badge_cls}">{pct:.2f}%</span>
            </td>
          </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<title>Monitoring Progress Pemadanan Pejabat Mempawah 6104</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
  body {{ background: #0f172a; color: #f8fafc; padding: 32px; display: flex; justify-content: center; }}
  .container {{ width: 1100px; max-width: 100%; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 24px; font-weight: 700; color: #38bdf8; }}
  .header p {{ font-size: 14px; color: #94a3b8; margin-top: 4px; }}
  .badge-tag {{ background: #1e293b; border: 1px solid #475569; color: #38bdf8; padding: 6px 14px; border-radius: 9999px; font-size: 13px; font-weight: 600; }}
  .grid-cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); }}
  .card-title {{ font-size: 13px; color: #94a3b8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }}
  .card-value {{ font-size: 32px; font-weight: 800; margin: 8px 0 4px; }}
  .card-sub {{ font-size: 12px; color: #64748b; }}
  .val-green {{ color: #10b981; }}
  .val-amber {{ color: #f59e0b; }}
  .val-blue {{ color: #38bdf8; }}
  .progress-section {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
  .progress-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
  .progress-title {{ font-size: 16px; font-weight: 700; color: #f1f5f9; }}
  .progress-bar-bg {{ width: 100%; height: 20px; background: #334155; border-radius: 9999px; overflow: hidden; display: flex; }}
  .progress-bar-fill {{ height: 100%; background: linear-gradient(90deg, #10b981, #06b6d4); font-size: 11px; font-weight: 700; color: #fff; display: flex; align-items: center; justify-content: center; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 2fr; gap: 20px; }}
  .status-box {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; }}
  .status-item {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #334155; }}
  .status-item:last-child {{ border-bottom: none; }}
  .status-name {{ font-size: 13px; color: #cbd5e1; }}
  .status-count {{ font-weight: 700; font-size: 14px; }}
  .table-box {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 10px 12px; background: #0f172a; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; border-radius: 4px; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #334155; }}
  tr:last-child td {{ border-bottom: none; }}
  .badge {{ display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }}
  .badge-emerald {{ background: #064e3b; color: #6ee7b7; border: 1px solid #047857; }}
  .badge-green {{ background: #14532d; color: #86efac; border: 1px solid #16a34a; }}
  .badge-amber {{ background: #78350f; color: #fde68a; border: 1px solid #b45309; }}
  .badge-orange {{ background: #7c2d12; color: #fdba74; border: 1px solid #ea580c; }}
  .badge-rose {{ background: #881337; color: #fecdd3; border: 1px solid #e11d48; }}
  .mini-bar {{ width: 80px; height: 8px; background: #334155; border-radius: 9999px; overflow: hidden; display: inline-block; vertical-align: middle; margin-right: 8px; }}
  .mini-fill {{ height: 100%; border-radius: 9999px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>Monitoring Pemadanan Pejabat Mempawah (SE2026)</h1>
      <p>Sumber: Google Sheets 'Data Pejabat Mempawah 6104' &bull; Tab: 'Data OPEN Match'</p>
    </div>
    <div class="badge-tag">Update Live Real-Time</div>
  </div>

  <div class="grid-cards">
    <div class="card">
      <div class="card-title">Total Target</div>
      <div class="card-value val-blue">{stats['total_rows']:,}</div>
      <div class="card-sub">Total baris penugasan</div>
    </div>
    <div class="card">
      <div class="card-title">Sudah Diproses</div>
      <div class="card-value val-green">{stats['total_done']:,}</div>
      <div class="card-sub">Selain status open & draft</div>
    </div>
    <div class="card">
      <div class="card-title">Belum Diproses</div>
      <div class="card-value val-amber">{stats['total_open']:,}</div>
      <div class="card-sub">Status masih open/draft</div>
    </div>
    <div class="card">
      <div class="card-title">Progress Total</div>
      <div class="card-value val-green">{stats['overall_pct']:.2f}%</div>
      <div class="card-sub">{stats['total_done']:,} dari {stats['total_rows']:,} target</div>
    </div>
  </div>

  <div class="progress-section">
    <div class="progress-header">
      <div class="progress-title">Persentase Capaian Keseluruhan</div>
      <div style="font-weight: 800; font-size: 16px; color: #10b981;">{stats['overall_pct']:.2f}% Selesai</div>
    </div>
    <div class="progress-bar-bg">
      <div class="progress-bar-fill" style="width: {stats['overall_pct']:.2f}%;">{stats['overall_pct']:.2f}%</div>
    </div>
  </div>

  <div class="two-col">
    <div class="status-box">
      <h3 style="font-size: 15px; margin-bottom: 16px; color: #f1f5f9;">Rincian Status Assignment (Kolom BD)</h3>
      <div class="status-item">
        <span class="status-name">open</span>
        <span class="status-count" style="color: #f59e0b;">{stats['status_counter']['open']:,} <span style="font-size: 12px; color: #64748b;">({stats['status_counter']['open']/stats['total_rows']*100:.2f}%)</span></span>
      </div>
      <div class="status-item">
        <span class="status-name">submitted respondent</span>
        <span class="status-count" style="color: #10b981;">{stats['status_counter']['submitted respondent']:,} <span style="font-size: 12px; color: #64748b;">({stats['status_counter']['submitted respondent']/stats['total_rows']*100:.2f}%)</span></span>
      </div>
      <div class="status-item">
        <span class="status-name">approved by pengawas</span>
        <span class="status-count" style="color: #06b6d4;">{stats['status_counter']['approved by pengawas']:,} <span style="font-size: 12px; color: #64748b;">({stats['status_counter']['approved by pengawas']/stats['total_rows']*100:.2f}%)</span></span>
      </div>
      <div class="status-item">
        <span class="status-name">edited by admin kabupaten</span>
        <span class="status-count" style="color: #3b82f6;">{stats['status_counter']['edited by admin kabupaten']:,} <span style="font-size: 12px; color: #64748b;">({stats['status_counter']['edited by admin kabupaten']/stats['total_rows']*100:.2f}%)</span></span>
      </div>
      <div class="status-item">
        <span class="status-name">completed by admin kabupaten</span>
        <span class="status-count" style="color: #8b5cf6;">{stats['status_counter']['completed by admin kabupaten']:,} <span style="font-size: 12px; color: #64748b;">({stats['status_counter']['completed by admin kabupaten']/stats['total_rows']*100:.2f}%)</span></span>
      </div>
      <div style="margin-top: 20px; padding: 12px; background: #0f172a; border-radius: 8px; font-size: 12px; color: #94a3b8;">
        &bull; <strong>Formula Live:</strong> Tab Google Sheets <strong>{TARGET_TAB}</strong> menggunakan formula dinamis & conditional formatting.<br>
        &bull; <strong>Auto-Update:</strong> Setiap kali tab <em>Data OPEN Match</em> diupdate tiap 1 jam, tab ini langsung otomatis terupdate secara instan.
      </div>
    </div>

    <div class="table-box">
      <h3 style="font-size: 15px; margin-bottom: 16px; color: #f1f5f9;">Progress Instansi BKSDM Terbesar (Kolom AT)</h3>
      <table>
        <thead>
          <tr>
            <th>Instansi BKSDM</th>
            <th style="text-align: center;">Target</th>
            <th style="text-align: center;">Selesai</th>
            <th>Progress (%)</th>
          </tr>
        </thead>
        <tbody>
          {rows_tr}
        </tbody>
      </table>
    </div>
  </div>
</div>
</body>
</html>"""


async def render_screenshot(html_str, output_path):
    """Render HTML ke gambar PNG menggunakan Patchright Chromium."""
    temp_html = "/tmp/temp_dashboard_pejabat.html"
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_str)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
        )
        page = await browser.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=2)
        await page.goto(f"file://{temp_html}")
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()


def cmd_screenshot(args):
    """Hasilkan gambar screenshot visual dashboard progress."""
    rows = fetch_open_match_data(args.spreadsheet_id)
    stats = compute_statistics(rows)
    html_str = generate_html_dashboard(stats)

    output_path = args.output
    asyncio.run(render_screenshot(html_str, output_path))
    print(f"Screenshot dashboard berhasil disimpan di: {output_path}")

    if args.send_wa:
        from subprocess import run
        caption = f"📊 Monitoring Progress Pemadanan Pejabat Mempawah (Data OPEN Match)\n\n• Progress Total: {stats['overall_pct']:.2f}%\n• Selesai: {stats['total_done']:,} / {stats['total_rows']:,} baris\n• Belum (Open/Draft): {stats['total_open']:,} baris"
        cmd = [
            "python3", "skills/whatsmeow/scripts/wa_tool.py", "send-media",
            "--to", args.send_wa,
            "--file", output_path,
            "--caption", caption
        ]
        run(cmd, check=True)
        print(f"Screenshot berhasil dikirimkan ke WhatsApp {args.send_wa}")


def main():
    parser = argparse.ArgumentParser(description="Monitoring Progress Pemadanan Pejabat Mempawah 6104")
    parser.add_argument("--spreadsheet-id", default=SPREADSHEET_ID, help="Google Spreadsheet ID")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # summary
    p_sum = subparsers.add_parser("summary", help="Tampilkan ringkasan teks angka progress")
    p_sum.add_argument("--json", action="store_true", help="Format JSON")
    p_sum.set_defaults(func=cmd_summary)

    # sync-sheet
    p_sync = subparsers.add_parser("sync-sheet", help="Sinkronkan tab Rekap_Progress_BKSDM di Google Sheets dengan Live Formulas")
    p_sync.set_defaults(func=cmd_sync_sheet)

    # screenshot
    p_sc = subparsers.add_parser("screenshot", help="Generate dashboard screenshot PNG")
    p_sc.add_argument("-o", "--output", default="output/progress_pemadanan_bksdm.png", help="Path berkas output PNG")
    p_sc.add_argument("--send-wa", help="Kirim langsung gambar ke JID WhatsApp target")
    p_sc.set_defaults(func=cmd_screenshot)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
