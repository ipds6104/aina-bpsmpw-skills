#!/usr/bin/env python3
"""
sbr_monitor_tool.py - CLI Tool untuk Monitoring & Visual Dashboard Matching SBR SE2026 BPS Kabupaten Mempawah (6104).
Membaca data live dari Google Spreadsheet 'Lembar Kerja Matching SBR SE2026',
mengenerate tangkapan layar dashboard visual via Patchright Chromium,
serta menyediakan utilitas sinkronisasi data NIK & Pemilik Usaha dari Parquet SE2026.
"""

import argparse
import asyncio
import datetime
import json
import os
import subprocess
import sys
from collections import defaultdict
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

def fetch_rekap_data(spreadsheet_id=SPREADSHEET_ID):
    """Ambil seluruh data monitoring dari tab 'Rekap Monitoring'."""
    token = get_valid_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'{MONITOR_TAB}'!A1:G42?valueRenderOption=FORMATTED_VALUE"
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise RuntimeError(f"Gagal mengambil data dari Google Sheets: {res.text}")
    return res.json().get("values", [])

def generate_html_dashboard(rows):
    """Generate visual dashboard HTML yang modern, responsif, dan elegan."""
    now_str = datetime.datetime.now().strftime("%d %B %Y %H:%M WIB")

    total_row = rows[11] if len(rows) > 11 else []
    total_target = total_row[3] if len(total_row) > 3 else "0"
    total_done = total_row[4] if len(total_row) > 4 else "0"
    total_remain = total_row[5] if len(total_row) > 5 else "0"
    total_pct = total_row[6] if len(total_row) > 6 else "0,0%"

    kategori_rows = []
    for r in rows[4:10]:
        if len(r) >= 7:
            kategori_rows.append({
                "no": r[0],
                "name": r[1],
                "desc": r[2],
                "target": r[3],
                "done": r[4],
                "remain": r[5],
                "pct": r[6]
            })

    organik_rows = []
    for r in rows[17:24]:
        if len(r) >= 7:
            organik_rows.append({
                "no": r[0],
                "name": r[1],
                "unit": r[2],
                "target": r[3],
                "done": r[4],
                "remain": r[5],
                "pct": r[6]
            })
    tot_org = rows[24] if len(rows) > 24 else []
    tot_org_target = tot_org[3] if len(tot_org) > 3 else "-"
    tot_org_done = tot_org[4] if len(tot_org) > 4 else "-"
    tot_org_remain = tot_org[5] if len(tot_org) > 5 else "-"
    tot_org_pct = tot_org[6] if len(tot_org) > 6 else "-"

    magang_rows = []
    for r in rows[28:40]:
        if len(r) >= 7:
            magang_rows.append({
                "no": r[0],
                "name": r[1],
                "unit": r[2],
                "target": r[3],
                "done": r[4],
                "remain": r[5],
                "pct": r[6]
            })
    tot_mag = rows[40] if len(rows) > 40 else []
    tot_mag_target = tot_mag[3] if len(tot_mag) > 3 else "-"
    tot_mag_done = tot_mag[4] if len(tot_mag) > 4 else "-"
    tot_mag_remain = tot_mag[5] if len(tot_mag) > 5 else "-"
    tot_mag_pct = tot_mag[6] if len(tot_mag) > 6 else "-"

    def make_progress_bar(pct_str):
        try:
            val = float(pct_str.replace('%', '').replace(',', '.').strip())
        except Exception:
            val = 0.0
        clamped = min(max(val, 0), 100)
        color = "#10b981" if clamped >= 75 else "#3b82f6" if clamped >= 40 else "#f59e0b" if clamped >= 10 else "#6366f1"
        return f"""
        <div style="display: flex; align-items: center; gap: 8px;">
            <div style="flex: 1; background: #334155; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="width: {clamped}%; background: {color}; height: 100%; border-radius: 4px;"></div>
            </div>
            <span style="font-weight: 700; font-size: 13px; color: {color}; min-width: 48px; text-align: right;">{pct_str}</span>
        </div>
        """

    kategori_tr = "".join([f"""
        <tr>
            <td style="text-align: center; color: #94a3b8;">{k['no']}</td>
            <td><strong>{k['name']}</strong><br><small style="color: #64748b;">{k['desc']}</small></td>
            <td style="text-align: center; font-weight: 600;">{k['target']}</td>
            <td style="text-align: center; font-weight: 600; color: #10b981;">{k['done']}</td>
            <td style="text-align: center; color: #94a3b8;">{k['remain']}</td>
            <td>{make_progress_bar(k['pct'])}</td>
        </tr>
    """ for k in kategori_rows])

    organik_tr = "".join([f"""
        <tr>
            <td style="text-align: center; color: #94a3b8;">{o['no']}</td>
            <td><strong>{o['name']}</strong></td>
            <td style="text-align: center; color: #38bdf8;">{o['unit']}</td>
            <td style="text-align: center; font-weight: 600;">{o['target']}</td>
            <td style="text-align: center; font-weight: 600; color: #10b981;">{o['done']}</td>
            <td style="text-align: center; color: #94a3b8;">{o['remain']}</td>
            <td>{make_progress_bar(o['pct'])}</td>
        </tr>
    """ for o in organik_rows])

    magang_tr = "".join([f"""
        <tr>
            <td style="text-align: center; color: #94a3b8;">{m['no']}</td>
            <td><strong>{m['name']}</strong></td>
            <td style="text-align: center; color: #a78bfa;">{m['unit']}</td>
            <td style="text-align: center; font-weight: 600;">{m['target']}</td>
            <td style="text-align: center; font-weight: 600; color: #10b981;">{m['done']}</td>
            <td style="text-align: center; color: #94a3b8;">{m['remain']}</td>
            <td>{make_progress_bar(m['pct'])}</td>
        </tr>
    """ for m in magang_rows])

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0b0f19;
    color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    padding: 32px;
  }}
  .container {{
    max-width: 1180px;
    margin: 0 auto;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #1e293b;
    padding-bottom: 20px;
    margin-bottom: 24px;
  }}
  .title-group h1 {{
    font-size: 22px;
    font-weight: 800;
    color: #38bdf8;
    letter-spacing: -0.5px;
    margin-bottom: 6px;
  }}
  .title-group p {{
    font-size: 13px;
    color: #94a3b8;
  }}
  .badge {{
    background: #0284c7;
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    padding: 6px 14px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .cards-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 28px;
  }}
  .card {{
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
  }}
  .card-label {{
    font-size: 12px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    margin-bottom: 8px;
  }}
  .card-val {{
    font-size: 26px;
    font-weight: 800;
    color: #f8fafc;
  }}
  .card.highlight {{
    background: linear-gradient(135deg, #0369a1 0%, #0284c7 100%);
    border: none;
  }}
  .card.highlight .card-label {{
    color: #e0f2fe;
  }}
  .card.highlight .card-val {{
    color: #ffffff;
  }}
  .section {{
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 28px;
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
  }}
  .section-title {{
    font-size: 16px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  th {{
    background: #1f2937;
    color: #cbd5e1;
    text-align: left;
    padding: 12px 14px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid #374151;
  }}
  td {{
    padding: 12px 14px;
    border-bottom: 1px solid #1f2937;
    color: #e2e8f0;
  }}
  tr:last-child td {{
    border-bottom: none;
  }}
  tr.total-row td {{
    background: #1e293b;
    font-weight: 700;
    color: #38bdf8;
    border-top: 2px solid #38bdf8;
  }}
  .two-cols {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }}
  .footer {{
    text-align: center;
    color: #64748b;
    font-size: 12px;
    margin-top: 16px;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="title-group">
      <h1>📊 MONITORING LIVE MATCHING PRELIST SBR SE2026</h1>
      <p>BPS Kabupaten Mempawah (6104) &bull; Terakhir Diperbarui: {now_str}</p>
    </div>
    <div class="badge">Realtime Tracker</div>
  </div>

  <div class="cards-grid">
    <div class="card">
      <div class="card-label">Total Beban Kasus</div>
      <div class="card-val">{total_target}</div>
    </div>
    <div class="card">
      <div class="card-label">Sudah Diverifikasi</div>
      <div class="card-val" style="color: #10b981;">{total_done}</div>
    </div>
    <div class="card">
      <div class="card-label">Sisa Belum Selesai</div>
      <div class="card-val" style="color: #f59e0b;">{total_remain}</div>
    </div>
    <div class="card highlight">
      <div class="card-label">Progress Keseluruhan</div>
      <div class="card-val">{total_pct}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📁 Progres Berdasarkan Kategori Temuan Prelist SBR</div>
    <table>
      <thead>
        <tr>
          <th style="width: 40px; text-align: center;">No</th>
          <th>Kategori Temuan</th>
          <th style="width: 100px; text-align: center;">Target</th>
          <th style="width: 110px; text-align: center;">Selesai</th>
          <th style="width: 100px; text-align: center;">Sisa</th>
          <th style="width: 200px;">Progress</th>
        </tr>
      </thead>
      <tbody>
        {kategori_tr}
        <tr class="total-row">
          <td colspan="2" style="text-align: center;">TOTAL SELURUH KATEGORI</td>
          <td style="text-align: center;">{total_target}</td>
          <td style="text-align: center;">{total_done}</td>
          <td style="text-align: center;">{total_remain}</td>
          <td>{make_progress_bar(total_pct)}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="two-cols">
    <div class="section">
      <div class="section-title">🏛️ Petugas Organik BPS (7 Orang)</div>
      <table>
        <thead>
          <tr>
            <th style="width: 32px; text-align: center;">No</th>
            <th>Nama Petugas</th>
            <th style="text-align: center;">Fungsi</th>
            <th style="text-align: center;">Target</th>
            <th style="text-align: center;">Selesai</th>
            <th style="text-align: center;">Sisa</th>
            <th style="width: 140px;">Progress</th>
          </tr>
        </thead>
        <tbody>
          {organik_tr}
          <tr class="total-row">
            <td colspan="3" style="text-align: center;">TOTAL ORGANIK BPS</td>
            <td style="text-align: center;">{tot_org_target}</td>
            <td style="text-align: center;">{tot_org_done}</td>
            <td style="text-align: center;">{tot_org_remain}</td>
            <td>{make_progress_bar(tot_org_pct)}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="section">
      <div class="section-title">🎓 Adik-Adik Magang Kemnaker (12 Orang)</div>
      <table>
        <thead>
          <tr>
            <th style="width: 32px; text-align: center;">No</th>
            <th>Nama Petugas</th>
            <th style="text-align: center;">Batch</th>
            <th style="text-align: center;">Target</th>
            <th style="text-align: center;">Selesai</th>
            <th style="text-align: center;">Sisa</th>
            <th style="width: 140px;">Progress</th>
          </tr>
        </thead>
        <tbody>
          {magang_tr}
          <tr class="total-row">
            <td colspan="3" style="text-align: center;">TOTAL MAGANG KEMNAKER</td>
            <td style="text-align: center;">{tot_mag_target}</td>
            <td style="text-align: center;">{tot_mag_done}</td>
            <td style="text-align: center;">{tot_mag_remain}</td>
            <td>{make_progress_bar(tot_mag_pct)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="footer">
    Sistem Otomasi Monitoring SBR SE2026 &bull; BPS Kabupaten Mempawah
  </div>
</div>
</body>
</html>"""
    return html

async def render_image(html_str, output_path):
    temp_html = "/tmp/temp_dashboard_rekap_sbr.html"
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_str)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 1100}, device_scale_factor=2)
        await page.goto(f"file://{temp_html}")
        await page.screenshot(path=output_path, full_page=True)
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
    """Generate screenshot dashboard dan optionally kirim via WhatsApp."""
    print("1. Mengambil data live dari Google Sheets...")
    rows = fetch_rekap_data(args.spreadsheet_id)
    total_row = rows[11] if len(rows) > 11 else []
    total_pct = total_row[6] if len(total_row) > 6 else "0%"
    total_done = total_row[4] if len(total_row) > 4 else "0"
    total_target = total_row[3] if len(total_row) > 3 else "1226"

    print("2. Menyusun template HTML visual dashboard...")
    html_str = generate_html_dashboard(rows)

    print(f"3. Merender screenshot ke {args.output} via Chromium...")
    asyncio.run(render_image(html_str, args.output))
    print("   Screenshot berhasil dibuat!")

    if args.send_wa:
        print(f"4. Mengirimkan screenshot ke WhatsApp {args.send_wa}...")
        caption = (
            f"*UPDATE MONITORING MATCHING SBR SE2026*\n"
            f"📅 Tanggal: {datetime.datetime.now().strftime('%d %B %Y')}\n\n"
            f"• *Progress Total*: {total_pct}\n"
            f"• *Selesai*: {total_done} dari {total_target} kasus\n\n"
            f"🔗 Spreadsheet Live:\nhttps://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/edit?usp=sharing"
        )
        cmd = [
            "python3", "skills/whatsmeow/scripts/wa_tool.py", "send-media",
            "--to", args.send_wa,
            "--file", args.output,
            "--caption", caption
        ]
        subprocess.run(cmd, check=True)
        print("   Terkirim sukses!")

def main():
    parser = argparse.ArgumentParser(description="Tool Monitoring Matching SBR SE2026 Mempawah")
    parser.add_argument("--spreadsheet-id", default=SPREADSHEET_ID, help="Spreadsheet ID")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # summary
    p_sum = subparsers.add_parser("summary", help="Cetak ringkasan teks")
    p_sum.set_defaults(func=cmd_summary)

    # screenshot
    p_sc = subparsers.add_parser("screenshot", help="Generate tangkapan layar dashboard visual")
    p_sc.add_argument("-o", "--output", default="output/rekap_monitoring_sbr.png", help="Path output PNG")
    p_sc.add_argument("--send-wa", help="JID WhatsApp target pengiriman")
    p_sc.set_defaults(func=cmd_screenshot)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
