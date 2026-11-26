#!/usr/bin/env python3
"""
browser_screenshot.py - Utilitas Tangkapan Layar (Screenshot) Browser Headless Serbaguna (Agnostic-Context).
Mendukung pengambilan gambar dari URL web publik, Google Sheets/Docs, dashboard SPA, maupun berkas HTML lokal
menggunakan Patchright stealth Chromium headless browser.

Diperkaya dengan arsitektur dan teknik stealth dari whaleyxbt/patchright-enhanced:
1. Persistent Context (launch_persistent_context) dengan direktori profil terisolasi untuk mengelabui deteksi incognito WAF.
2. Zero-Spoofing Protocol: Menggunakan header dan User-Agent native Patchright (mencegah fingerprint mismatch JA3/TLS).
3. Traffic & Ad Blocker: Opsi pemblokiran media berat dan domain iklan/pelacak untuk efisiensi bandwidth & loading kilat.
4. Proxy Management: Dukungan routing proxy HTTP/SOCKS (format URL atau host:port:user:pass).
5. Lifecycle Hygiene: Pembersihan profil sementara secara otomatis dan aman (zero disk leak).
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse
from patchright.async_api import async_playwright

BLOCKED_MEDIA_EXTS = (
    ".mp4", ".webm", ".avi", ".mov", ".mkv",
    ".mp3", ".ogg", ".wav", ".aac"
)

BLOCKED_AD_DOMAINS = (
    "youtube.com", "youtu.be", "vimeo.com", "jwplatform.com", "dailymotion.com",
    "outbrain.com", "taboola.com", "adnxs.com", "criteo.com", "adfox.ru",
    "disqus.com", "addthis.com", "google-analytics.com", "googletagmanager.com",
    "doubleclick.net", "facebook.net", "connect.facebook.net"
)

def resolve_target_url(target: str) -> str:
    """Mengonversi path lokal menjadi URL file:// jika bukan skema HTTP/HTTPS."""
    if target.startswith("http://") or target.startswith("https://") or target.startswith("file://"):
        return target
    p = Path(target).resolve()
    if p.exists():
        return f"file://{p}"
    return target

def parse_proxy_arg(proxy_str: str) -> dict:
    """Mem-parsing string proxy (URL atau host:port[:user:pass]) menjadi format Patchright."""
    if not proxy_str:
        return None
    proxy_str = proxy_str.strip()
    if "://" in proxy_str:
        parsed = urlparse(proxy_str)
        server = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            server += f":{parsed.port}"
        p_dict = {"server": server}
        if parsed.username:
            p_dict["username"] = parsed.username
        if parsed.password:
            p_dict["password"] = parsed.password
        return p_dict

    parts = proxy_str.split(":")
    if len(parts) == 2:
        return {"server": f"http://{parts[0]}:{parts[1]}"}
    elif len(parts) == 4:
        return {
            "server": f"http://{parts[0]}:{parts[1]}",
            "username": parts[2],
            "password": parts[3]
        }
    return {"server": proxy_str}

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
    dark_mode: bool = False,
    fail_on_challenge: bool = False,
    block_ads: bool = False,
    block_media: bool = False,
    proxy_str: str = None,
    user_agent: str = None
):
    """Mengambil tangkapan layar menggunakan Chromium Persistent Context Patchright."""
    target_url = resolve_target_url(url)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    is_google_docs = "docs.google.com" in target_url
    temp_profile_dir = tempfile.mkdtemp(prefix="patchright_profile_")

    try:
        async with async_playwright() as p:
            launch_args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]

            launch_kwargs = {
                "user_data_dir": temp_profile_dir,
                "headless": True,
                "args": launch_args,
                "viewport": {"width": width, "height": height},
                "device_scale_factor": scale,
                "color_scheme": "dark" if dark_mode else "light",
                "timezone_id": "Asia/Jakarta"
            }

            # Eksekusi binary Chromium yang tersedia
            if p.chromium.executable_path and Path(p.chromium.executable_path).exists():
                pass  # Gunakan binary patchright resmi yang sudah di-patch otomatis
            elif Path("/usr/bin/chromium").exists():
                launch_kwargs["executable_path"] = "/usr/bin/chromium"

            # Proxy configuration jika diisi
            proxy_dict = parse_proxy_arg(proxy_str)
            if proxy_dict:
                launch_kwargs["proxy"] = proxy_dict

            # Zero-Spoofing: Hanya gunakan custom user_agent jika eksplisit diminta
            if user_agent:
                launch_kwargs["user_agent"] = user_agent

            # Inisialisasi Persistent Context (Patchright Enhanced Pattern)
            context = await p.chromium.launch_persistent_context(**launch_kwargs)

            # Route filter untuk Traffic & Ad Blocker
            if block_ads or block_media:
                async def route_interceptor(route):
                    req = route.request
                    res_type = req.resource_type
                    req_url = req.url
                    clean_url = req_url.split("?")[0].lower()

                    if block_media:
                        if res_type == "media":
                            await route.abort()
                            return
                        if any(clean_url.endswith(ext) for ext in BLOCKED_MEDIA_EXTS):
                            await route.abort()
                            return

                    if block_ads:
                        if any(domain in req_url for domain in BLOCKED_AD_DOMAINS):
                            await route.abort()
                            return

                    await route.continue_()

                await context.route("**/*", route_interceptor)

            # Dapatkan page aktif atau buat baru
            page = context.pages[0] if context.pages else await context.new_page()

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

            # Validasi Bot Challenge / Cloudflare Verification
            page_title = await page.title()
            page_content = await page.content()
            title_lower = page_title.lower()
            content_lower = page_content.lower()

            challenge_in_title = any(k in title_lower for k in [
                "just a moment...", "security verification", "attention required", "access denied", "403 forbidden"
            ])
            challenge_in_body = any(k in content_lower for k in [
                "performing security verification",
                "this website uses a security service to protect against malicious bots",
                "checking if the site connection is secure",
                "cf-browser-verification",
                "challenge-platform",
                "cf-turnstile",
                "ray id:"
            ])
            is_bot_challenge = challenge_in_title or challenge_in_body
            if is_bot_challenge:
                print(f"[browser-screenshot] WARN: Terdeteksi halaman bot challenge/Cloudflare: '{page_title}'", file=sys.stderr)
                if fail_on_challenge:
                    await context.close()
                    print(f"[browser-screenshot] ERROR: Ditolak karena bot challenge pada URL: {target_url}", file=sys.stderr)
                    sys.exit(2)

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

            await context.close()
            print(f"[browser-screenshot] Berhasil disimpan di: {output_path}")

    finally:
        # Bersihkan direktori temporary profile agar tidak terjadi memory/disk leak
        if os.path.exists(temp_profile_dir):
            shutil.rmtree(temp_profile_dir, ignore_errors=True)

def send_whatsapp_media(file_path: str, recipient: str, caption: str = ""):
    """Mengirim file hasil screenshot ke WhatsApp via helper Whatsmeow."""
    wa_tool_candidates = [
        Path("/app/workspaces/default/skills/whatsmeow/scripts/wa_tool.py"),
        Path("/app/skills/whatsmeow/scripts/wa_tool.py"),
        Path("/root/projects/aina/skills/whatsmeow/scripts/wa_tool.py"),
        Path("/app/workspaces/default/.agents/skills/whatsmeow/scripts/wa_tool.py")
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
        description="Browser Headless Screenshot Tool (Context-Agnostic) berbasis Patchright Chromium Stealth."
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
    parser.add_argument("--fail-on-challenge", action="store_true", help="Gagal (exit code 2) jika terdeteksi halaman Cloudflare / bot challenge")
    parser.add_argument("--block-ads", action="store_true", help="Blokir domain iklan dan pelacak (Google Analytics, Taboola, Outbrain, dll.)")
    parser.add_argument("--block-media", action="store_true", help="Blokir streaming video/audio berat (.mp4, .webm, dll.) untuk menghemat RAM & bandwidth")
    parser.add_argument("--proxy", help="Konfigurasi proxy (contoh: http://127.0.0.1:8080 atau host:port:user:pass)")
    parser.add_argument("--user-agent", help="Kustomisasi User-Agent (opsional, bawaan menggunakan native Patchright stealth)")
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
        dark_mode=args.dark_mode,
        fail_on_challenge=args.fail_on_challenge,
        block_ads=args.block_ads,
        block_media=args.block_media,
        proxy_str=args.proxy,
        user_agent=args.user_agent
    ))

    if args.send_wa:
        send_whatsapp_media(args.output, args.send_wa, args.caption)

if __name__ == "__main__":
    main()
