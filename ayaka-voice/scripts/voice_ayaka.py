#!/usr/bin/env python3
"""
Multi-Character Voice Synthesis & Telemetry Engine (Supertonic-3 + RVC v2)
Custom Skill for Aina: Generates zero-shot character voice notes with telemetry.
Supported Characters: Ayaka, Amber, Mualani, Yanfei, Yumemizuki Mizuki
"""
import os
import sys
import time
import json
import uuid
import argparse
import traceback
import subprocess
from datetime import datetime

# Persistent directories
BASE_SKILL_DIR = "/app/data/custom-skills/ayaka-voice"
LOG_DIR = os.path.join(BASE_SKILL_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

TELEMETRY_FILE = os.path.join(LOG_DIR, "telemetry.jsonl")
EXEC_LOG_FILE = os.path.join(LOG_DIR, "voice.log")

OUT_DIR = "/app/workspaces/default/output/voice"
os.makedirs(OUT_DIR, exist_ok=True)

BASE_RVC_DIR = "/app/workspaces/default/models/rvc"

CHARACTERS = {
    "ayaka": {
        "name": "Kamisato Ayaka",
        "folder": os.path.join(BASE_RVC_DIR, "ayaka_jp_v2"),
        "voice_style": "F1",
        "pitch": 0
    },
    "amber": {
        "name": "Amber",
        "folder": os.path.join(BASE_RVC_DIR, "amber_jp"),
        "voice_style": "F1",
        "pitch": 0
    },
    "mualani": {
        "name": "Mualani",
        "folder": os.path.join(BASE_RVC_DIR, "mualani_jp"),
        "voice_style": "F2",
        "pitch": 1
    },
    "yanfei": {
        "name": "Yanfei",
        "folder": os.path.join(BASE_RVC_DIR, "yanfei_jp"),
        "voice_style": "F1",
        "pitch": 0
    },
    "mizuki": {
        "name": "Yumemizuki Mizuki",
        "folder": os.path.join(BASE_RVC_DIR, "mizuki_jp"),
        "voice_style": "F4",
        "pitch": 0
    }
}

CPU_THREADS = 2

def init_env():
    import torch
    torch.set_num_threads(CPU_THREADS)
    torch.set_num_interop_threads(1)
    os.environ["OMP_NUM_THREADS"] = str(CPU_THREADS)
    os.environ["MKL_NUM_THREADS"] = str(CPU_THREADS)

def log_event(level, msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(EXEC_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def record_telemetry(record):
    with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def find_model_and_index(folder):
    pth_file = None
    index_file = None
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.endswith('.pth') and not pth_file:
                pth_file = os.path.join(root, f)
            elif f.endswith('.index') and not index_file:
                index_file = os.path.join(root, f)
    return pth_file, index_file

def synthesize(text, char="ayaka", tts_engine="supertonic", to_jid=None, output_path=None, pitch_shift=None):
    init_env()
    run_id = f"v_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    iso_now = datetime.now().isoformat()

    char_key = char.lower()
    if char_key not in CHARACTERS:
        char_key = "ayaka"

    char_cfg = CHARACTERS[char_key]
    char_name = char_cfg["name"]

    log_event("INFO", f"[{run_id}] Mulai sintesis ({char_name}, TTS={tts_engine}, len={len(text)}): '{text}'")

    telemetry_record = {
        "run_id": run_id,
        "timestamp": iso_now,
        "character": char_name,
        "char_key": char_key,
        "text": text,
        "text_length": len(text),
        "tts_engine": tts_engine,
        "cpu_threads": CPU_THREADS,
        "recipient": to_jid,
        "status": "PENDING"
    }

    try:
        pth_path, index_path = find_model_and_index(char_cfg["folder"])
        if not pth_path:
            raise FileNotFoundError(f"Model .pth tidak ditemukan di {char_cfg['folder']}")

        raw_wav = os.path.join(OUT_DIR, f"{run_id}_base.wav")
        raw_48k = os.path.join(OUT_DIR, f"{run_id}_48k.wav")
        final_ogg = output_path or os.path.join(OUT_DIR, f"{run_id}_{char_key}.ogg")

        # Step 1: Base TTS
        t_tts_start = time.time()
        if tts_engine == "supertonic":
            import soundfile as sf
            from supertonic import TTS
            tts = TTS(model="supertonic-3", intra_op_num_threads=CPU_THREADS)
            style = tts.get_voice_style(char_cfg.get("voice_style", "F1"))
            wav, _ = tts.synthesize(text=text, voice_style=style, total_steps=8, speed=1.0, lang="id")
            samples = wav.squeeze()
            audio_duration = len(samples) / tts.sample_rate
            sf.write(raw_wav, samples, tts.sample_rate)
        else:
            # Edge-TTS fallback
            raw_mp3 = os.path.join(OUT_DIR, f"{run_id}_edge.mp3")
            subprocess.run(["edge-tts", "--voice", "id-ID-GadisNeural", "--text", text, "--write-media", raw_mp3], check=True)
            subprocess.run(["ffmpeg", "-y", "-i", raw_mp3, "-ar", "48000", "-ac", "1", raw_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(raw_mp3):
                os.remove(raw_mp3)
            audio_duration = 1.0

        t_tts = time.time() - t_tts_start

        # Resample to 48kHz mono
        subprocess.run(["ffmpeg", "-y", "-i", raw_wav, "-ar", "48000", "-ac", "1", raw_48k], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(raw_wav):
            os.remove(raw_wav)

        # Step 2: RVC Conversion
        t_rvc_start = time.time()
        from infer_rvc_python import BaseLoader
        loader = BaseLoader(only_cpu=True)
        pitch = pitch_shift if pitch_shift is not None else char_cfg.get("pitch", 0)
        tag = f"char_{char_key}"
        loader.apply_conf(
            tag=tag,
            file_model=pth_path,
            file_index=index_path or "",
            pitch_algo="pm",
            pitch_lvl=pitch,
            index_influence=0.7,
            respiration_median_filtering=3,
            envelope_ratio=0.25,
            consonant_breath_protection=0.33,
            resample_sr=48000
        )
        out = loader(audio_files=[raw_48k], tag_list=[tag], overwrite=True, type_output="wav", show_progress=False)
        t_rvc = time.time() - t_rvc_start

        converted_wav = out[0] if (isinstance(out, list) and len(out) > 0) else raw_48k

        # Step 3: Opus Transcode
        subprocess.run(["ffmpeg", "-y", "-i", converted_wav, "-c:a", "libopus", "-b:a", "32k", "-ar", "48000", "-ac", "1", final_ogg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(raw_48k):
            os.remove(raw_48k)

        total_duration = time.time() - start_time
        rtf = t_rvc / audio_duration if audio_duration > 0 else 0.0

        log_event("SUCCESS", f"[{run_id}] Selesai! Audio {audio_duration:.2f}s selesai dalam {total_duration:.2f}s (RVC: {t_rvc:.2f}s, RTF: {rtf:.2f}x). File: {final_ogg}")

        telemetry_record.update({
            "status": "SUCCESS",
            "audio_duration_sec": round(audio_duration, 2),
            "inference_duration_sec": round(t_rvc, 2),
            "total_duration_sec": round(total_duration, 2),
            "rtf": round(rtf, 2),
            "output_file": final_ogg,
            "error": None
        })

        if to_jid:
            log_event("INFO", f"[{run_id}] Mengirim voice note ke WhatsApp: {to_jid}")
            wa_tool = "/app/workspaces/default/skills/whatsmeow/scripts/wa_tool.py"
            send_cmd = [sys.executable, wa_tool, "send-media", "--to", to_jid, "--file", final_ogg, "--type", "voice"]
            res = subprocess.run(send_cmd, capture_output=True, text=True)
            if res.returncode == 0:
                log_event("INFO", f"[{run_id}] Berhasil dikirim ke WhatsApp.")
                telemetry_record["whatsapp_sent"] = True
            else:
                log_event("WARN", f"[{run_id}] Gagal kirim ke WhatsApp: {res.stderr}")
                telemetry_record["whatsapp_sent"] = False

        record_telemetry(telemetry_record)
        return final_ogg

    except Exception as e:
        err_msg = str(e)
        stack = traceback.format_exc()
        log_event("ERROR", f"[{run_id}] Gagal: {err_msg}\n{stack}")
        telemetry_record.update({
            "status": "FAILED",
            "error": err_msg,
            "traceback": stack,
            "total_duration_sec": round(time.time() - start_time, 2)
        })
        record_telemetry(telemetry_record)
        raise

def show_telemetry_summary():
    if not os.path.exists(TELEMETRY_FILE):
        print("Belum ada data telemetry yang tercatat.")
        return

    records = []
    with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    total = len(records)
    if total == 0:
        print("Data telemetry kosong.")
        return

    successes = [r for r in records if r.get("status") == "SUCCESS"]
    failed = [r for r in records if r.get("status") == "FAILED"]
    success_rate = (len(successes) / total) * 100

    avg_latency = (
        sum(r.get("inference_duration_sec", 0) for r in successes) / len(successes)
        if successes else 0
    )
    avg_rtf = (
        sum(r.get("rtf", 0) for r in successes) / len(successes)
        if successes else 0
    )

    print("=" * 60)
    print("📊 MULTI-CHARACTER VOICE SYNTHESIS TELEMETRY")
    print("=" * 60)
    print(f"Total Permintaan       : {total}")
    print(f"Tingkat Keberhasilan   : {success_rate:.1f}% ({len(successes)} sukses, {len(failed)} gagal)")
    print(f"Rata-rata Durasi Infer : {avg_latency:.2f} detik")
    print(f"Rata-rata RTF (Factor) : {avg_rtf:.2f}x (durasi inferensi / durasi audio)")
    print(f"Thread CPU Dibatasi    : {CPU_THREADS} Core")
    print("-" * 60)
    print("5 Riwayat Terakhir:")
    for r in records[-5:]:
        ts = r.get("timestamp", "-")[:19]
        st = r.get("status", "-")
        char = r.get("character", "Ayaka")
        txt = (r.get("text", "")[:25] + "...") if len(r.get("text", "")) > 25 else r.get("text", "")
        dur = f"{r.get('inference_duration_sec', 0):.1f}s"
        rtf = f"RTF: {r.get('rtf', 0):.2f}"
        print(f" • [{ts}] [{char}] [{st}] {dur} ({rtf}) | \"{txt}\"")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Multi-Character Voice Synthesis (Supertonic + RVC v2)")
    parser.add_argument("text", nargs="?", default=None, help="Text to speak in Indonesian")
    parser.add_argument("--char", choices=list(CHARACTERS.keys()), default="ayaka", help="Character voice (default: ayaka)")
    parser.add_argument("--tts", choices=["supertonic", "edge_tts"], default="supertonic", help="Base TTS engine (default: supertonic)")
    parser.add_argument("--to", default=None, help="WhatsApp JID recipient")
    parser.add_argument("--output", default=None, help="Output .ogg path")
    parser.add_argument("--pitch", type=int, default=None, help="Pitch shift semitones")
    parser.add_argument("--telemetry", action="store_true", help="Display telemetry report")
    parser.add_argument("--status", action="store_true", help="Alias for --telemetry")

    args = parser.parse_args()

    if args.telemetry or args.status or (args.text and args.text.strip().lower() in ["telemetry", "status", "stats"]):
        show_telemetry_summary()
        return

    if not args.text:
        parser.print_help()
        sys.exit(1)

    try:
        synthesize(
            text=args.text,
            char=args.char,
            tts_engine=args.tts,
            to_jid=args.to,
            output_path=args.output,
            pitch_shift=args.pitch
        )
    except Exception as e:
        print(f"[ERROR] Synthesis failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
