#!/usr/bin/env python3
"""
sbr_monitor_tool.py - CLI Tool untuk Monitoring & Visual Dashboard Matching SBR SE2026 BPS Kabupaten Mempawah (6104).
Membaca data live dari Google Spreadsheet 'Lembar Kerja Matching SBR SE2026' dan
mengambil tangkapan layar (screenshot) langsung dari Google Sheet via Patchright Chromium browser headless.
"""

import argparse
import asyncio
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
import requests

# Add gdrive path
GDRIVE_TOOL_PATH = Path("/app/skills/gdrive/scripts")
if str(GDRIVE_TOOL_PATH) not in sys.path:
    sys.path.insert(0, str(GDRIVE_TOOL_PATH))

try:
    from gdrive_tool import get_valid_access_token
except ImportError:
    fallback_gdrive = Path(__file__).resolve().parent.parent.parent.parent / "skills" / "gdrive" / "scripts"
    sys.path.insert(0, str(fallback_gdrive))
    from gdrive_tool import get_valid_access_token

from patchright.async_api import async_playwright

SPREADSHEET_ID = os.getenv("SBR_SPREADSHEET_ID", "1tgXYr4dagc4LlDffJXNu7Q389uGh_HDBQWrMleTv2FA")
MONITOR_TAB = "Rekap Monitoring"
SHEET_GID = os.getenv("SBR_SHEET_GID", "393620021")

def fetch_rekap_data(spreadsheet_id=SPREADSHEET_ID):
    """Ambil ringkasan data monitoring dari tab 'Rekap Monitoring'."""
    try:
        token = get_valid_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'{MONITOR_TAB}'!A1:G42?valueRenderOption=FORMATTED_VALUE"
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get("values", [])
    except Exception as e:
        print(f"Warning saat fetch_rekap_data: {e}")
    return []

async def capture_sheet_screenshot(spreadsheet_id, gid, output_path):
    """Membuka Google Sheet langsung di headless Chromium dan mengambil tangkapan layar antarmuka asli."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={gid}"

    async with async_playwright() as p:
        launch_kwargs = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--headless=new"]
        }
        if not (p.chromium.executable_path and Path(p.chromium.executable_path).exists()):
            if Path("/usr/bin/chromium").exists():
                launch_kwargs["executable_path"] = "/usr/bin/chromium"

        browser = await p.chromium.launch(**launch_kwargs)
        page = await browser.new_page(viewport={"width": 1360, "height": 1200}, device_scale_factor=2)
        await page.goto(url, wait_until="domcontentloaded")
        try:
            await page.wait_for_selector("canvas", timeout=15000)
        except Exception:
            pass
        # Tunggu rendering sel/formula stabil
        await page.wait_for_timeout(5000)
        await page.screenshot(path=output_path)
        await browser.close()

def cmd_summary(args):
    """Cetak ringkasan teks singkat ke terminal."""
    rows = fetch_rekap_data(args.spreadsheet_id)
    total_row = rows[11] if len(rows) > 11 else []
    total_pct = total_row[6] if len(total_row) > 6 else "0%"
    total_done = total_row[4] if len(total_row) > 4 else "0"
    total_target = total_row[3] if len(total_row) > 3 else "1226"

    print("=== RINGKASAN PROGRESS MATCHING PRELIST SBR SE2026 ===")
    print(f"• Total Target  : {total_target} kasus")
    print(f"• Selesai       : {total_done} kasus ({total_pct})")
    print(f"• Sisa          : {total_row[5] if len(total_row) > 5 else '-'} kasus")

def cmd_screenshot(args):
    """Generate tangkapan layar langsung dari Google Sheets dan optionally kirim via WhatsApp."""
    print("1. Mengambil data ringkasan live dari Google Sheets...")
    rows = fetch_rekap_data(args.spreadsheet_id)
    total_row = rows[11] if len(rows) > 11 else []
    total_pct = total_row[6] if len(total_row) > 6 else "0%"
    total_done = total_row[4] if len(total_row) > 4 else "0"
    total_target = total_row[3] if len(total_row) > 3 else "1226"

    print(f"2. Membuka Google Sheet & mengambil screenshot ke {args.output} via Chromium...")
    asyncio.run(capture_sheet_screenshot(args.spreadsheet_id, args.gid, args.output))
    print("   Screenshot Google Sheet berhasil dibuat!")

    if args.send_wa:
        print(f"3. Mengirimkan screenshot ke WhatsApp {args.send_wa}...")
        caption = (
            f"*UPDATE MONITORING MATCHING SBR SE2026*\n"
            f"📅 Tanggal: {datetime.datetime.now().strftime('%d %B %Y')}\n\n"
            f"• *Progress Total*: {total_pct}\n"
            f"• *Selesai*: {total_done} dari {total_target} kasus\n\n"
            f"🔗 Spreadsheet Live:\nhttps://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/edit#gid={args.gid}"
        )
        cmd = [
            "python3", "skills/whatsmeow/scripts/wa_tool.py", "send-media",
            "--to", args.send_wa,
            "--file", args.output,
            "--caption", caption
        ]
        subprocess.run(cmd, check=True)
        print("   Terkirim sukses!")

def cmd_format_target(args):
    """Menerapkan conditional formatting otomatis untuk menandai sel progress sampai nama petugas yang belum capai target harian."""
    print("Menerapkan Conditional Formatting pada Tab 'Rekap Monitoring'...")
    token = get_valid_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    spreadsheet_id = args.spreadsheet_id

    # Ambil list conditional format yang ada
    res = requests.get(f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?fields=sheets(properties,conditionalFormats)", headers=headers)
    rekap_sheet_id = int(args.gid)
    rules_count = 0
    for s in res.json().get("sheets", []):
        if s["properties"]["sheetId"] == rekap_sheet_id:
            rules_count = len(s.get("conditionalFormats", []))

    delete_reqs = [{"deleteConditionalFormatRule": {"sheetId": rekap_sheet_id, "index": 0}} for _ in range(rules_count)]

    # Rule untuk Organik (B18:G24) dan Magang (B29:G40)
    add_reqs = [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {
                            "sheetId": rekap_sheet_id,
                            "startRowIndex": 17,
                            "endRowIndex": 24,
                            "startColumnIndex": 1,
                            "endColumnIndex": 8
                        }
                    ],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [
                                {
                                    "userEnteredValue": "=AND($D18 > 0; $G18 < MIN(1; (TODAY() - DATE(2026; 11; 10)) / (DATE(2026; 11; 20) - DATE(2026; 11; 10))))"
                                }
                            ]
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.98,
                                "green": 0.86,
                                "blue": 0.85
                            }
                        }
                    }
                },
                "index": 0
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {
                            "sheetId": rekap_sheet_id,
                            "startRowIndex": 28,
                            "endRowIndex": 40,
                            "startColumnIndex": 1,
                            "endColumnIndex": 8
                        }
                    ],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [
                                {
                                    "userEnteredValue": "=AND($D29 > 0; $G29 < MIN(1; (TODAY() - DATE(2026; 11; 10)) / (DATE(2026; 11; 20) - DATE(2026; 11; 10))))"
                                }
                            ]
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.98,
                                "green": 0.86,
                                "blue": 0.85
                            }
                        }
                    }
                },
                "index": 1
            }
        }
    ]

    body = {"requests": delete_reqs + add_reqs}
    resp = requests.post(f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate", headers=headers, json=body)
    if resp.status_code == 200:
        print("Conditional formatting berhasil diterapkan!")
    else:
        print(f"Gagal menerapkan conditional formatting: {resp.text}")

def main():
    parser = argparse.ArgumentParser(description="Tool Monitoring Matching SBR SE2026 Mempawah")
    parser.add_argument("--spreadsheet-id", default=SPREADSHEET_ID, help="Spreadsheet ID")
    parser.add_argument("--gid", default=SHEET_GID, help="Sheet Tab GID")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # summary
    p_sum = subparsers.add_parser("summary", help="Cetak ringkasan teks")
    p_sum.set_defaults(func=cmd_summary)

    # screenshot
    p_sc = subparsers.add_parser("screenshot", help="Generate tangkapan layar langsung dari Google Sheet")
    p_sc.add_argument("-o", "--output", default="output/rekap_monitoring_sbr.png", help="Path output PNG")
    p_sc.add_argument("--send-wa", help="JID WhatsApp target pengiriman")
    p_sc.set_defaults(func=cmd_screenshot)

    # format-target
    p_fmt = subparsers.add_parser("format-target", help="Terapkan conditional formatting batas target harian s.d. 20 Nov")
    p_fmt.set_defaults(func=cmd_format_target)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
