#!/usr/bin/env python3
"""
Patchright Web-to-PDF Utility Tool
Mengonversi halaman web atau file HTML menjadi PDF (setara Ctrl+P / Save as PDF)
menggunakan Patchright stealth Chromium headless browser.
"""

import argparse
import asyncio
import os
import shutil
import sys
import time
from pathlib import Path


def find_chromium_executable():
    """Mencari binary Chromium yang tersedia di sistem atau cache."""
    # 1. Cek cache playwright / patchright
    cache_base = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", Path.home() / ".cache/ms-playwright"))
    if cache_base.exists():
        for candidate in cache_base.glob("**/chrome-linux64/chrome"):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        for candidate in cache_base.glob("**/chrome-headless-shell-linux64/chrome-headless-shell"):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)

    # 2. Cek binary sistem di PATH
    for cmd in ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"]:
        found = shutil.which(cmd)
        if found:
            return found

    return None


async def render_pdf(
    url: str,
    output_path: str,
    format_size: str = "A4",
    landscape: bool = False,
    emulate_print: bool = True,
    print_background: bool = True,
    margin_top: str = "1cm",
    margin_bottom: str = "1cm",
    margin_left: str = "1cm",
    margin_right: str = "1cm",
    wait_until: str = "networkidle",
    wait_delay: float = 0.0,
    wait_selector: str = None,
    scale: float = 1.0,
    header_template: str = None,
    footer_template: str = None,
    executable_path: str = None,
    user_agent: str = None,
    proxy: str = None,
    timeout_sec: int = 60,
):
    try:
        from patchright.async_api import async_playwright
    except ImportError:
        print("[ERROR] Pustaka 'patchright' belum terpasang. Jalankan: pip install --user patchright", file=sys.stderr)
        sys.exit(1)

    exec_path = executable_path or find_chromium_executable()
    if not exec_path:
        print("[ERROR] Tidak dapat menemukan binary Chromium. Pastikan chromium terpasang di sistem.", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Membuka Chromium via: {exec_path}")
    print(f"[INFO] Memuat URL: {url}")

    launch_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-setuid-sandbox",
        "--no-zygote",
    ]

    launch_kwargs = {
        "headless": True,
        "executable_path": exec_path,
        "args": launch_args,
    }

    if proxy:
        launch_kwargs["proxy"] = {"server": proxy}

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)

        context_kwargs = {
            "viewport": {"width": 1280, "height": 800},
            "device_scale_factor": 1,
        }
        if user_agent:
            context_kwargs["user_agent"] = user_agent

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        # Set default timeout
        page.set_default_navigation_timeout(timeout_sec * 1000)
        page.set_default_timeout(timeout_sec * 1000)

        # Navigasi ke URL
        if url.startswith("http://") or url.startswith("https://") or url.startswith("file://"):
            await page.goto(url, wait_until=wait_until)
        else:
            # Menganggap sebagai file lokal
            abs_local = Path(url).resolve()
            if abs_local.exists():
                await page.goto(f"file://{abs_local}", wait_until=wait_until)
            else:
                await page.goto(f"https://{url}", wait_until=wait_until)

        # Tunggu selector tertentu jika diminta
        if wait_selector:
            print(f"[INFO] Menunggu selector: {wait_selector}...")
            await page.wait_for_selector(wait_selector, timeout=timeout_sec * 1000)

        # Tunggu jeda waktu tambahan jika ditentukan (misal grafik/animasi JS selesai)
        if wait_delay > 0:
            print(f"[INFO] Menunggu jeda tambahan {wait_delay} detik...")
            await asyncio.sleep(wait_delay)

        # Emulasi media print jika aktif
        if emulate_print:
            await page.emulate_media(media="print")

        # Parameter PDF
        pdf_options = {
            "path": output_path,
            "format": format_size,
            "landscape": landscape,
            "print_background": print_background,
            "scale": scale,
            "margin": {
                "top": margin_top,
                "bottom": margin_bottom,
                "left": margin_left,
                "right": margin_right,
            },
        }

        if header_template or footer_template:
            pdf_options["display_header_footer"] = True
            if header_template:
                pdf_options["header_template"] = header_template
            if footer_template:
                pdf_options["footer_template"] = footer_template

        # Pastikan folder target ada
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"[INFO] Mengonversi ke PDF: {out_file} (Format: {format_size}, Print CSS: {emulate_print})...")
        await page.pdf(**pdf_options)

        await context.close()
        await browser.close()

        if out_file.exists():
            size_kb = out_file.stat().st_size / 1024
            print(f"[SUCCESS] Berhasil disimpan! File: {out_file} ({size_kb:.1f} KB)")
            return str(out_file)
        else:
            print("[ERROR] Berkas PDF gagal dibuat.", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Patchright Web-to-PDF: Konversi halaman web/HTML ke PDF via Patchright stealth Chromium."
    )
    parser.add_argument("url", help="URL target (misal: https://example.com) atau path file HTML lokal")
    parser.add_argument(
        "-o", "--output", default="output.pdf", help="Path file output PDF (default: output.pdf)"
    )
    parser.add_argument(
        "--format", default="A4", choices=["A4", "Letter", "Legal", "A3", "A5", "Tabloid"], help="Ukuran kertas (default: A4)"
    )
    parser.add_argument("--landscape", action="store_true", help="Cetak dalam orientasi landscape (horizontal)")
    parser.add_argument(
        "--no-print-css", action="store_true", help="Jangan emulasi CSS print (gunakan styling layar biasa)"
    )
    parser.add_argument(
        "--no-background", action="store_true", help="Jangan cetak gambar/warna latar belakang (background)"
    )
    parser.add_argument(
        "--margin", default="1cm", help="Margin semua sisi (default: 1cm, misal: '0.5cm' atau '10px')"
    )
    parser.add_argument("--margin-top", default=None, help="Margin atas khusus")
    parser.add_argument("--margin-bottom", default=None, help="Margin bawah khusus")
    parser.add_argument("--margin-left", default=None, help="Margin kiri khusus")
    parser.add_argument("--margin-right", default=None, help="Margin kanan khusus")
    parser.add_argument(
        "--wait-until",
        default="networkidle",
        choices=["networkidle", "load", "domcontentloaded", "commit"],
        help="Event selesai muat halaman (default: networkidle)",
    )
    parser.add_argument("--delay", type=float, default=0.0, help="Jeda waktu tambahan dalam detik sebelum cetak")
    parser.add_argument("--wait-selector", default=None, help="Tunggu elemen CSS tertentu sebelum cetak")
    parser.add_argument("--scale", type=float, default=1.0, help="Skala render halaman (0.1 - 2.0, default: 1.0)")
    parser.add_argument("--browser-path", default=None, help="Path khusus binary Chromium")
    parser.add_argument("--timeout", type=int, default=60, help="Batas waktu navigasi dalam detik (default: 60)")
    parser.add_argument(
        "--send-wa",
        metavar="JID",
        default=None,
        help="Kirim berkas PDF langsung ke WhatsApp JID pemohon setelah selesai via wa_tool",
    )
    parser.add_argument("--caption", default="", help="Keterangan/caption jika dikirim ke WhatsApp")

    args = parser.parse_args()

    m_top = args.margin_top or args.margin
    m_bottom = args.margin_bottom or args.margin
    m_left = args.margin_left or args.margin
    m_right = args.margin_right or args.margin

    out_pdf = asyncio.run(
        render_pdf(
            url=args.url,
            output_path=args.output,
            format_size=args.format,
            landscape=args.landscape,
            emulate_print=not args.no_print_css,
            print_background=not args.no_background,
            margin_top=m_top,
            margin_bottom=m_bottom,
            margin_left=m_left,
            margin_right=m_right,
            wait_until=args.wait_until,
            wait_delay=args.delay,
            wait_selector=args.wait_selector,
            scale=args.scale,
            executable_path=args.browser_path,
            timeout_sec=args.timeout,
        )
    )

    if args.send_wa and out_pdf:
        print(f"[INFO] Mengirim hasil PDF ke WhatsApp: {args.send_wa}...")
        wa_tool = Path("/app/skills/whatsmeow/scripts/wa_tool.py")
        if wa_tool.exists():
            caption = args.caption or f"Dokumen PDF hasil cetak dari {args.url}"
            cmd = f'python3 "{wa_tool}" send-media --to "{args.send_wa}" --file "{out_pdf}" --caption "{caption}"'
            os.system(cmd)
        else:
            print("[WARN] wa_tool.py tidak ditemukan, gagal mengirim ke WhatsApp.", file=sys.stderr)


if __name__ == "__main__":
    main()
