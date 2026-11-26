#!/usr/bin/env python3
"""
File Seeker CLI - Multi-source file and book discovery tool for Aina.
Supports BitTorrent/Magnet search, Libgen book discovery, and headless downloading via libtorrent.
"""

import sys
import os
import argparse
import json
import re
import html
import time
import urllib.request
import urllib.parse
import ssl

try:
    import libtorrent as lt
    HAS_LIBTORRENT = True
except ImportError:
    HAS_LIBTORRENT = False


def search_torrents(query: str, limit: int = 10) -> list:
    """Search public torrent indexers for magnet links."""
    results = []
    # 1. Bitsearch
    url = f"https://bitsearch.to/search?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            page = resp.read().decode("utf-8", errors="ignore")
            magnets = re.findall(r'href=[\"\'](magnet:\?[^\"\']+)[\"\']', page)
            seen_xt = set()
            for m in magnets:
                clean_m = html.unescape(m)
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(clean_m).query)
                dn = parsed.get("dn", ["Unknown Title"])[0]
                xt = parsed.get("xt", [""])[0]
                if xt and xt not in seen_xt:
                    seen_xt.add(xt)
                    results.append({
                        "source": "bitsearch",
                        "title": dn,
                        "magnet": clean_m,
                        "hash": xt
                    })
                    if len(results) >= limit:
                        break
    except Exception as e:
        sys.stderr.write(f"Bitsearch search error: {e}\n")

    # 2. Apibay (The Pirate Bay) fallback if bitsearch results few
    if len(results) < limit:
        apibay_url = f"https://apibay.org/q.php?q={urllib.parse.quote(query)}"
        try:
            req = urllib.request.Request(apibay_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                for item in data:
                    name = item.get("name", "")
                    info_hash = item.get("info_hash", "")
                    if name and info_hash and info_hash != "0000000000000000000000000000000000000000":
                        mag = f"magnet:?xt=urn:btih:{info_hash}&dn={urllib.parse.quote(name)}&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce"
                        results.append({
                            "source": "thepiratebay",
                            "title": name,
                            "magnet": mag,
                            "hash": f"urn:btih:{info_hash}",
                            "seeders": item.get("seeders", 0),
                            "size_bytes": item.get("size", 0)
                        })
                        if len(results) >= limit:
                            break
        except Exception as e:
            sys.stderr.write(f"Apibay error: {e}\n")

    return results


def search_books(query: str, limit: int = 10) -> list:
    """Search Libgen mirrors for books, returning metadata, MD5, and links."""
    results = []
    url = f"https://libgen.li/index.php?req={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL)
            for r in rows:
                if "md5=" in r:
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
                    clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                    md5_match = re.search(r'md5=([a-zA-Z0-9]{32})', r)
                    md5 = md5_match.group(1) if md5_match else ""
                    
                    file_id_match = re.search(r'file\.php\?id=(\d+)', r)
                    file_id = file_id_match.group(1) if file_id_match else ""

                    if len(clean_cells) >= 8 and md5:
                        first_cell = cells[0]
                        # extract text inside <a> tag if present
                        a_match = re.search(r'<a[^>]*>(.*?)</a>', first_cell, re.DOTALL)
                        if a_match:
                            clean_title = re.sub(r'<[^>]+>', '', a_match.group(1)).strip()
                        else:
                            clean_title = clean_cells[0].split("\n")[0].strip()

                        # clean up duplicated or noisy suffix
                        clean_title = clean_title.split("\n")[0].strip()
                        for delim in [" — ", " - "]:
                            if delim in clean_title:
                                clean_title = clean_title.split(delim)[0].strip()

                        author = clean_cells[1]
                        publisher = clean_cells[2]
                        year = clean_cells[3]
                        language = clean_cells[4]
                        pages = clean_cells[5]
                        size = clean_cells[6]
                        extension = clean_cells[7]

                        results.append({
                            "title": clean_title,
                            "author": author,
                            "publisher": publisher,
                            "year": year,
                            "language": language,
                            "pages": pages,
                            "size": size,
                            "format": extension,
                            "md5": md5,
                            "file_id": file_id,
                            "libgen_url": f"https://libgen.li/ads.php?md5={md5}",
                            "file_info_url": f"https://libgen.li/file.php?id={file_id}" if file_id else ""
                        })
                        if len(results) >= limit:
                            break
    except Exception as e:
        sys.stderr.write(f"Libgen search error: {e}\n")

    return results


def download_torrent_headless(magnet_or_file: str, save_path: str = "downloads", timeout_sec: int = 120) -> dict:
    """Download a torrent or magnet headless using libtorrent without TUI."""
    if not HAS_LIBTORRENT:
        return {"ok": False, "error": "libtorrent package is not installed"}

    os.makedirs(save_path, exist_ok=True)
    ses = lt.session({"listen_interfaces": "0.0.0.0:6881"})
    ses.apply_settings({"enable_dht": True})

    if magnet_or_file.startswith("magnet:"):
        params = lt.parse_magnet_uri(magnet_or_file)
        params.save_path = save_path
        handle = ses.add_torrent(params)
    else:
        if not os.path.exists(magnet_or_file):
            return {"ok": False, "error": f"File not found: {magnet_or_file}"}
        info = lt.torrent_info(magnet_or_file)
        params = lt.add_torrent_params()
        params.ti = info
        params.save_path = save_path
        handle = ses.add_torrent(params)

    start_time = time.time()
    sys.stderr.write(f"Waiting for torrent download (timeout {timeout_sec}s)...\n")
    
    while time.time() - start_time < timeout_sec:
        st = handle.status()
        if st.is_seeding or st.progress >= 1.0:
            return {
                "ok": True,
                "name": handle.torrent_file().name() if st.has_metadata else "Downloaded",
                "save_path": os.path.abspath(save_path),
                "total_bytes": st.total_done
            }
        time.sleep(2)
        if st.has_metadata:
            sys.stderr.write(f"Progress: {st.progress*100:.1f}%, Peers: {st.num_peers}, Down: {st.download_rate/1024:.1f} KB/s\n")

    st = handle.status()
    return {
        "ok": False,
        "error": "Timeout waiting for download completion",
        "progress": f"{st.progress*100:.1f}%",
        "peers": st.num_peers,
        "seeds": st.num_seeds
    }


def download_http(url: str, out_path: str) -> dict:
    """Download an HTTP/HTTPS file stream safely."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            bytes_written = 0
            with open(out_path, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 64)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_written += len(chunk)
            return {
                "ok": True,
                "path": os.path.abspath(out_path),
                "bytes": bytes_written,
                "content_type": resp.headers.get("Content-Type", "")
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Multi-source File and Book Discovery Tool for Aina")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # search-torrent
    p_st = subparsers.add_parser("search-torrent", help="Search public torrent indexers for magnet links")
    p_st.add_argument("query", help="Keyword or title to search")
    p_st.add_argument("--limit", type=int, default=10, help="Maximum results to return")
    p_st.add_argument("--json", action="store_true", help="Output in JSON format")

    # search-book
    p_sb = subparsers.add_parser("search-book", help="Search Libgen indexers for books and documents")
    p_sb.add_argument("query", help="Book title, author, or ISBN")
    p_sb.add_argument("--limit", type=int, default=10, help="Maximum results to return")
    p_sb.add_argument("--json", action="store_true", help="Output in JSON format")

    # download-torrent
    p_dt = subparsers.add_parser("download-torrent", help="Download torrent/magnet headless via libtorrent")
    p_dt.add_argument("source", help="Magnet URI or path to .torrent file")
    p_dt.add_argument("--save-path", default="downloads", help="Destination folder")
    p_dt.add_argument("--timeout", type=int, default=60, help="Download timeout in seconds")

    # download-http
    p_dh = subparsers.add_parser("download-http", help="Download a direct HTTP/HTTPS file")
    p_dh.add_argument("url", help="Direct download URL")
    p_dh.add_argument("--out", required=True, help="Destination file path")

    args = parser.parse_args()

    if args.subcommand == "search-torrent":
        results = search_torrents(args.query, args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"Tidak ada hasil torrent ditemukan untuk: '{args.query}'")
            else:
                print(f"Ditemukan {len(results)} hasil torrent:")
                for i, r in enumerate(results, 1):
                    print(f"{i}. {r['title']}")
                    print(f"   Source: {r.get('source')} | Hash: {r.get('hash')}")
                    print(f"   Magnet: {r.get('magnet')[:90]}...")

    elif args.subcommand == "search-book":
        results = search_books(args.query, args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"Tidak ada buku ditemukan di katalog untuk: '{args.query}'")
            else:
                print(f"Ditemukan {len(results)} entri buku:")
                for i, r in enumerate(results, 1):
                    print(f"{i}. {r['title']} - {r['author']} ({r['year']})")
                    print(f"   Format: {r['format'].upper()} | Size: {r['size']} | Penerbit: {r['publisher']}")
                    print(f"   MD5: {r['md5']}")
                    print(f"   Download Info: {r['libgen_url']}")

    elif args.subcommand == "download-torrent":
        res = download_torrent_headless(args.source, args.save_path, args.timeout)
        print(json.dumps(res, indent=2))

    elif args.subcommand == "download-http":
        res = download_http(args.url, args.out)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
