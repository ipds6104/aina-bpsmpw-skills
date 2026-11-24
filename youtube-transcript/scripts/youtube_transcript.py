#!/usr/bin/env python3
"""
youtube_transcript.py
---------------------
CLI Tool & Engine ekstraksi transkrip / subtitle video YouTube secara instan.
Mendukung video biasa, live replay, Shorts, dan tautan pendek youtu.be.

Prioritas:
1. youtube-transcript-api (Cepat, direct HTTP API ke YouTube timedtext, ~1 detik)
2. yt-dlp fallback (Jika butuh ekstrasi auto-sub rumit)
"""

import os
import re
import sys
import json
import argparse
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Cek uv binary
UV_BIN = "/app/data/bin/uv" if os.path.exists("/app/data/bin/uv") else "uv"

def extract_video_id(url_or_id: str) -> str:
    """Mengekstrak 11-karakter YouTube Video ID dari berbagai format URL."""
    url_or_id = url_or_id.strip()
    if re.fullmatch(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id
    
    # Format: youtu.be/<id>
    if "youtu.be/" in url_or_id:
        match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url_or_id)
        if match:
            return match.group(1)
            
    # Format: youtube.com/watch?v=<id>
    if "watch?v=" in url_or_id:
        match = re.search(r"watch\?v=([a-zA-Z0-9_-]{11})", url_or_id)
        if match:
            return match.group(1)

    # Format: youtube.com/live/<id>
    if "/live/" in url_or_id:
        match = re.search(r"/live/([a-zA-Z0-9_-]{11})", url_or_id)
        if match:
            return match.group(1)

    # Format: youtube.com/shorts/<id>
    if "/shorts/" in url_or_id:
        match = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", url_or_id)
        if match:
            return match.group(1)

    # Fallback general query
    parsed = urlparse(url_or_id)
    qs = parse_qs(parsed.query)
    if "v" in qs and qs["v"]:
        return qs["v"][0]

    raise ValueError(f"Tidak dapat mengekstrak Video ID dari URL: {url_or_id}")

def format_timestamp(seconds: float) -> str:
    """Konversi detik ke format MM:SS atau HH:MM:SS."""
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def get_transcript_via_api(video_id: str, languages: list) -> list:
    """Mengambil transkrip menggunakan youtube_transcript_api dan mengembalikan list of dict."""
    from youtube_transcript_api import YouTubeTranscriptApi
    ytt = YouTubeTranscriptApi()
    
    # Cari daftar transkrip yang tersedia
    transcript_list = ytt.list(video_id)
    
    fetched = None
    # Coba cari manual transcript
    try:
        t = transcript_list.find_manually_created_transcript(languages)
        fetched = t.fetch()
    except Exception:
        pass

    # Coba cari generated transcript
    if fetched is None:
        try:
            t = transcript_list.find_generated_transcript(languages)
            fetched = t.fetch()
        except Exception:
            pass

    # Fallback ke transcript pertama apa pun
    if fetched is None:
        for tr in transcript_list:
            fetched = tr.fetch()
            break

    if fetched is None:
        raise RuntimeError(f"Tidak ada transkrip untuk video {video_id}")

    # Normalisasi ke list of dict
    results = []
    for s in fetched:
        if isinstance(s, dict):
            results.append(s)
        else:
            results.append({
                "text": getattr(s, "text", ""),
                "start": getattr(s, "start", 0.0),
                "duration": getattr(s, "duration", 0.0)
            })
    return results

def main():
    parser = argparse.ArgumentParser(description="YouTube Transcript Extractor CLI")
    parser.add_argument("url", help="URL Video YouTube atau Video ID")
    parser.add_argument("-o", "--output", help="Simpan output ke file (Markdown / Text / JSON)")
    parser.add_argument(
        "-f", "--format",
        choices=["text", "timestamp", "json"],
        default="text",
        help="Format keluaran: 'text' (paragraf rapi), 'timestamp' ([MM:SS] teks), 'json' (array data mentah)"
    )
    parser.add_argument(
        "--lang",
        default="id,en",
        help="Prioritas kode bahasa dipisahkan koma (default: 'id,en')"
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="Batas maksimum karakter (0 = tanpa batas)"
    )

    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    lang_list = [l.strip() for l in args.lang.split(",") if l.strip()]

    # Jalankan ekstraksi via youtube_transcript_api
    try:
        segments = get_transcript_via_api(video_id, lang_list)
    except ImportError:
        # Re-execute via uv
        import subprocess
        cmd = [
            UV_BIN, "run", "--with", "youtube-transcript-api",
            "python3", __file__, args.url,
            "-f", args.format,
            "--lang", args.lang
        ]
        if args.output:
            cmd.extend(["-o", args.output])
        if args.max_chars > 0:
            cmd.extend(["--max-chars", str(args.max_chars)])
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Gagal mengambil transkrip via API: {e}", file=sys.stderr)
        # Fallback via yt-dlp jika API gagal
        print("Mencoba fallback via yt-dlp...", file=sys.stderr)
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                UV_BIN, "run", "--with", "yt-dlp",
                "yt-dlp",
                "--write-auto-sub",
                "--write-sub",
                "--sub-lang", args.lang,
                "--skip-download",
                "--sub-format", "vtt/srv3/ttml",
                "-o", f"{tmpdir}/sub",
                f"https://www.youtube.com/watch?v={video_id}"
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Cari file sub
            sub_files = list(Path(tmpdir).glob("sub*"))
            if not sub_files:
                print(f"Error: Tidak ditemukan transkrip atau subtitle untuk video {video_id}.", file=sys.stderr)
                sys.exit(1)
            # Parse vtt sederhana
            raw_text = sub_files[0].read_text(encoding="utf-8", errors="ignore")
            # Bersihkan tag VTT
            clean_lines = []
            for line in raw_text.splitlines():
                if "-->" in line or line.startswith("WEBVTT") or line.strip().isdigit() or not line.strip():
                    continue
                # buang tag html seperti <c>...</c>
                clean = re.sub(r"<[^>]+>", "", line).strip()
                if clean and (not clean_lines or clean_lines[-1] != clean):
                    clean_lines.append(clean)
            
            output_content = "\n".join(clean_lines)
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(output_content, encoding="utf-8")
                print(f"Transkrip berhasil disimpan ke: {args.output}")
            else:
                print(output_content)
            sys.exit(0)

    # Format hasil
    if args.format == "json":
        formatted_output = json.dumps(segments, indent=2, ensure_ascii=False)
    elif args.format == "timestamp":
        lines = []
        for s in segments:
            ts = format_timestamp(s.get("start", 0))
            text = s.get("text", "").strip()
            if text:
                lines.append(f"[{ts}] {text}")
        formatted_output = "\n".join(lines)
    else:  # text
        # Gabungkan segmen menjadi teks mengalir
        raw_texts = [s.get("text", "").strip() for s in segments if s.get("text", "").strip()]
        # Kelompokkan per ~3-4 kalimat
        full_text = " ".join(raw_texts)
        # Rapikan spasi ganda
        full_text = re.sub(r"\s+", " ", full_text)
        formatted_output = full_text

    if args.max_chars > 0 and len(formatted_output) > args.max_chars:
        formatted_output = formatted_output[:args.max_chars] + "\n\n... [Transkrip dipotong sesuai batas max-chars]"

    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(formatted_output, encoding="utf-8")
        print(f"Transkrip berhasil disimpan ke: {args.output} ({len(formatted_output)} karakter)")
    else:
        print(formatted_output)

if __name__ == "__main__":
    main()
