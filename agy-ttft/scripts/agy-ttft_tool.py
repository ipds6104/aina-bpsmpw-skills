#!/usr/bin/env python3
"""
agy-ttft_tool.py - High-precision Time To First Token (TTFT) and Cloud Latency Profiler for AGY CLI.

Measures and separates:
1. Local CLI Overhead: Bootstrap, runtime initialization, and prompt preparation.
2. Cloud TTFT (Pure Cloud Time): From cloud request dispatch (user_input DONE) until first token arrives.
3. End-to-End TTFT: Total elapsed time from CLI launch to first token reception.
4. Streaming Duration & Throughput: Tokens per second generation rate.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, Any, List, Optional


def check_agy_available() -> bool:
    return shutil.which("agy") is not None


def run_single_measurement(
    model: str = "gemini-3.8-flash-high",
    prompt: str = "Halo, sebutkan 3 warna pelangi singkat saja.",
    clean_workspace: bool = True,
    timeout: int = 60
) -> Dict[str, Any]:
    if not check_agy_available():
        return {
            "status": "error",
            "message": "Biner 'agy' tidak ditemukan di PATH sistem."
        }

    work_dir = None
    if clean_workspace:
        work_dir = tempfile.mkdtemp(prefix="agy_bench_")
    else:
        work_dir = os.getcwd()

    cmd = [
        "agy",
        "-p", prompt,
        "--model", model,
        "--output-format", "stream-json",
        "--disable-slash-commands"
    ]

    t_proc_start = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=work_dir
    )

    t_init = None
    t_cloud_dispatch = None
    t_first_token = None
    t_response_done = None
    first_token_snippet = ""
    accumulated_text = []
    server_duration = None
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "thinking_tokens": 0,
        "cache_read_tokens": 0,
        "total_tokens": 0
    }
    raw_error = None

    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            now = time.perf_counter()
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                event = data.get("event")

                if event == "init" and t_init is None:
                    t_init = now

                elif event == "step_update":
                    su = data.get("step_update", {})
                    stype = su.get("step_type")
                    state = su.get("state")
                    delta = su.get("text_delta")

                    if stype == "user_input" and state == "DONE" and t_cloud_dispatch is None:
                        t_cloud_dispatch = now

                    elif stype == "agent_response":
                        if delta:
                            accumulated_text.append(delta)
                            if t_first_token is None:
                                t_first_token = now
                                first_token_snippet = delta.strip()

                        if state == "DONE":
                            t_response_done = now
                            if "duration_seconds" in su and su["duration_seconds"] is not None:
                                server_duration = float(su["duration_seconds"])
                            if "usage" in su and isinstance(su["usage"], dict):
                                usage.update(su["usage"])

                elif event == "result":
                    res = data.get("result", {})
                    if res.get("status") == "ERROR":
                        raw_error = res.get("error") or "Unknown error"
                    if "usage" in res and isinstance(res["usage"], dict):
                        usage.update(res["usage"])
                    if "duration_seconds" in res and server_duration is None:
                        server_duration = float(res["duration_seconds"])

            except json.JSONDecodeError:
                pass

        proc.wait(timeout=timeout)
        t_proc_end = time.perf_counter()

    except subprocess.TimeoutExpired:
        proc.kill()
        return {
            "status": "error",
            "message": f"Pengukuran timeout setelah {timeout} detik."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Terjadi kesalahan eksekusi: {str(e)}"
        }
    finally:
        if clean_workspace and work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

    if raw_error:
        return {
            "status": "error",
            "message": f"Model error: {raw_error}"
        }

    total_proc_time = t_proc_end - t_proc_start
    local_overhead = (t_cloud_dispatch - t_proc_start) if t_cloud_dispatch else (total_proc_time)
    cloud_ttft = (t_first_token - t_cloud_dispatch) if (t_first_token and t_cloud_dispatch) else None
    e2e_ttft = (t_first_token - t_proc_start) if t_first_token else None
    streaming_duration = (t_response_done - t_first_token) if (t_response_done and t_first_token) else 0.0

    output_tokens = usage.get("output_tokens", 0)
    throughput_tps = (output_tokens / streaming_duration) if (streaming_duration > 0 and output_tokens > 0) else 0.0

    return {
        "status": "success",
        "model": model,
        "prompt": prompt,
        "metrics": {
            "local_overhead_seconds": round(local_overhead, 4),
            "local_overhead_ms": round(local_overhead * 1000, 1),
            "cloud_ttft_seconds": round(cloud_ttft, 4) if cloud_ttft is not None else None,
            "cloud_ttft_ms": round(cloud_ttft * 1000, 1) if cloud_ttft is not None else None,
            "e2e_ttft_seconds": round(e2e_ttft, 4) if e2e_ttft is not None else None,
            "e2e_ttft_ms": round(e2e_ttft * 1000, 1) if e2e_ttft is not None else None,
            "streaming_duration_seconds": round(streaming_duration, 4),
            "total_proc_seconds": round(total_proc_time, 4),
            "server_reported_duration_seconds": round(server_duration, 4) if server_duration is not None else None,
            "throughput_tokens_per_sec": round(throughput_tps, 2)
        },
        "usage": usage,
        "first_token_snippet": first_token_snippet[:60],
        "response_preview": "".join(accumulated_text).strip()[:100]
    }


def cmd_status(args):
    agy_path = shutil.which("agy")
    if not agy_path:
        print(json.dumps({
            "status": "not_ready",
            "skill": "agy-ttft",
            "message": "Biner agy tidak ditemukan di PATH."
        }, indent=2))
        return

    # Check available models
    models = []
    try:
        proc = subprocess.run(["agy", "models"], capture_output=True, text=True, timeout=10)
        for line in proc.stdout.splitlines():
            parts = line.strip().split()
            if parts and not parts[0].startswith("⠋") and not parts[0].startswith("⠙"):
                models.append(parts[0])
    except Exception:
        pass

    print(json.dumps({
        "status": "ready",
        "skill": "agy-ttft",
        "binary_path": agy_path,
        "available_models": models,
        "default_target": "gemini-3.8-flash-high",
        "message": "Tool siap untuk mengukur TTFT dan latensi cloud AGY CLI"
    }, indent=2))


def cmd_measure(args):
    runs = max(1, args.runs)
    results = []

    for r in range(runs):
        res = run_single_measurement(
            model=args.model,
            prompt=args.prompt,
            clean_workspace=not args.keep_workspace,
            timeout=args.timeout
        )
        results.append(res)

    if runs == 1:
        single = results[0]
        if args.format == "json":
            print(json.dumps(single, indent=2))
        else:
            format_human_output(single)
        return

    # Aggregate metrics if multiple runs
    successful_runs = [r for r in results if r.get("status") == "success"]
    if not successful_runs:
        print(json.dumps({
            "status": "error",
            "message": "Semua pengujian gagal dieksekusi.",
            "details": results
        }, indent=2))
        return

    cloud_ttfts = [r["metrics"]["cloud_ttft_ms"] for r in successful_runs if r["metrics"]["cloud_ttft_ms"] is not None]
    local_ovhs = [r["metrics"]["local_overhead_ms"] for r in successful_runs]
    e2e_ttfts = [r["metrics"]["e2e_ttft_ms"] for r in successful_runs if r["metrics"]["e2e_ttft_ms"] is not None]

    summary = {
        "status": "success",
        "model": args.model,
        "total_runs": runs,
        "successful_runs": len(successful_runs),
        "averages": {
            "avg_cloud_ttft_ms": round(sum(cloud_ttfts) / len(cloud_ttfts), 1) if cloud_ttfts else None,
            "min_cloud_ttft_ms": min(cloud_ttfts) if cloud_ttfts else None,
            "max_cloud_ttft_ms": max(cloud_ttfts) if cloud_ttfts else None,
            "avg_local_overhead_ms": round(sum(local_ovhs) / len(local_ovhs), 1),
            "avg_e2e_ttft_ms": round(sum(e2e_ttfts) / len(e2e_ttfts), 1) if e2e_ttfts else None
        },
        "runs": results
    }

    if args.format == "json":
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n*HASIL REKAPITULASI BENCHMARK TTFT ({args.model})*")
        print(f"• Jumlah Pengujian: {runs} run")
        print(f"• *Cloud TTFT (Murni Cloud)*: avg {summary['averages']['avg_cloud_ttft_ms']} ms (min: {summary['averages']['min_cloud_ttft_ms']} ms, max: {summary['averages']['max_cloud_ttft_ms']} ms)")
        print(f"• *Local CLI Overhead*: avg {summary['averages']['avg_local_overhead_ms']} ms")
        print(f"• *End-to-End CLI TTFT*: avg {summary['averages']['avg_e2e_ttft_ms']} ms\n")


def cmd_compare(args):
    models = args.models or ["gemini-3.8-flash-low", "gemini-3.8-flash-medium", "gemini-3.8-flash-high"]
    comparisons = []

    for m in models:
        res = run_single_measurement(
            model=m,
            prompt=args.prompt,
            clean_workspace=True,
            timeout=args.timeout
        )
        comparisons.append(res)

    if args.format == "json":
        print(json.dumps({"status": "success", "comparisons": comparisons}, indent=2))
        return

    print("\n*KOMPARASI TTFT & LATENSI MODEL GEMINI (AGY CLI)*")
    print(f"Prompt: \"{args.prompt}\"\n")
    for r in comparisons:
        if r.get("status") == "success":
            m = r["model"]
            met = r["metrics"]
            usg = r.get("usage", {})
            cloud_ttft = met.get("cloud_ttft_ms", 0)
            local_ovh = met.get("local_overhead_ms", 0)
            total_sec = met.get("total_proc_seconds", 0)
            thinking = usg.get("thinking_tokens", 0)
            out_tokens = usg.get("output_tokens", 0)

            print(f"• *{m}*:")
            print(f"  - Cloud TTFT (Murni Cloud): *{cloud_ttft} ms* ({met.get('cloud_ttft_seconds')}s)")
            print(f"  - Local CLI Overhead: {local_ovh} ms ({met.get('local_overhead_seconds')}s)")
            print(f"  - Total Waktu Eksekusi: {total_sec}s")
            print(f"  - Tokens: {out_tokens} out (termasuk {thinking} thinking tokens)")
        else:
            print(f"• *{r.get('model')}*: Gagal ({r.get('message')})")
    print("")


def format_human_output(result: Dict[str, Any]):
    if result.get("status") != "success":
        print(f"Gagal mengukur TTFT: {result.get('message')}")
        return

    m = result["model"]
    met = result["metrics"]
    usg = result.get("usage", {})
    first_tok = result.get("first_token_snippet", "")
    preview = result.get("response_preview", "")

    print(f"\n*PROFIL WAKTU TIME TO FIRST TOKEN (TTFT) - {m}*")
    print(f"• *Cloud TTFT (Murni Panggilan Cloud)*: *{met['cloud_ttft_ms']} ms* ({met['cloud_ttft_seconds']}s)")
    print(f"• *Local CLI Overhead (Bootstrap & Init)*: *{met['local_overhead_ms']} ms* ({met['local_overhead_seconds']}s)")
    print(f"• *End-to-End CLI TTFT (Total dari Start)*: *{met['e2e_ttft_ms']} ms* ({met['e2e_ttft_seconds']}s)")
    print(f"• *Streaming Generation Duration*: {met['streaming_duration_seconds']}s")
    print(f"• *Throughput Generator*: {met['throughput_tokens_per_sec']} tokens/detik")
    print(f"• *Total Waktu Proses*: {met['total_proc_seconds']}s")
    print(f"• *Token Usage*: {usg.get('input_tokens', 0)} in | {usg.get('output_tokens', 0)} out ({usg.get('thinking_tokens', 0)} thinking)")
    print(f"• *First Token Chunk*: `{first_tok}`")
    print(f"• *Cuplikan Respon*: \"{preview}...\"\n")


def main():
    parser = argparse.ArgumentParser(description="AGY CLI TTFT & Latency Profiler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Cek kesiapan agy dan model")
    p_status.set_defaults(func=cmd_status)

    # measure
    p_measure = subparsers.add_parser("measure", help="Ukur TTFT model tertentu")
    p_measure.add_argument("--model", "-m", default="gemini-3.8-flash-high", help="Nama model AGY (default: gemini-3.8-flash-high)")
    p_measure.add_argument("--prompt", "-p", default="Halo, sebutkan 3 warna pelangi singkat saja.", help="Teks prompt")
    p_measure.add_argument("--runs", "-n", type=int, default=1, help="Jumlah perulangan benchmark")
    p_measure.add_argument("--format", "-f", choices=["wa", "json"], default="wa", help="Format output (wa/json)")
    p_measure.add_argument("--keep-workspace", action="store_true", help="Gunakan direktori kerja aktif alih-alih clean temp dir")
    p_measure.add_argument("--timeout", "-t", type=int, default=60, help="Batas timeout per request dalam detik")
    p_measure.set_defaults(func=cmd_measure)

    # compare
    p_comp = subparsers.add_parser("compare", help="Bandingkan TTFT antar model (flash-low, medium, high)")
    p_comp.add_argument("--models", nargs="+", default=["gemini-3.8-flash-low", "gemini-3.8-flash-medium", "gemini-3.8-flash-high"], help="Daftar model yang ingin dibandingkan")
    p_comp.add_argument("--prompt", "-p", default="Halo, sebutkan 3 warna pelangi singkat saja.", help="Teks prompt")
    p_comp.add_argument("--format", "-f", choices=["wa", "json"], default="wa", help="Format output (wa/json)")
    p_comp.add_argument("--timeout", "-t", type=int, default=60, help="Batas timeout per request dalam detik")
    p_comp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
