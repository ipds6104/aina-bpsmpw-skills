#!/usr/bin/env python3
"""
browser_screenshot.py - Utilitas Tangkapan Layar (Screenshot) Browser Headless Serbaguna (Agnostic-Context).
Mendukung pengambilan gambar dari URL web publik, Google Sheets/Docs, dashboard SPA, maupun berkas HTML lokal
menggunakan Patchright stealth Chromium headless browser. Mendukung opsi HiDPI/Retina, delay render, selector element,
serta pengiriman otomatis via WhatsApp Gateway Whatsmeow.
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from patchright.async_api import async_playwright

def resolve_target_url(target: str) -> str:
    """Mengonversi path lokal menjadi URL file:// jika bukan skema HTTP/HTTPS."""
    if target.startswith("http://") or target.startswith("https://") or target.startswith("file://"):
        return target
    p = Path(target).resolve()
    if p.exists():
        return f"file://{p}"
    return target

async def capture_screenshot(
    url: str,
    output_path: str,
    width: int = 1360,
    height: int = 900,
    scale: int = 2,
    full_page: bool = False,
    selector: str = None,
    wait_selector: str = None,
    delay: float = 2.0,
    timeout_sec: int = 30,
    dark_mode: bool = False
):
    """Mengambil tangkapan layar menggunakan Chromium headless Patchright."""
    target_url = resolve_target_url(url)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    is_google_docs = "docs.google.com" in target_url

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage"
            ]
        )

        color_scheme = "dark" if dark_mode else "light"
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
            color_scheme=color_scheme
        )
        page = await context.new_page()

        print(f"[browser-screenshot] Membuka URL: {target_url}...")
        nav_wait = "domcontentloaded" if is_google_docs else "networkidle"

        try:
            await page.goto(target_url, wait_until=nav_wait, timeout=timeout_sec * 1000)
        except Exception as e:
            # Fallback jika networkidle timeout pada SPA ber-polling
            if nav_wait == "networkidle":
                print(f"[browser-screenshot] Navigasi networkidle timeout, melanjutkan dengan status DOM saat ini: {e}")
            else:
                raise

        # Otomatis deteksi Google Sheets jika wait_selector tidak diisi
        if is_google_docs and not wait_selector:
            wait_selector = "canvas"

        if wait_selector:
            print(f"[browser-screenshot] Menunggu selector: {wait_selector}...")
            try:
                await page.wait_for_selector(wait_selector, timeout=15000)
            except Exception as e:
                print(f"[browser-screenshot] Selector '{wait_selector}' tidak muncul dalam 15s: {e}")

        if delay > 0:
            print(f"[browser-screenshot] Jeda render: {delay} detik...")
            await page.wait_for_timeout(int(delay * 1000))

        # Pengambilan screenshot
        if selector:
            print(f"[browser-screenshot] Mengambil tangkapan layar elemen: {selector}...")
            element = await page.query_selector(selector)
            if element:
                await element.screenshot(path=output_path)
            else:
                print(f"[browser-screenshot] Elemen '{selector}' tidak ditemukan, mengambil full viewport...")
                await page.screenshot(path=output_path, full_page=full_page)
        else:
            print(f"[browser-screenshot] Mengambil tangkapan layar (full_page={full_page})...")
            await page.screenshot(path=output_path, full_page=full_page)

        await browser.close()
        print(f"[browser-screenshot] Berhasil disimpan di: {output_path}")

def send_whatsapp_media(file_path: str, recipient: str, caption: str = ""):
    """Mengirim file hasil screenshot ke WhatsApp via helper Whatsmeow."""
    wa_tool_candidates = [
        Path("/app/workspaces/default/skills/whatsmeow/scripts/wa_tool.py"),
        Path("/app/skills/whatsmeow/scripts/wa_tool.py"),
        Path("/root/projects/aina/skills/whatsmeow/scripts/wa_tool.py")
    ]
    wa_tool = None
    for c in wa_tool_candidates:
        if c.exists():
            wa_tool = c
            break

    if not wa_tool:
        raise FileNotFoundError("Helper script wa_tool.py tidak ditemukan.")

    cmd = [
        sys.executable, str(wa_tool), "send-media",
        "--to", recipient,
        "--file", file_path
    ]
    if caption:
        cmd.extend(["--caption", caption])

    print(f"[browser-screenshot] Mengirim gambar ke WhatsApp: {recipient}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"[browser-screenshot] Pengiriman WhatsApp berhasil!")
    else:
        print(f"[browser-screenshot] Gagal mengirim WhatsApp: {res.stderr}")

def main():
    parser = argparse.ArgumentParser(
        description="Browser Headless Screenshot Tool (Context-Agnostic) berbasis Patchright Chromium."
    )
    parser.add_argument("url", help="URL web, tautan Google Sheet/Doc, atau berkas HTML lokal")
    parser.add_argument("-o", "--output", default="output/screenshot.png", help="Path berkas output (default: output/screenshot.png)")
    parser.add_argument("--width", type=int, default=1360, help="Lebar viewport dalam pixel (default: 1360)")
    parser.add_argument("--height", type=int, default=900, help="Tinggi viewport dalam pixel (default: 900)")
    parser.add_argument("--scale", type=int, default=2, help="Device Scale Factor untuk HiDPI/Retina (default: 2)")
    parser.add_argument("--full-page", action="store_true", help="Ambil tangkapan layar penuh (scroll full page)")
    parser.add_argument("--selector", help="CSS selector elemen spesifik yang ingin di-screenshot")
    parser.add_argument("--wait-selector", help="CSS selector yang ditunggu sebelum screenshot (misal: canvas)")
    parser.add_argument("--delay", type=float, default=2.0, help="Jeda rendering dalam detik setelah navigasi (default: 2.0)")
    parser.add_argument("--timeout", type=int, default=30, help="Batas waktu navigasi dalam detik (default: 30)")
    parser.add_argument("--dark-mode", action="store_true", help="Aktifkan prefers-color-scheme dark")
    parser.add_argument("--send-wa", help="JID WhatsApp tujuan pengiriman (misal: 62896xxx@s.whatsapp.net atau xxx@g.us)")
    parser.add_argument("--caption", default="", help="Keterangan teks untuk pengiriman WhatsApp")

    args = parser.parse_args()

    asyncio.run(capture_screenshot(
        url=args.url,
        output_path=args.output,
        width=args.width,
        height=args.height,
        scale=args.scale,
        full_page=args.full_page,
        selector=args.selector,
        wait_selector=args.wait_selector,
        delay=args.delay,
        timeout_sec=args.timeout,
        dark_mode=args.dark_mode
    ))

    if args.send_wa:
        send_whatsapp_media(args.output, args.send_wa, args.caption)

if __name__ == "__main__":
    main()
