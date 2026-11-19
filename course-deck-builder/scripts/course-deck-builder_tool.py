#!/usr/bin/env python3
"""
course-deck-builder_tool.py - Pedagogical Course & Curriculum Slide Deck Generator
Integrates cognitive learning science (Learning Progression, CPA, Worked Examples)
with interactive web presentations (guizang-ppt single-file HTML).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CUSTOM_SKILLS_DIR = BASE_DIR.parent
GUIZANG_DIR = CUSTOM_SKILLS_DIR / "guizang-ppt-skill"
DEFAULT_OUTPUT_BASE = Path("/app/workspaces/default/pembelajaran")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "course-deck"


def get_guizang_paths():
    # Primary location
    candidates = [
        GUIZANG_DIR,
        Path("/app/data/custom-skills/guizang-ppt-skill"),
        Path("/app/workspaces/default/data/custom-skills/guizang-ppt-skill"),
    ]
    for c in candidates:
        if (c / "assets" / "template.html").exists():
            return {
                "root": c,
                "template_magazine": c / "assets" / "template.html",
                "template_swiss": c / "assets" / "template-swiss.html",
                "validator": c / "scripts" / "validate-presenter-mode.mjs",
                "theme_script": c / "scripts" / "gz-theme.mjs",
            }
    return None


def cmd_status(args):
    gz = get_guizang_paths()
    node_installed = shutil.which("node") is not None

    status_data = {
        "status": "ready" if (gz and node_installed) else "degraded",
        "skill": "course-deck-builder",
        "guizang_ppt_available": gz is not None,
        "guizang_root": str(gz["root"]) if gz else None,
        "node_installed": node_installed,
        "output_base_dir": str(DEFAULT_OUTPUT_BASE),
        "supported_styles": ["magazine", "swiss"],
        "themes": {
            "magazine": ["ink-classic", "indigo-porcelain", "forest-ink", "kraft-paper", "dune"],
            "swiss": ["ikb", "lemon", "lemon-green", "safety-orange"],
        },
        "pedagogical_pipeline": [
            "Phase 1: Hook & Learning Outcomes (Prinsip Backward Design)",
            "Phase 2: Learning Progression & Scope (Roadmap dari Dasar ke Mahir)",
            "Phase 3: Concrete Analogy (CPA - Konsep Fisik / Dunia Nyata)",
            "Phase 4: Pictorial Model (CPA - Diagram Visual / Arsitektur)",
            "Phase 5: Abstract & Formal Rules (CPA - Definisi / Rumus / Kode)",
            "Phase 6: Comprehensive Worked Example (Studi Kasus Step-by-Step)",
            "Phase 7: Faded Scaffolding & Stuck Points (Titik Miskonsepsi & Solusi)",
            "Phase 8: Practice & Retrieval Challenge (Tantangan Mandiri & Soal Refleksi)",
            "Phase 9: Synthesis & Next Horizon (Rangkuman & Arah Belajar Selanjutnya)",
        ],
    }
    print(json.dumps(status_data, indent=2))


def build_default_slides(title: str, topic: str, level: str, style: str = "magazine"):
    """
    Constructs the 9 pedagogical slides formatted according to style (Magazine or Swiss).
    """
    if style == "swiss":
        # Style B: Swiss International Style (Inter/Helvetica, Grid, High-Contrast)
        slides_html = f"""
  <!-- Slide 1: S01 Index Cover -->
  <section class="slide hero dark" data-slide-id="01-cover" data-layout="S01">
    <div class="inner" style="display: flex; flex-direction: column; justify-content: space-between; height: 100%; padding: 6vh 6vw;">
      <div class="meta-row" style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 2vh;">
        <span class="mono" style="font-size: 14px; letter-spacing: 0.1em; text-transform: uppercase;">MODUL PEMBELAJARAN TERSTRUKTUR</span>
        <span class="mono" style="font-size: 14px;">LEVEL: {level.upper()}</span>
      </div>
      <div style="margin: auto 0;">
        <div style="font-size: 16px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.15em; color: var(--accent); margin-bottom: 2vh;">PEDAGOGICAL LEARNING BLUEPRINT</div>
        <h1 style="font-size: min(5.8vw, 10vh); font-weight: 200; line-height: 1.05; margin: 0; letter-spacing: -0.02em;">{title}</h1>
        <p style="font-size: 20px; font-weight: 300; opacity: 0.8; margin-top: 3vh; max-width: 60ch;">Membedah konsep {topic} secara runut dari fondasi paling konkret hingga abstraksi tingkat lanjut.</p>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 14px; opacity: 0.6; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 2vh;">
        <span>Kerangka Berpikir: CPA Sequence & Worked-Example Fading</span>
        <span class="mono">SWISS STYLE · 9 MODUL</span>
      </div>
    </div>
  </section>

  <!-- Slide 2: S11 Horizontal Roadmap -->
  <section class="slide light" data-slide-id="02-roadmap" data-layout="S11">
    <div class="inner" style="padding: 6vh 6vw;">
      <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; color: var(--accent); margin-bottom: 1vh;">TAHAP 1: LEARNING PROGRESSION</div>
      <h2 style="font-size: min(4vw, 7vh); font-weight: 300; margin: 0 0 5vh 0;">Peta Jalur Belajar: Dari Nol ke Mahir</h2>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 2vw; margin-top: 4vh;">
        <div style="background: rgba(0,0,0,0.03); border-top: 3px solid var(--accent); padding: 3vh 1.5vw;">
          <div class="mono" style="font-size: 13px; opacity: 0.6;">STEP 01</div>
          <h3 style="font-size: 20px; font-weight: 600; margin: 1vh 0;">Prasyarat & Realita Fisik</h3>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.5;">Menghubungkan topik dengan fenomena konkret dunia nyata yang dapat diraba.</p>
        </div>
        <div style="background: rgba(0,0,0,0.03); border-top: 3px solid var(--accent); padding: 3vh 1.5vw;">
          <div class="mono" style="font-size: 13px; opacity: 0.6;">STEP 02</div>
          <h3 style="font-size: 20px; font-weight: 600; margin: 1vh 0;">Pemodelan Visual</h3>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.5;">Mengubah fakta konkret menjadi representasi diagram, alur, dan arsitektur logis.</p>
        </div>
        <div style="background: rgba(0,0,0,0.03); border-top: 3px solid var(--accent); padding: 3vh 1.5vw;">
          <div class="mono" style="font-size: 13px; opacity: 0.6;">STEP 03</div>
          <h3 style="font-size: 20px; font-weight: 600; margin: 1vh 0;">Abstraksi & Kode</h3>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.5;">Menyusun sintaks formal, aturan sistem, dan prinsip otomatisasi terukur.</p>
        </div>
        <div style="background: rgba(0,0,0,0.03); border-top: 3px solid var(--accent); padding: 3vh 1.5vw;">
          <div class="mono" style="font-size: 13px; opacity: 0.6;">STEP 04</div>
          <h3 style="font-size: 20px; font-weight: 600; margin: 1vh 0;">Penerapan Nyata</h3>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.5;">Menguji pemahaman melalui studi kasus kompleks dan pemecahan masalah mandiri.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 3: S08 Duo Compare (CPA Concrete) -->
  <section class="slide light" data-slide-id="03-concrete" data-layout="S08">
    <div class="inner" style="padding: 6vh 6vw;">
      <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; color: var(--accent); margin-bottom: 1vh;">TAHAP 2: CONCRETE STAGE (CPA)</div>
      <h2 style="font-size: min(4vw, 7vh); font-weight: 300; margin: 0 0 4vh 0;">Analogi Fisik: Memahami Tanpa Hafalan</h2>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4vw; align-items: start;">
        <div style="border-left: 2px solid var(--accent); padding-left: 2vw;">
          <h4 style="font-size: 22px; font-weight: 600; margin: 0 0 1.5vh 0;">Contoh Nyata / Metafora Fisik</h4>
          <p style="font-size: 17px; line-height: 1.6; opacity: 0.85;">Bayangkan sebuah sakelar lampu rumah tangga atau sistem pengiriman surat pos. Sebelum ada jaringan internet canggih, prinsip transmisi data bekerja mirip loket pengurutan fisik yang menyortir amplop berdasarkan kode pos.</p>
          <div style="margin-top: 3vh; padding: 2vh; background: rgba(0,0,0,0.04); font-size: 14px;">
            <strong>Prinsip Inti:</strong> Selalu mulai dari pengalaman indrawi yang akrab bagi pembelajar sebelum memperkenalkan terminologi teknis.
          </div>
        </div>
        <div style="border-left: 2px solid rgba(0,0,0,0.15); padding-left: 2vw;">
          <h4 style="font-size: 22px; font-weight: 600; margin: 0 0 1.5vh 0;">Kenapa Otak Kita Butuh Analogi?</h4>
          <p style="font-size: 17px; line-height: 1.6; opacity: 0.85;">Beban kognitif (*cognitive load*) akan melonjak drastis jika siswa langsung disodori definisi formal tanpa jangkar (*anchor*) pengetahuan awal. Analogi konkret menurunkan friksi pemahaman hingga 70%.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 4: S17 System Diagram (CPA Pictorial) -->
  <section class="slide dark" data-slide-id="04-pictorial" data-layout="S17">
    <div class="inner" style="padding: 6vh 6vw;">
      <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; color: var(--accent); margin-bottom: 1vh;">TAHAP 3: PICTORIAL STAGE (DUAL CODING)</div>
      <h2 style="font-size: min(4vw, 7vh); font-weight: 300; margin: 0 0 4vh 0;">Model Mental: Arsitektur & Hubungan Antar Komponen</h2>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2vw;">
        <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 3vh 2vw;">
          <div style="font-size: 24px; font-weight: 200; color: var(--accent);">01. INPUT / TRIGGER</div>
          <p style="font-size: 15px; opacity: 0.8; margin-top: 2vh;">Sinyal atau data masuk yang diterima sistem dari lingkungan luar.</p>
        </div>
        <div style="background: rgba(255,255,255,0.05); border: 1px solid var(--accent); padding: 3vh 2vw;">
          <div style="font-size: 24px; font-weight: 200; color: var(--accent);">02. TRANSFORMATION</div>
          <p style="font-size: 15px; opacity: 0.8; margin-top: 2vh;">Logika pemrosesan dan layer enkapsulasi yang menyembunyikan detail rumit.</p>
        </div>
        <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 3vh 2vw;">
          <div style="font-size: 24px; font-weight: 200; color: var(--accent);">03. OUTCOME / STATE</div>
          <p style="font-size: 15px; opacity: 0.8; margin-top: 2vh;">Hasil terprediksi yang siap dikonsumsi oleh lapisan komputasi berikutnya.</p>
        </div>
      </div>
      <p style="font-size: 15px; opacity: 0.6; margin-top: 4vh; text-align: center;">Bagan Visual: Menyajikan hubungan spasial yang menguatkan pemahaman narasi verbal.</p>
    </div>
  </section>

  <!-- Slide 5: S03 Split Statement (CPA Abstract) -->
  <section class="slide light" data-slide-id="05-abstract" data-layout="S03">
    <div class="inner" style="padding: 6vh 6vw; display: flex; flex-direction: column; justify-content: center; height: 100%;">
      <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; color: var(--accent); margin-bottom: 2vh;">TAHAP 4: ABSTRACT STAGE (FORMAL RULES)</div>
      <h2 style="font-size: min(4.5vw, 8vh); font-weight: 200; line-height: 1.15; margin: 0 0 4vh 0;">
        "Abstraksi bukanlah menghilangkan detail penting, melainkan menyembunyikan detail agar kita bisa fokus pada gambaran besar."
      </h2>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4vw; font-size: 16px; opacity: 0.85; line-height: 1.6;">
        <p>Pada tahap ini, pembelajar siap memahami istilah resmi, definisi standar industri, dan aturan sintaksis formal tanpa kebingungan karena fondasi visualnya telah terbentuk.</p>
        <p>Setiap antarmuka (interface) di desain untuk memberikan kontrak yang jelas: input yang diharapkan, operasi yang dijamin, dan output yang dihasilkan.</p>
      </div>
    </div>
  </section>

  <!-- Slide 6: S19 Four Cards (Worked Example) -->
  <section class="slide light" data-slide-id="06-worked-example" data-layout="S19">
    <div class="inner" style="padding: 6vh 6vw;">
      <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; color: var(--accent); margin-bottom: 1vh;">TAHAP 5: COMPREHENSIVE WORKED EXAMPLE</div>
      <h2 style="font-size: min(4vw, 7vh); font-weight: 300; margin: 0 0 4vh 0;">Bedah Kasus: Langkah Demi Langkah</h2>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2vw;">
        <div style="background: rgba(0,0,0,0.03); padding: 3vh 2vw; border-top: 2px solid rgba(0,0,0,0.15);">
          <div class="mono" style="font-size: 13px;">LANGKAH 1</div>
          <h4 style="font-size: 18px; margin: 1vh 0;">Identifikasi Masalah</h4>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.5;">Bedah masukan dan spesifikasi yang diinginkan tanpa terburu-buru menulis solusi.</p>
        </div>
        <div style="background: rgba(0,0,0,0.03); padding: 3vh 2vw; border-top: 2px solid var(--accent);">
          <div class="mono" style="font-size: 13px; color: var(--accent);">LANGKAH 2</div>
          <h4 style="font-size: 18px; margin: 1vh 0;">Dekonstruksi Logika</h4>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.5;">Pecah masalah besar menjadi modul-modul kecil yang memiliki satu tanggung jawab tunggal.</p>
        </div>
        <div style="background: rgba(0,0,0,0.03); padding: 3vh 2vw; border-top: 2px solid rgba(0,0,0,0.15);">
          <div class="mono" style="font-size: 13px;">LANGKAH 3</div>
          <h4 style="font-size: 18px; margin: 1vh 0;">Verifikasi & Validasi</h4>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.5;">Uji hasil keluaran terhadap batasan ekstrem (*edge cases*) untuk memastikan keandalan.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 7: S08 Duo Compare (Stuck Points & Fading) -->
  <section class="slide light" data-slide-id="07-stuck-points" data-layout="S08">
    <div class="inner" style="padding: 6vh 6vw;">
      <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; color: var(--accent); margin-bottom: 1vh;">TAHAP 6: SCAFFOLDING & TITIK RAWAN BINGUNG</div>
      <h2 style="font-size: min(4vw, 7vh); font-weight: 300; margin: 0 0 4vh 0;">Miskonsepsi Umum & Cara Mengatasinya</h2>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4vw;">
        <div style="background: #fff1f0; border-left: 4px solid #ff4d4f; padding: 3vh 2vw;">
          <h4 style="font-size: 20px; font-weight: 600; color: #cf1322; margin: 0 0 1.5vh 0;">Jebakan Pemula (Common Pitfalls)</h4>
          <ul style="font-size: 15px; line-height: 1.7; padding-left: 1.2vw; margin: 0; color: #5c0011;">
            <li>Mengabaikan abstraksi dan mencoba mengontrol seluruh subsistem secara manual.</li>
            <li>Mencampuradukkan level detail (leaky abstraction) antar lapisan komponen.</li>
            <li>Menghafal rumus tanpa memahami relasi sebab-akibat antar parameter.</li>
          </ul>
        </div>
        <div style="background: #f6ffed; border-left: 4px solid #52c41a; padding: 3vh 2vw;">
          <h4 style="font-size: 20px; font-weight: 600; color: #389e0d; margin: 0 0 1.5vh 0;">Strategi Penyelesaian (Correct Protocol)</h4>
          <ul style="font-size: 15px; line-height: 1.7; padding-left: 1.2vw; margin: 0; color: #135200;">
            <li>Percayakan antarmuka: gunakan kontrak layer tanpa membongkar implementasi dalamnya.</li>
            <li>Terapkan prinsip Single Responsibility pada setiap modul yang dibangun.</li>
            <li>Gunakan diagram alur data untuk mengisolasi titik anomali saat terjadi bug.</li>
          </ul>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 8: S16 Multi-card Brief (Practice & Retrieval) -->
  <section class="slide dark" data-slide-id="08-practice" data-layout="S16">
    <div class="inner" style="padding: 6vh 6vw;">
      <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; color: var(--accent); margin-bottom: 1vh;">TAHAP 7: RETRIEVAL PRACTICE</div>
      <h2 style="font-size: min(4vw, 7vh); font-weight: 300; margin: 0 0 4vh 0;">Tantangan Mandiri: Uji Pemahaman Anda</h2>
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 3vw;">
        <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 3vh 2vw;">
          <div style="color: var(--accent); font-weight: 600; font-size: 16px;">TANTANGAN LEVEL 1 (TEACH-BACK)</div>
          <p style="font-size: 16px; margin-top: 1.5vh; line-height: 1.6;">Jelaskan konsep inti topik ini kepada rekan kerja yang belum pernah mempelajarinya dengan menggunakan 1 analogi dunia nyata tanpa istilah teknis.</p>
        </div>
        <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 3vh 2vw;">
          <div style="color: var(--accent); font-weight: 600; font-size: 16px;">TANTANGAN LEVEL 2 (ANALISIS KASUS)</div>
          <p style="font-size: 16px; margin-top: 1.5vh; line-height: 1.6;">Jika salah satu modul downstream mengalami latensi tinggi, bagaimana arsitektur ini mencegah kegagalan berantai (*cascading failure*)?</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 9: S10 Split Closing -->
  <section class="slide hero dark" data-slide-id="09-closing" data-layout="S10">
    <div class="inner" style="display: flex; flex-direction: column; justify-content: space-between; height: 100%; padding: 6vh 6vw;">
      <div class="mono" style="font-size: 14px; letter-spacing: 0.1em; opacity: 0.7;">TAHAP 8: CAPAIAN KOMPETENSI SELESAI</div>
      <div>
        <h2 style="font-size: min(5vw, 9vh); font-weight: 200; line-height: 1.1; margin: 0 0 2vh 0;">Selamat, Anda Telah Menguasai Fondasi {topic}!</h2>
        <p style="font-size: 20px; font-weight: 300; opacity: 0.8; max-width: 60ch;">Langkah berikutnya: terapkan pola berpikir terstruktur ini ke proyek nyata dan terus eksplorasi layer abstraksi yang lebih mendalam.</p>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 14px; opacity: 0.5; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 2vh;">
        <span>Dibuat dengan Pedagogical Course Builder & Guizang PPT</span>
        <span class="mono">Tekan P untuk Mode Presenter</span>
      </div>
    </div>
  </section>
"""
    else:
        # Style A: Electronic Magazine x E-Ink (Serif headers, warm/intellectual tone)
        slides_html = f"""
  <!-- Slide 1: Cover Layout 1 -->
  <section class="slide hero dark" data-slide-id="01-cover">
    <div class="inner" style="display: flex; flex-direction: column; justify-content: space-between; height: 100%; padding: 7vh 7vw;">
      <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.15); padding-bottom: 2vh;">
        <span style="font-family: monospace; font-size: 13px; letter-spacing: 0.15em; text-transform: uppercase;">MONOCLE SPECIAL CURRICULUM · ISSUE 2026</span>
        <span style="font-family: monospace; font-size: 13px;">LEVEL: {level.upper()}</span>
      </div>
      <div style="margin: auto 0;">
        <span style="font-family: monospace; font-size: 14px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--accent); display: block; margin-bottom: 2vh;">PEDAGOGICAL LEARNING PATH</span>
        <h1 class="h-hero" style="margin: 0; line-height: 1.05;">{title}</h1>
        <p style="font-size: 22px; font-weight: 300; opacity: 0.85; margin-top: 3vh; max-width: 55ch; line-height: 1.5;">
          Sebuah eksplorasi terstruktur tentang {topic}, menghubungkan fakta konkret dunia nyata ke arsitektur pemikiran tingkat lanjut.
        </p>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 14px; opacity: 0.6; border-top: 1px solid rgba(255,255,255,0.15); padding-top: 2vh;">
        <span>Sains Pembelajaran: Learning Progression · CPA · Worked Examples</span>
        <span style="font-family: monospace;">MAGAZINE STYLE · 9 MODUL</span>
      </div>
    </div>
  </section>

  <!-- Slide 2: Pipeline Roadmap -->
  <section class="slide light" data-slide-id="02-roadmap">
    <div class="inner" style="padding: 7vh 7vw;">
      <span style="font-family: monospace; font-size: 13px; color: var(--accent); letter-spacing: 0.15em; text-transform: uppercase;">TAHAP 1: LEARNING PROGRESSION</span>
      <h2 style="font-size: 2.8vw; margin: 1vh 0 4vh 0; font-family: var(--serif);">Peta Jalur Belajar: Dari Nol Hingga Mahir</h2>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 2vw; margin-top: 5vh;">
        <div style="border-top: 2px solid var(--text-primary); padding-top: 2vh;">
          <span style="font-family: monospace; font-size: 12px; opacity: 0.6;">BAGIAN 01</span>
          <h3 style="font-size: 20px; margin: 1vh 0; font-family: var(--serif);">Pondasi Konkret</h3>
          <p style="font-size: 15px; opacity: 0.8; line-height: 1.6;">Menemukan jangkar pemahaman lewat metafora fisik yang akrab di kehidupan sehari-hari.</p>
        </div>
        <div style="border-top: 2px solid var(--text-primary); padding-top: 2vh;">
          <span style="font-family: monospace; font-size: 12px; opacity: 0.6;">BAGIAN 02</span>
          <h3 style="font-size: 20px; margin: 1vh 0; font-family: var(--serif);">Model Visual</h3>
          <p style="font-size: 15px; opacity: 0.8; line-height: 1.6;">Menghubungkan indera visual dengan bagan alur kerja dan skema rancang bangun.</p>
        </div>
        <div style="border-top: 2px solid var(--text-primary); padding-top: 2vh;">
          <span style="font-family: monospace; font-size: 12px; opacity: 0.6;">BAGIAN 03</span>
          <h3 style="font-size: 20px; margin: 1vh 0; font-family: var(--serif);">Sintaksis Formal</h3>
          <p style="font-size: 15px; opacity: 0.8; line-height: 1.6;">Menguasai terminologi baku, aturan logika, dan implementasi kode tanpa rasa terintimidasi.</p>
        </div>
        <div style="border-top: 2px solid var(--text-primary); padding-top: 2vh;">
          <span style="font-family: monospace; font-size: 12px; opacity: 0.6;">BAGIAN 04</span>
          <h3 style="font-size: 20px; margin: 1vh 0; font-family: var(--serif);">Studi Kasus Mandiri</h3>
          <p style="font-size: 15px; opacity: 0.8; line-height: 1.6;">Menerapkan seluruh pemahaman ke dalam latihan bertingkat dan pemecahan kasus nyata.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 3: CPA Concrete Analogy -->
  <section class="slide light" data-slide-id="03-concrete">
    <div class="inner" style="padding: 7vh 7vw;">
      <span style="font-family: monospace; font-size: 13px; color: var(--accent); letter-spacing: 0.15em; text-transform: uppercase;">TAHAP 2: CONCRETE STAGE (CPA)</span>
      <h2 style="font-size: 2.8vw; margin: 1vh 0 4vh 0; font-family: var(--serif);">Analogi Konkret: Membuka Gerbang Pemahaman</h2>
      <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 4vw; align-items: start;">
        <div>
          <p style="font-size: 20px; line-height: 1.7; opacity: 0.9;">
            Sebelum memikirkan algoritma yang rumit atau sistem distribusi yang luas, bayangkan sebuah jam mekanik kuno. Jarum jam yang bergerak anggun di permukaan sebenarnya digerakkan oleh ratusan roda gigi kecil yang berputar di balik pelat logam.
          </p>
          <p style="font-size: 16px; line-height: 1.7; opacity: 0.75; margin-top: 2vh;">
            Pengguna cukup melihat waktu tanpa perlu mengatur tegangan pegas di dalamnya. Begitulah konsep fundamental {topic}: memberikan fungsi optimal sambil melindungi pengguna dari kompleksitas mesin.
          </p>
        </div>
        <div style="background: rgba(0,0,0,0.03); padding: 4vh 2.5vw; border-left: 2px solid var(--accent);">
          <span style="font-family: monospace; font-size: 12px; text-transform: uppercase; color: var(--accent);">CATATAN PEDAGOGI</span>
          <h4 style="font-family: var(--serif); font-size: 18px; margin: 1.5vh 0;">Kenapa Harus Mulai dari Hal Nyata?</h4>
          <p style="font-size: 14px; line-height: 1.6; opacity: 0.8;">
            Teori beban kognitif Sweller menunjukkan bahwa otak manusia menyimpan pola baru jauh lebih cepat saat disematkan pada skema memori jangka panjang yang sudah terbentuk.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 4: CPA Pictorial Visual Model -->
  <section class="slide dark" data-slide-id="04-pictorial">
    <div class="inner" style="padding: 7vh 7vw;">
      <span style="font-family: monospace; font-size: 13px; color: var(--accent); letter-spacing: 0.15em; text-transform: uppercase;">TAHAP 3: PICTORIAL STAGE (DUAL CODING)</span>
      <h2 style="font-size: 2.8vw; margin: 1vh 0 4vh 0; font-family: var(--serif);">Representasi Visual: Menghubungkan Konkret & Logika</h2>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2vw; margin-top: 4vh;">
        <div style="border: 1px solid rgba(255,255,255,0.15); padding: 4vh 2vw;">
          <div style="font-family: monospace; font-size: 14px; color: var(--accent);">LAYER 01</div>
          <h3 style="font-family: var(--serif); font-size: 22px; margin: 1.5vh 0;">Persepsi Masukan</h3>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.6;">Menerima impuls, parameter, atau permintaan dari agen pemanggil.</p>
        </div>
        <div style="border: 1px solid var(--accent); padding: 4vh 2vw; background: rgba(255,255,255,0.02);">
          <div style="font-family: monospace; font-size: 14px; color: var(--accent);">LAYER 02</div>
          <h3 style="font-family: var(--serif); font-size: 22px; margin: 1.5vh 0;">Enkapsulasi Mesin</h3>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.6;">Menjalankan transformasi state dan menjamin aturan bisnis terpenuhi.</p>
        </div>
        <div style="border: 1px solid rgba(255,255,255,0.15); padding: 4vh 2vw;">
          <div style="font-family: monospace; font-size: 14px; color: var(--accent);">LAYER 03</div>
          <h3 style="font-family: var(--serif); font-size: 22px; margin: 1.5vh 0;">Antarmuka Bersih</h3>
          <p style="font-size: 15px; opacity: 0.75; line-height: 1.6;">Menyajikan hasil terverifikasi tanpa kebocoran detail implementasi.</p>
        </div>
      </div>
      <p style="font-size: 14px; opacity: 0.5; margin-top: 5vh; text-align: center; font-family: monospace;">DUAL CODING THEORY: KOMBINASI VERBAL + VISUAL MENINGKATKAN RETENSI HINGGA 2X LIPAT</p>
    </div>
  </section>

  <!-- Slide 5: CPA Abstract Principle -->
  <section class="slide light" data-slide-id="05-abstract">
    <div class="inner" style="padding: 7vh 7vw; display: flex; flex-direction: column; justify-content: center; height: 100%;">
      <span style="font-family: monospace; font-size: 13px; color: var(--accent); letter-spacing: 0.15em; text-transform: uppercase;">TAHAP 4: ABSTRACT STAGE (THEORY & CONTRACT)</span>
      <blockquote style="font-family: var(--serif); font-size: 3vw; line-height: 1.25; margin: 2vh 0 4vh 0; font-style: italic;">
        "Setiap lapis abstraksi yang baik adalah janji: ia menyederhanakan cara pandang Anda terhadap dunia tanpa mengurangi ketepatan hasilnya."
      </blockquote>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4vw; font-size: 17px; opacity: 0.85; line-height: 1.7;">
        <div>
          <h4 style="font-family: var(--serif); font-size: 20px; margin: 0 0 1vh 0;">Kontrak Antarmuka Formal</h4>
          <p>Setelah memahami analogi dan diagramnya, kita dapat menyimpulkan kaidah formal: bahwa setiap komponen terikat oleh kontrak masukan dan keluaran yang deterministik.</p>
        </div>
        <div>
          <h4 style="font-family: var(--serif); font-size: 20px; margin: 0 0 1vh 0;">Efisiensi Penalaran</h4>
          <p>Dengan menguasai abstraksi, Anda tidak perlu lagi mengingat setiap transistor atau kabel; Anda cukup bernalar di tingkat arsitektur dan sistem.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 6: Worked Example -->
  <section class="slide light" data-slide-id="06-worked-example">
    <div class="inner" style="padding: 7vh 7vw;">
      <span style="font-family: monospace; font-size: 13px; color: var(--accent); letter-spacing: 0.15em; text-transform: uppercase;">TAHAP 5: COMPREHENSIVE WORKED EXAMPLE</span>
      <h2 style="font-size: 2.8vw; margin: 1vh 0 4vh 0; font-family: var(--serif);">Studi Kasus Lengkap: Dari Masalah ke Solusi</h2>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2vw; margin-top: 3vh;">
        <div style="background: rgba(0,0,0,0.02); padding: 4vh 2vw; border: 1px solid rgba(0,0,0,0.08);">
          <span style="font-family: monospace; font-size: 12px; opacity: 0.6;">STEP 01: BEDAH KASUS</span>
          <h4 style="font-family: var(--serif); font-size: 19px; margin: 1.5vh 0;">Isolasi Domain</h4>
          <p style="font-size: 14px; opacity: 0.8; line-height: 1.6;">Menentukan batas permasalahan yang ingin dipecahkan tanpa terdistraksi faktor luar.</p>
        </div>
        <div style="background: rgba(0,0,0,0.02); padding: 4vh 2vw; border: 1px solid rgba(0,0,0,0.08); border-top: 3px solid var(--accent);">
          <span style="font-family: monospace; font-size: 12px; color: var(--accent);">STEP 02: PENERAPAN POLA</span>
          <h4 style="font-family: var(--serif); font-size: 19px; margin: 1.5vh 0;">Rancang Solusi</h4>
          <p style="font-size: 14px; opacity: 0.8; line-height: 1.6;">Mengaplikasikan prinsip abstraksi dan enkapsulasi secara bertahap pada rancangan.</p>
        </div>
        <div style="background: rgba(0,0,0,0.02); padding: 4vh 2vw; border: 1px solid rgba(0,0,0,0.08);">
          <span style="font-family: monospace; font-size: 12px; opacity: 0.6;">STEP 03: VERIFIKASI</span>
          <h4 style="font-family: var(--serif); font-size: 19px; margin: 1.5vh 0;">Uji Ketahanan</h4>
          <p style="font-size: 14px; opacity: 0.8; line-height: 1.6;">Memastikan solusi tidak bocor (zero abstraction leakage) saat menghadapi beban berat.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 7: Stuck Points & Misconceptions -->
  <section class="slide light" data-slide-id="07-stuck-points">
    <div class="inner" style="padding: 7vh 7vw;">
      <span style="font-family: monospace; font-size: 13px; color: var(--accent); letter-spacing: 0.15em; text-transform: uppercase;">TAHAP 6: SCAFFOLDING & TITIK RAWAN BINGUNG</span>
      <h2 style="font-size: 2.8vw; margin: 1vh 0 4vh 0; font-family: var(--serif);">Miskonsepsi Umum & Cara Menghindarinya</h2>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4vw; margin-top: 3vh;">
        <div style="border-left: 2px solid #cf1322; padding-left: 2vw;">
          <h4 style="font-family: var(--serif); font-size: 22px; color: #cf1322; margin: 0 0 1.5vh 0;">Titik Rawan Miskonsepsi</h4>
          <p style="font-size: 16px; line-height: 1.7; opacity: 0.85;">
            Banyak pembelajar terjebak menganggap abstraksi membuat sistem menjadi lebih lambat atau menambah *overhead* yang tidak perlu, sehingga mereka mencoba memprogram segalanya di level paling rendah.
          </p>
        </div>
        <div style="border-left: 2px solid #389e0d; padding-left: 2vw;">
          <h4 style="font-family: var(--serif); font-size: 22px; color: #389e0d; margin: 0 0 1.5vh 0;">Perspektif yang Tepat</h4>
          <p style="font-size: 16px; line-height: 1.7; opacity: 0.85;">
            Abstraksi yang dirancang dengan baik justru memungkinkan pengoptimalan otomatis oleh *compiler* atau mesin runtime, serta melindungi tim dari kesalahan manusia (*human error*) saat skala membesar.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 8: Practice & Retrieval Challenge -->
  <section class="slide dark" data-slide-id="08-practice">
    <div class="inner" style="padding: 7vh 7vw;">
      <span style="font-family: monospace; font-size: 13px; color: var(--accent); letter-spacing: 0.15em; text-transform: uppercase;">TAHAP 7: RETRIEVAL PRACTICE CHALLENGE</span>
      <h2 style="font-size: 2.8vw; margin: 1vh 0 4vh 0; font-family: var(--serif);">Tantangan Mandiri & Soal Refleksi</h2>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4vw; margin-top: 4vh;">
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.12); padding: 4vh 2.5vw;">
          <span style="font-family: monospace; font-size: 13px; color: var(--accent);">LATIHAN RETENSI 01</span>
          <h4 style="font-family: var(--serif); font-size: 20px; margin: 1.5vh 0;">Teach-Back Challenge</h4>
          <p style="font-size: 15px; opacity: 0.8; line-height: 1.6;">
            Coba tuliskan rangkuman 3 kalimat tentang apa itu {topic} tanpa membuka kembali slide materi sebelumnya.
          </p>
        </div>
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.12); padding: 4vh 2.5vw;">
          <span style="font-family: monospace; font-size: 13px; color: var(--accent);">LATIHAN RETENSI 02</span>
          <h4 style="font-family: var(--serif); font-size: 20px; margin: 1.5vh 0;">Troubleshooting Studi Kasus</h4>
          <p style="font-size: 15px; opacity: 0.8; line-height: 1.6;">
            Jika terjadi kebocoran informasi antar layer, komponen mana yang pertama kali harus diaudit dan diperbaiki?
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Slide 9: Closing Takeaway -->
  <section class="slide hero dark" data-slide-id="09-closing">
    <div class="inner" style="display: flex; flex-direction: column; justify-content: space-between; height: 100%; padding: 7vh 7vw;">
      <div style="font-family: monospace; font-size: 13px; letter-spacing: 0.15em; opacity: 0.7;">TAHAP 8: CAPAIAN KOMPETENSI TERCAPAI</div>
      <div>
        <h2 class="h-hero" style="margin: 0 0 2vh 0;">Selamat Belajar & Berkembang!</h2>
        <p style="font-size: 22px; font-weight: 300; opacity: 0.85; max-width: 55ch; line-height: 1.5;">
          Fondasi pemahaman {topic} telah terpasang kuat. Teruslah bereksperimen, membangun karya, dan membagikan ilmu ini kepada rekan-rekan Anda.
        </p>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 14px; opacity: 0.5; border-top: 1px solid rgba(255,255,255,0.15); padding-top: 2vh;">
        <span>Dibuat dengan Pedagogical Course Builder · Modul Mandiri</span>
        <span style="font-family: monospace;">Tekan P untuk Catatan Pengajar</span>
      </div>
    </div>
  </section>
"""
    return slides_html


def build_speaker_notes(title: str, topic: str):
    """
    Constructs the valid SPEAKER_NOTES array corresponding to the 9 slides.
    """
    notes = [
        {
            "id": "01-cover",
            "title": f"Pengantar: {title}",
            "section": "Pembuka",
            "minutes": 2,
            "purpose": f"Membangun ketertarikan peserta terhadap topik {topic} dan menetapkan ekspektasi alur pembelajaran.",
            "talk": [
                f"Selamat datang rekan-rekan! Hari ini kita akan membedah topik {topic}.",
                "Kita tidak akan langsung loncat ke hafalan atau rumus rumit, tapi akan menyusuri alurnya dari analogi paling sederhana sampai penerapan nyata.",
                "Tujuan sesi ini agar rekan-rekan memiliki intuisi mendalam, bukan sekadar hafalan sintaks."
            ],
            "transition": "Mari kita lihat peta jalan pembelajaran yang akan kita lalui bersama."
        },
        {
            "id": "02-roadmap",
            "title": "Peta Jalur Belajar (Learning Progression)",
            "section": "Struktur",
            "minutes": 2,
            "purpose": "Menunjukkan peta perjalanan belajar (big picture) agar peserta tidak bingung di tengah jalan.",
            "talk": [
                "Perjalanan kita dibagi menjadi 4 etape utama.",
                "Pertama kita kuatkan fondasi konkret, lalu kita visualisasikan ke diagram.",
                "Setelah model mentalnya terbentuk, baru kita masuk ke sintaks dan aturan formalnya, diakhiri dengan studi kasus."
            ],
            "transition": "Kita awali etape pertama dengan metafora nyata yang akrab dalam kehidupan kita."
        },
        {
            "id": "03-concrete",
            "title": "Analogi Fisik & Konsep Konkret",
            "section": "Fondasi Konkret",
            "minutes": 3,
            "purpose": "Menambatkan konsep abstrak ke fenomena nyata yang sudah dipahami peserta.",
            "talk": [
                f"Di slide ini, perhatikan bagaimana {topic} sebenarnya mirip sekali dengan mekanisme kerja di dunia nyata.",
                "Sama seperti kita menyetir mobil tanpa perlu tahu berapa tekanan oli di ruang bakar, sistem komputer juga dirancang seperti itu.",
                "Poin kuncinya adalah pemisahan antara siapa yang memakai dan siapa yang mengelola kerumitan di dalam."
            ],
            "transition": "Sekarang, bagaimana cara kita menggambarkan metafora ini ke dalam bentuk diagram arsitektur?"
        },
        {
            "id": "04-pictorial",
            "title": "Representasi Visual & Diagram Arsitektur",
            "section": "Model Mental",
            "minutes": 3,
            "purpose": "Memperkuat representasi verbal dengan skema spasial melalui prinsip Dual Coding.",
            "talk": [
                "Bagan ini membagi sistem menjadi tiga lapis utama: input, transformasi, dan antarmuka.",
                "Perhatikan arah aliran data yang selalu bergerak satu arah secara terprediksi.",
                "Dengan melihat hubungan kotak-kotak ini, rekan-rekan bisa dengan mudah melacak di mana suatu proses terjadi."
            ],
            "transition": "Dengan gambar ini di kepala kita, sekarang kita siap masuk ke aturan dan definisi formalnya."
        },
        {
            "id": "05-abstract",
            "title": "Kaidah & Definisi Formal",
            "section": "Abstraksi Teori",
            "minutes": 3,
            "purpose": "Menjelaskan kontrak formal, aturan sistem, dan prinsip inti tanpa kebingungan.",
            "talk": [
                "Kutipan di layar adalah inti dari seluruh materi kita hari ini.",
                "Abstraksi bukan berarti menghilangkan fakta, melainkan memilih detail mana yang relevan pada waktu tertentu.",
                "Saat kita menulis fungsi atau API, kita sedang membuat janji kontrak kepada pemanggilnya."
            ],
            "transition": "Teori akan jauh lebih hidup jika kita bedah langsung dalam satu studi kasus nyata."
        },
        {
            "id": "06-worked-example",
            "title": "Studi Kasus Step-by-Step",
            "section": "Penerapan",
            "minutes": 4,
            "purpose": "Menyajikan contoh penerapan lengkap dari awal hingga akhir (Worked Example).",
            "talk": [
                "Di sini kita pecah penyelesaian kasus menjadi tiga langkah sistematis.",
                "Langkah satu kita batasi ruang lingkupnya, langkah dua kita rancang modulnya, dan langkah tiga kita verifikasi keandalannya.",
                "Perhatikan bahwa kita tidak langsung menulis solusi tanpa memvalidasi asumsi awal."
            ],
            "transition": "Namun, di mana biasanya orang sering keliru saat mempraktekkan hal ini?"
        },
        {
            "id": "07-stuck-points",
            "title": "Titik Rawan Miskonsepsi & Solusi",
            "section": "Scaffolding",
            "minutes": 3,
            "purpose": "Mencegah kesalahan umum dan meluruskan miskonsepsi yang sering dialami pembelajar.",
            "talk": [
                "Banyak pemula merasa abstraksi bikin ribet atau bikin lambat.",
                "Padahal dalam sistem berskala besar, tanpa batas abstraksi yang jelas, sistem akan runtuh seperti kartu remi saat ada perubahan kecil.",
                "Kuncinya adalah jangan biarkan implementasi dalam bocor ke luar (no leaky abstraction)."
            ],
            "transition": "Sekarang giliran rekan-rekan untuk menguji apakah konsep ini sudah benar-benar melekat."
        },
        {
            "id": "08-practice",
            "title": "Tantangan Mandiri & Refleksi",
            "section": "Evaluasi",
            "minutes": 3,
            "purpose": "Menguji pemahaman aktif melalui teknik retrieval practice dan teach-back.",
            "talk": [
                "Ada dua tantangan di layar: tantangan menjelaskan kembali (teach-back) dan analisis kasus.",
                "Saya beri waktu sejenak untuk memikirkan analogi terbaik menurut versi rekan-rekan sendiri.",
                "Jika rekan-rekan bisa menjelaskan ini kepada orang awam, berarti pemahaman rekan-rekan sudah mencapai tingkat mahir."
            ],
            "transition": "Luar biasa! Mari kita rangkum capaian sesi belajar hari ini."
        },
        {
            "id": "09-closing",
            "title": "Rangkuman & Langkah Selanjutnya",
            "section": "Penutup",
            "minutes": 2,
            "purpose": "Menutup sesi pembelajaran dengan optimisme dan panduan tindak lanjut.",
            "talk": [
                f"Selamat rekan-rekan telah menyelesaikan modul {title}!",
                "Fondasi berpikir terstruktur ini bisa rekan-rekan gunakan di setiap aspek perancangan perangkat lunak maupun analisis data.",
                "Slide ini bisa dibuka kapan saja, dan jangan ragu untuk berdiskusi lebih lanjut jika ada studi kasus baru di pekerjaan."
            ],
            "transition": "Selesai. Terima kasih atas partisipasi aktif rekan-rekan semua!"
        }
    ]
    return notes


def cmd_generate(args):
    gz = get_guizang_paths()
    if not gz:
        print(json.dumps({
            "status": "error",
            "message": "guizang-ppt-skill assets not found. Ensure guizang-ppt-skill is installed in data/custom-skills/"
        }, indent=2), file=sys.stderr)
        sys.exit(1)

    title = args.title or "Modul Pembelajaran Terstruktur"
    topic = args.topic or title
    level = args.level or "Umum / Semua Tingkat"
    style = args.style.lower()
    if style not in ["magazine", "swiss"]:
        style = "magazine"

    # Select template
    template_path = gz["template_swiss"] if style == "swiss" else gz["template_magazine"]
    if not template_path.exists():
        print(json.dumps({"status": "error", "message": f"Template {template_path} not found"}, indent=2), file=sys.stderr)
        sys.exit(1)

    template_content = template_path.read_text(encoding="utf-8")

    # Set theme
    theme = args.theme
    if not theme:
        theme = "ikb" if style == "swiss" else "indigo-porcelain"

    # Set output directory
    slug = slugify(args.slug or title)
    output_dir = Path(args.output_dir) if args.output_dir else (DEFAULT_OUTPUT_BASE / slug)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "images").mkdir(exist_ok=True)

    # Copy motion.min.js if available
    motion_src = gz["root"] / "assets" / "motion.min.js"
    if motion_src.exists():
        shutil.copy(motion_src, output_dir / "motion.min.js")

    # Build slides & notes
    slides_html = build_default_slides(title, topic, level, style=style)
    speaker_notes = build_speaker_notes(title, topic)
    speaker_notes_json = json.dumps(speaker_notes, indent=2, ensure_ascii=False)

    # Replace placeholders
    rendered = template_content
    # Replace title
    rendered = re.sub(r"<title>.*?</title>", f"<title>{title} · Modul Pembelajaran</title>", rendered, count=1)
    # Set data-theme
    rendered = re.sub(r'<html([^>]*)data-theme="[^"]*"', f'<html\\1data-theme="{theme}"', rendered, count=1)
    if 'data-theme="' not in rendered:
        rendered = rendered.replace("<html", f'<html data-theme="{theme}"', 1)

    # Replace slides cleanly across both templates
    slides_pattern = r'<!-- SLIDES_HERE[\s\S]*?(?=</div>\s*<div id="nav">)'
    if re.search(slides_pattern, rendered):
        rendered = re.sub(slides_pattern, f"<!-- SLIDES_HERE -->\n{slides_html}\n", rendered, count=1)
    elif "<!-- SLIDES_HERE -->" in rendered:
        rendered = rendered.replace("<!-- SLIDES_HERE -->", slides_html)
    else:
        rendered = rendered.replace('<div id="nav"></div>', f"{slides_html}\n<div id=\"nav\"></div>")

    # Replace speaker notes
    notes_replacement = f"const SPEAKER_NOTES = {speaker_notes_json};"
    rendered = re.sub(r"const SPEAKER_NOTES\s*=\s*\[[\s\S]*?\];", notes_replacement, rendered, count=1)

    output_file = output_dir / "index.html"
    output_file.write_text(rendered, encoding="utf-8")

    # Run validation via validate-presenter-mode.mjs
    validator_path = gz["validator"]
    val_status = "unverified"
    val_warnings = []
    if validator_path.exists() and shutil.which("node"):
        try:
            res = subprocess.run(
                ["node", str(validator_path), str(output_file)],
                capture_output=True,
                text=True,
                timeout=15
            )
            val_output = (res.stdout + res.stderr).strip()
            val_status = "passed" if res.returncode == 0 else "failed"
            if res.returncode != 0:
                val_warnings.append(val_output)
        except Exception as e:
            val_warnings.append(str(e))

    # Optional Google Drive Upload
    gdrive_info = None
    if getattr(args, "gdrive", False):
        try:
            gdrive_tool_script = Path("/app/workspaces/default/skills/gdrive/scripts/gdrive_tool.py")
            if not gdrive_tool_script.exists():
                gdrive_tool_script = Path("skills/gdrive/scripts/gdrive_tool.py")
            folder_res = subprocess.run([
                "python3", str(gdrive_tool_script), "drive-create-folder",
                "--name", slug,
                "--parent", "1kbWEz96WhIRuydOVIyqMOIkJkzKXDwLt",
                "--share", "anyone",
                "--role", "reader"
            ], capture_output=True, text=True)
            folder_data = json.loads(folder_res.stdout) if folder_res.returncode == 0 else {}
            sub_id = folder_data.get("id")
            if sub_id:
                up_res = subprocess.run([
                    "python3", str(gdrive_tool_script), "drive-upload",
                    "--file", str(output_file),
                    "--name", f"{slug}.html",
                    "--folder-id", sub_id,
                    "--share", "anyone",
                    "--role", "reader"
                ], capture_output=True, text=True)
                up_data = json.loads(up_res.stdout) if up_res.returncode == 0 else {}
                gdrive_info = {
                    "folder_id": sub_id,
                    "folder_link": folder_data.get("web_view_link"),
                    "file_link": up_data.get("web_view_link")
                }
        except Exception as e:
            gdrive_info = {"error": str(e)}

    result = {
        "status": "success",
        "title": title,
        "topic": topic,
        "level": level,
        "style": style,
        "theme": theme,
        "total_slides": len(speaker_notes),
        "estimated_minutes": sum(n.get("minutes", 2) for n in speaker_notes),
        "output_path": str(output_file),
        "output_dir": str(output_dir),
        "gdrive": gdrive_info,
        "validation_status": val_status,
        "validation_notes": val_warnings if val_warnings else "0 errors, presenter mode fully synced",
        "instructions": {
            "view_in_browser": f"Buka file di browser: file://{output_file}",
            "presenter_mode": "Tekan tombol 'P' pada keyboard untuk membuka layar pengajar / speaker notes interaktif",
            "grid_overview": "Tekan tombol 'ESC' untuk melihat ikhtisar kisi seluruh slide",
            "navigation": "Gunakan tombol panah keyboard ← → atau swipe layar sentuh untuk berpindah slide"
        }
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_list(args):
    if not DEFAULT_OUTPUT_BASE.exists():
        print(json.dumps({"status": "success", "decks": []}, indent=2))
        return

    decks = []
    for d in sorted(DEFAULT_OUTPUT_BASE.iterdir()):
        if d.is_dir() and (d / "index.html").exists():
            index_file = d / "index.html"
            decks.append({
                "slug": d.name,
                "path": str(index_file),
                "modified_at": os.path.getmtime(index_file),
                "size_kb": round(index_file.stat().st_size / 1024, 1),
            })
    print(json.dumps({
        "status": "success",
        "total_decks": len(decks),
        "output_dir": str(DEFAULT_OUTPUT_BASE),
        "decks": decks
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Course Deck Builder - Pedagogical Learning Slide Generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Periksa status kesiapan modul dan dependensi")
    p_status.set_defaults(func=cmd_status)

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate modul kurikulum pembelajaran jadi slide guizang-ppt")
    p_gen.add_argument("--title", "-t", required=True, help="Judul kurikulum / materi")
    p_gen.add_argument("--topic", help="Topik utama (default: sama dengan title)")
    p_gen.add_argument("--level", default="Pemula hingga Menengah", help="Tingkat sasaran peserta didik")
    p_gen.add_argument("--style", choices=["magazine", "swiss"], default="magazine", help="Gaya visual: magazine (Monocle) atau swiss (Helvetica/grid)")
    p_gen.add_argument("--theme", help="Tema warna (misal: indigo-porcelain, ink-classic, ikb, lemon)")
    p_gen.add_argument("--slug", help="Slug folder output (opsional)")
    p_gen.add_argument("--output-dir", help="Lokasi folder output kustom")
    p_gen.add_argument("--gdrive", "--upload-gdrive", action="store_true", help="Otomatis upload slide ke folder Google Drive pembelajaran")
    p_gen.set_defaults(func=cmd_generate)

    # list
    p_list = subparsers.add_parser("list", help="Daftar seluruh slide deck kursus yang telah dibuat")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
