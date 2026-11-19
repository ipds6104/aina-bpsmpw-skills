#!/usr/bin/env python3
"""
slides_tool.py - Comprehensive Google Slides Architecture for Aina

Equipped with cutting-edge capabilities adapted from industry-grade deck engineering:
1. Creation: Widescreen 16:9 rich formatting (cards, 2-column, tables, code boxes) with auto-Drive conversion.
2. Deck Enhancement: Visual restyling, unified brand palette, background fills, and per-slide icon integration.
3. Two-Way Door Safety: Automatic dated backup ([BACKUP YYYY-MM-DD]) before modifying existing decks.
4. Visual QA & Verification: High-resolution PNG thumbnail rendering (pages.getThumbnail) to catch overflow.
5. Brand Extraction: Scrapes brand colors & Google Fonts from any website URL.
6. Realtime Text Manipulation: Global replaceAllText via Google Slides batchUpdate API.
7. Local Export: Download to PDF format for direct WhatsApp delivery.
"""

import argparse
from datetime import datetime
import json
import os
import re
import sys
import tempfile
import urllib.parse
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import requests

# Add paths to load gdrive_tool
for p in [
    "/app/skills/gdrive/scripts",
    "/app/workspaces/default/.agents/skills/gdrive/scripts",
    ".agents/skills/gdrive/scripts",
    "skills/gdrive/scripts",
    "/root/projects/aina/skills/gdrive/scripts"
]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.append(p)

try:
    import gdrive_tool
except ImportError:
    gdrive_tool = None

# Built-in Theme Palettes
THEMES = {
    "navy": {
        "name": "Navy Executive",
        "bg": RGBColor(248, 250, 252),      # Slate 50
        "primary": RGBColor(15, 23, 42),    # Slate 900
        "accent": RGBColor(37, 99, 235),    # Blue 600
        "secondary": RGBColor(71, 85, 105), # Slate 600
        "card_bg": RGBColor(255, 255, 255),
        "card_border": RGBColor(226, 232, 240),
        "header_bg": RGBColor(30, 58, 138), # Blue 900
        "header_text": RGBColor(255, 255, 255),
        "bg_hex": "#F8FAFC",
        "accent_hex": "2563EB",
        "body_hex": "#0F172A",
        "title_font": "Arial",
        "body_font": "Arial"
    },
    "emerald": {
        "name": "Emerald Growth",
        "bg": RGBColor(246, 254, 249),
        "primary": RGBColor(6, 78, 59),      # Emerald 900
        "accent": RGBColor(16, 185, 129),    # Emerald 500
        "secondary": RGBColor(55, 65, 81),
        "card_bg": RGBColor(255, 255, 255),
        "card_border": RGBColor(209, 250, 229),
        "header_bg": RGBColor(6, 78, 59),
        "header_text": RGBColor(255, 255, 255),
        "bg_hex": "#F6FEF9",
        "accent_hex": "10B981",
        "body_hex": "#064E3B",
        "title_font": "Arial",
        "body_font": "Arial"
    },
    "sunset": {
        "name": "Sunset Warm",
        "bg": RGBColor(255, 251, 245),
        "primary": RGBColor(124, 45, 18),    # Orange 900
        "accent": RGBColor(234, 88, 12),     # Orange 600
        "secondary": RGBColor(87, 83, 78),
        "card_bg": RGBColor(255, 255, 255),
        "card_border": RGBColor(254, 215, 170),
        "header_bg": RGBColor(154, 52, 18),
        "header_text": RGBColor(255, 255, 255),
        "bg_hex": "#FFFBF5",
        "accent_hex": "EA580C",
        "body_hex": "#7C2D12",
        "title_font": "Arial",
        "body_font": "Arial"
    },
    "slate": {
        "name": "Slate Minimalist",
        "bg": RGBColor(250, 250, 250),
        "primary": RGBColor(24, 24, 27),     # Zinc 900
        "accent": RGBColor(79, 70, 229),     # Indigo 600
        "secondary": RGBColor(113, 113, 122),
        "card_bg": RGBColor(255, 255, 255),
        "card_border": RGBColor(228, 228, 231),
        "header_bg": RGBColor(39, 39, 42),
        "header_text": RGBColor(255, 255, 255),
        "bg_hex": "#FAFAFA",
        "accent_hex": "4F46E5",
        "body_hex": "#18181B",
        "title_font": "Arial",
        "body_font": "Arial"
    },
    "midnight": {
        "name": "Midnight Dark",
        "bg": RGBColor(15, 23, 42),          # Slate 900
        "primary": RGBColor(248, 250, 252),  # White / Slate 50
        "accent": RGBColor(56, 189, 248),    # Sky 400
        "secondary": RGBColor(148, 163, 184),# Slate 400
        "card_bg": RGBColor(30, 41, 59),     # Slate 800
        "card_border": RGBColor(51, 65, 85), # Slate 700
        "header_bg": RGBColor(30, 41, 59),
        "header_text": RGBColor(56, 189, 248),
        "bg_hex": "#0F172A",
        "accent_hex": "38BDF8",
        "body_hex": "#F8FAFC",
        "title_font": "Arial",
        "body_font": "Arial"
    }
}

# Verified Icons8 Slugs Map
VERIFIED_ICONS = {
    "book": ["panduan", "buku", "literatur", "kamus", "referensi", "konsep"],
    "brain": ["analisis", "analitik", "kecerdasan", "ai", "machine learning", "strategi", "wawasan"],
    "bug": ["error", "troubleshoot", "debugging", "kendala", "anomali"],
    "chat": ["komunikasi", "konsultasi", "diskusi", "tanya", "qna", "koordinasi"],
    "checkmark": ["selesai", "target", "capaian", "evaluasi", "rekomendasi", "sukses"],
    "command-line": ["sistem", "script", "terminal", "cli", "backend", "otomasi"],
    "document": ["laporan", "surat", "dokumen", "pok", "berkas", "regulasi", "notula"],
    "download": ["ekspor", "unduh", "distribusi", "output", "arsip"],
    "idea": ["tujuan", "inovasi", "latar belakang", "gagasan", "peluang"],
    "lightning-bolt": ["kinerja", "kecepatan", "efisiensi", "performa", "produktivitas"],
    "rocket": ["peluncuran", "rencana", "langkah", "tahapan", "program", "tindak lanjut"],
    "settings": ["konfigurasi", "teknis", "mekanisme", "metodologi", "prosedur"],
    "shield": ["keamanan", "integritas", "validasi", "kontrol", "opsec", "kebijakan"],
    "star": ["prioritas", "unggulan", "inti", "highlight", "pilar", "prinsip"],
    "workflow": ["alur", "proses", "sop", "siklus", "tahap", "timeline"]
}


def get_token():
    """Retrieve OAuth token from gdrive_tool or environment."""
    if gdrive_tool:
        try:
            return gdrive_tool.get_valid_access_token()
        except Exception:
            pass
    token = os.environ.get("GOOGLE_ACCESS_TOKEN", "").strip()
    if token:
        return token
    raise RuntimeError("Tidak dapat memperoleh token Google OAuth. Jalankan 'gdrive_tool auth' terlebih dahulu.")


def extract_id(input_str):
    """Extract presentation ID from URL or return raw ID."""
    if not input_str:
        return ""
    if gdrive_tool:
        return gdrive_tool.extract_resource_id(input_str)
    m = re.search(r"/presentation/d/([a-zA-Z0-9-_]+)", input_str)
    if m:
        return m.group(1)
    m2 = re.search(r"/d/([a-zA-Z0-9-_]+)", input_str)
    if m2:
        return m2.group(1)
    m3 = re.search(r"id=([a-zA-Z0-9-_]+)", input_str)
    if m3:
        return m3.group(1)
    return input_str.strip()


def hex_to_rgb(hex_str):
    """Convert hex string (with or without #) to Google Slides rgbColor float dict."""
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return {
        "red": int(h[0:2], 16) / 255.0,
        "green": int(h[2:4], 16) / 255.0,
        "blue": int(h[4:6], 16) / 255.0
    }


def find_icon_for_title(title_text):
    """Select the best verified Icons8 slug for a slide based on keyword matching."""
    text_lower = title_text.lower()
    for slug, keywords in VERIFIED_ICONS.items():
        if any(kw in text_lower for kw in keywords):
            return slug
    return "star"


def set_bg_color(slide, prs, color):
    """Fill slide background with a solid color in python-pptx."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def create_presentation_file(title, subtitle=None, slides_data=None, theme_name="navy", output_path=None):
    """Build a PPTX presentation with rich formatting and presentation-grade card patterns."""
    theme = THEMES.get(theme_name.lower(), THEMES["navy"])
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # 1. Slide Judul / Cover
    title_slide = prs.slides.add_slide(blank_layout)
    set_bg_color(title_slide, prs, theme["bg"])

    top_bar = title_slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.4)
    )
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = theme["accent"]
    top_bar.line.fill.background()

    title_box = title_slide.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(2.2))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = theme["title_font"]
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = theme["primary"]
    p.alignment = PP_ALIGN.LEFT

    sub_text = subtitle if subtitle else "Dibuat otomatis oleh Aina • BPS Kabupaten Mempawah"
    sub_box = title_slide.shapes.add_textbox(Inches(1.2), Inches(4.5), Inches(11.0), Inches(1.5))
    stf = sub_box.text_frame
    stf.word_wrap = True
    sp = stf.paragraphs[0]
    sp.text = sub_text
    sp.font.name = theme["body_font"]
    sp.font.size = Pt(20)
    sp.font.color.rgb = theme["secondary"]
    sp.alignment = PP_ALIGN.LEFT

    if not slides_data:
        slides_data = []

    # 2. Content Slides
    for item in slides_data:
        stype = item.get("type", "content").lower()
        slide = prs.slides.add_slide(blank_layout)
        set_bg_color(slide, prs, theme["bg"])

        # Accent Bar
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(0.7), Inches(1.5), Inches(0.08)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = theme["accent"]
        line.line.fill.background()

        # Title
        stitle_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.85), Inches(11.3), Inches(1.0))
        stf = stitle_box.text_frame
        stf.word_wrap = True
        stp = stf.paragraphs[0]
        stp.text = item.get("title", "Materi Presentasi")
        stp.font.name = theme["title_font"]
        stp.font.size = Pt(28)
        stp.font.bold = True
        stp.font.color.rgb = theme["primary"]

        if stype == "cards" or "cards" in item:
            cards = item.get("cards", [])
            num_cards = min(len(cards), 4)
            if num_cards > 0:
                card_w = (11.333 - (0.4 * (num_cards - 1))) / num_cards
                for idx, c in enumerate(cards[:num_cards]):
                    cx = 1.0 + idx * (card_w + 0.4)
                    cy = 2.1
                    ch = 4.4

                    c_shape = slide.shapes.add_shape(
                        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(cx), Inches(cy), Inches(card_w), Inches(ch)
                    )
                    c_shape.fill.solid()
                    c_shape.fill.fore_color.rgb = theme["card_bg"]
                    c_shape.line.color.rgb = theme["card_border"]
                    c_shape.line.width = Pt(1.5)

                    ct_box = slide.shapes.add_textbox(Inches(cx + 0.25), Inches(cy + 0.3), Inches(card_w - 0.5), Inches(0.8))
                    ctf = ct_box.text_frame
                    ctf.word_wrap = True
                    cp = ctf.paragraphs[0]
                    cp.text = c.get("title", "")
                    cp.font.name = theme["title_font"]
                    cp.font.size = Pt(18)
                    cp.font.bold = True
                    cp.font.color.rgb = theme["accent"]

                    cd_box = slide.shapes.add_textbox(Inches(cx + 0.25), Inches(cy + 1.1), Inches(card_w - 0.5), Inches(3.0))
                    cdf = cd_box.text_frame
                    cdf.word_wrap = True
                    desc = c.get("desc", c.get("content", ""))
                    if isinstance(desc, list):
                        for b_idx, bullet in enumerate(desc):
                            bp = cdf.paragraphs[0] if b_idx == 0 else cdf.add_paragraph()
                            bp.text = f"•  {bullet}"
                            bp.font.name = theme["body_font"]
                            bp.font.size = Pt(14)
                            bp.font.color.rgb = theme["secondary"]
                            bp.space_after = Pt(8)
                    else:
                        dp = cdf.paragraphs[0]
                        dp.text = str(desc)
                        dp.font.name = theme["body_font"]
                        dp.font.size = Pt(14)
                        dp.font.color.rgb = theme["secondary"]

            # Takeaway Caption underneath cards
            caption = item.get("caption", item.get("takeaway", ""))
            if caption:
                cap_box = slide.shapes.add_textbox(Inches(1.0), Inches(6.6), Inches(11.3), Inches(0.5))
                cap_p = cap_box.text_frame.paragraphs[0]
                cap_p.text = f"💡 {caption}"
                cap_p.font.name = theme["body_font"]
                cap_p.font.size = Pt(12)
                cap_p.font.italic = True
                cap_p.font.color.rgb = theme["secondary"]

        elif stype == "two_column":
            col1 = item.get("col1", {})
            col2 = item.get("col2", {})
            for idx, (col, title_key, bullet_key) in enumerate([(col1, "col1_title", "col1_bullets"), (col2, "col2_title", "col2_bullets")]):
                cx = 1.0 + idx * 5.8
                card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(cx), Inches(2.1), Inches(5.4), Inches(4.6))
                card.fill.solid()
                card.fill.fore_color.rgb = theme["card_bg"]
                card.line.color.rgb = theme["card_border"]

                th = slide.shapes.add_textbox(Inches(cx + 0.3), Inches(2.3), Inches(4.8), Inches(0.7))
                th_p = th.text_frame.paragraphs[0]
                th_p.text = col.get("title", item.get(title_key, f"Poin Bagian {idx+1}"))
                th_p.font.name = theme["title_font"]
                th_p.font.size = Pt(18)
                th_p.font.bold = True
                th_p.font.color.rgb = theme["accent"]

                tb = slide.shapes.add_textbox(Inches(cx + 0.3), Inches(3.0), Inches(4.8), Inches(3.5))
                tbf = tb.text_frame
                tbf.word_wrap = True
                bullets = col.get("bullets", item.get(bullet_key, []))
                for b_idx, b_text in enumerate(bullets):
                    bp = tbf.paragraphs[0] if b_idx == 0 else tbf.add_paragraph()
                    bp.text = f"•  {b_text}"
                    bp.font.name = theme["body_font"]
                    bp.font.size = Pt(15)
                    bp.font.color.rgb = theme["secondary"]
                    bp.space_after = Pt(10)

        elif stype == "table" and "rows" in item:
            headers = item.get("headers", [])
            rows = item.get("rows", [])
            num_rows = len(rows) + (1 if headers else 0)
            num_cols = len(headers) if headers else (len(rows[0]) if rows else 1)

            t_shape = slide.shapes.add_table(num_rows, num_cols, Inches(1.0), Inches(2.1), Inches(11.3), Inches(0.6 * num_rows))
            table = t_shape.table

            r_offset = 0
            if headers:
                for col_idx, h_text in enumerate(headers):
                    cell = table.cell(0, col_idx)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = theme["header_bg"]
                    p = cell.text_frame.paragraphs[0]
                    p.text = str(h_text)
                    p.font.name = theme["title_font"]
                    p.font.size = Pt(15)
                    p.font.bold = True
                    p.font.color.rgb = theme["header_text"]
                    p.alignment = PP_ALIGN.CENTER
                r_offset = 1

            for row_idx, row_vals in enumerate(rows):
                for col_idx, val in enumerate(row_vals):
                    cell = table.cell(row_idx + r_offset, col_idx)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = theme["card_bg"] if (row_idx % 2 == 0) else theme["bg"]
                    p = cell.text_frame.paragraphs[0]
                    p.text = str(val)
                    p.font.name = theme["body_font"]
                    p.font.size = Pt(14)
                    p.font.color.rgb = theme["primary"]

        else:
            # Default Content Layout
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(2.1), Inches(11.333), Inches(4.7))
            card.fill.solid()
            card.fill.fore_color.rgb = theme["card_bg"]
            card.line.color.rgb = theme["card_border"]
            card.line.width = Pt(1.5)

            cbox = slide.shapes.add_textbox(Inches(1.4), Inches(2.4), Inches(10.5), Inches(4.1))
            ctf = cbox.text_frame
            ctf.word_wrap = True

            bullets = item.get("bullets", [])
            content_text = item.get("content", "")
            if bullets:
                for b_idx, b_text in enumerate(bullets):
                    bp = ctf.paragraphs[0] if b_idx == 0 else ctf.add_paragraph()
                    bp.text = f"•  {b_text}"
                    bp.font.name = theme["body_font"]
                    bp.font.size = Pt(18)
                    bp.font.color.rgb = theme["primary"]
                    bp.space_after = Pt(14)
            elif content_text:
                for b_idx, line_t in enumerate(content_text.split("\n")):
                    if not line_t.strip():
                        continue
                    bp = ctf.paragraphs[0] if b_idx == 0 else ctf.add_paragraph()
                    bp.text = line_t
                    bp.font.name = theme["body_font"]
                    bp.font.size = Pt(18)
                    bp.font.color.rgb = theme["primary"]
                    bp.space_after = Pt(12)

    # 3. Slide Penutup
    closing_slide = prs.slides.add_slide(blank_layout)
    set_bg_color(closing_slide, prs, theme["bg"])

    bottom_bar = closing_slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(7.1), Inches(13.333), Inches(0.4)
    )
    bottom_bar.fill.solid()
    bottom_bar.fill.fore_color.rgb = theme["accent"]
    bottom_bar.line.fill.background()

    c_box = closing_slide.shapes.add_textbox(Inches(1.5), Inches(2.8), Inches(10.3), Inches(2.0))
    c_tf = c_box.text_frame
    c_tf.word_wrap = True
    cp = c_tf.paragraphs[0]
    cp.text = "Terima Kasih"
    cp.font.name = theme["title_font"]
    cp.font.size = Pt(48)
    cp.font.bold = True
    cp.font.color.rgb = theme["primary"]
    cp.alignment = PP_ALIGN.CENTER

    sub_cp = c_tf.add_paragraph()
    sub_cp.text = "Ada pertanyaan atau tanggapan?"
    sub_cp.font.name = theme["body_font"]
    sub_cp.font.size = Pt(20)
    sub_cp.font.color.rgb = theme["secondary"]
    sub_cp.alignment = PP_ALIGN.CENTER

    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
        output_path = tmp.name
        tmp.close()

    prs.save(output_path)
    return output_path, len(prs.slides)


def upload_and_convert_to_google_slides(pptx_path, title, share_type="anyone", role="writer"):
    """Upload PPTX to Google Drive and convert to native Google Slides."""
    token = get_token()
    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    headers = {"Authorization": f"Bearer {token}"}

    metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.presentation"
    }

    with open(pptx_path, "rb") as f:
        clean_filename = f"{title}.pptx"
        files = {
            "data": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
            "file": (clean_filename, f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        }
        res = requests.post(url, headers=headers, files=files, timeout=60)

    if res.status_code not in [200, 201]:
        raise RuntimeError(f"Gagal upload ke Google Drive: {res.status_code} - {res.text}")

    data = res.json()
    file_id = data.get("id")
    slides_url = f"https://docs.google.com/presentation/d/{file_id}/edit?usp=sharing"

    shared = False
    if share_type and gdrive_tool:
        try:
            gdrive_tool.set_drive_permissions(token, file_id, share_type=share_type, role=role)
            shared = True
        except Exception:
            pass

    return {
        "status": "success",
        "id": file_id,
        "title": title,
        "url": slides_url,
        "shared": shared,
        "role": role
    }


def backup_deck(deck_id, title_prefix=None):
    """Safety Protocol: Create a dated backup of the deck in Google Drive before editing."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.now().strftime("%Y-%m-%d")

    # Get original title
    meta_res = requests.get(f"https://www.googleapis.com/drive/v3/files/{deck_id}?fields=name", headers=headers, timeout=10)
    orig_name = meta_res.json().get("name", "Untitled Presentation") if meta_res.status_code == 200 else "Presentation"

    backup_name = f"[BACKUP {today}] {orig_name}"
    copy_res = requests.post(f"https://www.googleapis.com/drive/v3/files/{deck_id}/copy", headers=headers, json={"name": backup_name}, timeout=30)
    if copy_res.status_code not in [200, 201]:
        raise RuntimeError(f"Gagal membuat backup deck: {copy_res.status_code} - {copy_res.text}")

    data = copy_res.json()
    b_id = data.get("id")
    return {
        "status": "success",
        "original_id": deck_id,
        "backup_id": b_id,
        "backup_name": backup_name,
        "backup_url": f"https://docs.google.com/presentation/d/{b_id}/edit"
    }


def render_slide_thumbnail(presentation_id, slide_object_id, out_path):
    """Render a single slide to PNG via Google Slides getThumbnail."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}/pages/{slide_object_id}/thumbnail?thumbnailProperties.mimeType=PNG&thumbnailProperties.thumbnailSize=LARGE"
    res = requests.get(url, headers=headers, timeout=20)
    if res.status_code != 200:
        raise RuntimeError(f"Gagal mengambil thumbnail: {res.status_code} - {res.text}")

    img_url = res.json().get("contentUrl")
    img_data = requests.get(img_url, timeout=30).content

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(img_data)
    return out_path, len(img_data)


def cmd_backup(args):
    """Handle backup command."""
    file_id = extract_id(args.id or args.url)
    if not file_id:
        print(json.dumps({"status": "error", "message": "ID atau URL Google Slides wajib disediakan."}, indent=2))
        sys.exit(1)
    res = backup_deck(file_id)
    print(json.dumps(res, indent=2))


def cmd_thumbnail(args):
    """Render slide(s) to PNG thumbnail for visual verification."""
    file_id = extract_id(args.id or args.url)
    if not file_id:
        print(json.dumps({"status": "error", "message": "ID atau URL Google Slides wajib disediakan."}, indent=2))
        sys.exit(1)

    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    p_res = requests.get(f"https://slides.googleapis.com/v1/presentations/{file_id}", headers=headers, timeout=20)
    if p_res.status_code != 200:
        print(json.dumps({"status": "error", "code": p_res.status_code, "message": p_res.text}, indent=2))
        sys.exit(1)

    slides = p_res.json().get("slides", [])
    if not slides:
        print(json.dumps({"status": "error", "message": "Presentasi tidak memuat slide."}, indent=2))
        sys.exit(1)

    out_images = []
    if args.all:
        out_dir = args.out_dir or f"/tmp/slides_verify_{file_id}"
        for idx, s in enumerate(slides):
            s_id = s.get("objectId")
            out_file = os.path.join(out_dir, f"slide_{idx+1}_{s_id}.png")
            render_slide_thumbnail(file_id, s_id, out_file)
            out_images.append({"index": idx + 1, "slide_id": s_id, "path": out_file})
    else:
        s_idx = max(0, min(args.index - 1, len(slides) - 1))
        target_slide = slides[s_idx]
        s_id = target_slide.get("objectId")
        out_file = args.out or f"/tmp/slide_{file_id}_{s_idx+1}.png"
        render_slide_thumbnail(file_id, s_id, out_file)
        out_images.append({"index": s_idx + 1, "slide_id": s_id, "path": out_file})

    print(json.dumps({
        "status": "success",
        "id": file_id,
        "total_rendered": len(out_images),
        "thumbnails": out_images
    }, indent=2))


def cmd_enhance(args):
    """
    Comprehensive deck enhancement:
    1. Automatic safety backup.
    2. Background refresh & visual consistency across all slides.
    3. Per-slide Icons8 icon integration on content slides.
    4. Optional visual thumbnail verification.
    """
    file_id = extract_id(args.id or args.url)
    if not file_id:
        print(json.dumps({"status": "error", "message": "ID atau URL Google Slides wajib disediakan."}, indent=2))
        sys.exit(1)

    theme = THEMES.get(args.theme.lower(), THEMES["navy"])
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Safety Backup
    backup_info = None
    if not args.no_backup:
        backup_info = backup_deck(file_id)

    # 2. Read Deck
    p_res = requests.get(f"https://slides.googleapis.com/v1/presentations/{file_id}", headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if p_res.status_code != 200:
        print(json.dumps({"status": "error", "code": p_res.status_code, "message": p_res.text}, indent=2))
        sys.exit(1)

    data = p_res.json()
    slides = data.get("slides", [])

    # Phase A: Backgrounds
    bg_reqs = []
    for s in slides:
        s_id = s.get("objectId")
        bg_reqs.append({
            "updatePageProperties": {
                "objectId": s_id,
                "pageProperties": {
                    "pageBackgroundFill": {
                        "solidFill": {
                            "color": {"rgbColor": hex_to_rgb(theme["bg_hex"])},
                            "alpha": 1.0
                        }
                    }
                },
                "fields": "pageBackgroundFill.solidFill.color"
            }
        })

    if bg_reqs:
        requests.post(f"https://slides.googleapis.com/v1/presentations/{file_id}:batchUpdate", headers=headers, json={"requests": bg_reqs}, timeout=30)

    # Phase B: Icons on content slides (excluding cover)
    icons_added = 0
    if args.icons and len(slides) > 1:
        for idx, s in enumerate(slides[1:], start=2):
            s_id = s.get("objectId")
            # Extract title
            elements = s.get("pageElements", [])
            title_text = ""
            for el in elements:
                t_el = el.get("shape", {}).get("text", {})
                for te in t_el.get("textElements", []):
                    title_text += te.get("textRun", {}).get("content", "")

            slug = find_icon_for_title(title_text)
            icon_url = f"https://img.icons8.com/ios-filled/192/{theme['accent_hex']}/{slug}.png"

            img_req = {
                "createImage": {
                    "url": icon_url,
                    "elementProperties": {
                        "pageObjectId": s_id,
                        "size": {
                            "width": {"magnitude": 450000, "unit": "EMU"},
                            "height": {"magnitude": 450000, "unit": "EMU"}
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 8300000,
                            "translateY": 300000,
                            "unit": "EMU"
                        }
                    }
                }
            }
            # Send icon requests individually with retry to guard against flakiness
            for _ in range(2):
                res = requests.post(f"https://slides.googleapis.com/v1/presentations/{file_id}:batchUpdate", headers=headers, json={"requests": [img_req]}, timeout=15)
                if res.status_code == 200:
                    icons_added += 1
                    break

    # Phase C: Optional Thumbnail Verification
    thumbnails = []
    if args.verify:
        for idx, s in enumerate(slides[:3]):
            s_id = s.get("objectId")
            out_file = f"/tmp/verify_enhance_{file_id}_{idx+1}.png"
            render_slide_thumbnail(file_id, s_id, out_file)
            thumbnails.append(out_file)

    print(json.dumps({
        "status": "success",
        "id": file_id,
        "title": data.get("title", ""),
        "theme_applied": theme["name"],
        "backup": backup_info,
        "slides_enhanced": len(slides),
        "icons_added": icons_added,
        "verification_thumbnails": thumbnails,
        "url": f"https://docs.google.com/presentation/d/{file_id}/edit"
    }, indent=2))


def cmd_brand_extract(args):
    """Scrape website to extract brand color palette and font declarations."""
    url = args.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    try:
        res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        html = res.text

        # Extract hex colors
        hex_candidates = re.findall(r"#(?:[0-9a-fA-F]{3}){1,2}\b", html)
        color_counts = {}
        for h in hex_candidates:
            h_norm = h.upper()
            if h_norm not in ["#FFF", "#FFFFFF", "#000", "#000000", "#CCC", "#EEE"]:
                color_counts[h_norm] = color_counts.get(h_norm, 0) + 1

        sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
        primary_accent = sorted_colors[0][0] if sorted_colors else "#2563EB"
        secondary_accent = sorted_colors[1][0] if len(sorted_colors) > 1 else "#10B981"

        # Extract Google Font
        font_match = re.search(r"fonts\.googleapis\.com/css2\?family=([a-zA-Z+]+)", html)
        font_family = font_match.group(1).replace("+", " ") if font_match else "Arial"

        palette = {
            "status": "success",
            "source_url": url,
            "tokens": {
                "background": "#F8FAFC",
                "primary_accent": primary_accent,
                "secondary_accent": secondary_accent,
                "body_text": "#0F172A",
                "font_family": font_family
            },
            "command_suggestion": f"slides_tool create --title '...' --theme navy"
        }
        print(json.dumps(palette, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        sys.exit(1)


def cmd_create(args):
    """Handle create command."""
    title = args.title.strip()
    subtitle = args.subtitle.strip() if args.subtitle else None
    theme = args.theme.lower()

    slides_data = []
    if args.slides_json:
        if os.path.exists(args.slides_json):
            with open(args.slides_json, "r", encoding="utf-8") as f:
                slides_data = json.load(f)
        else:
            slides_data = json.loads(args.slides_json)

    local_pptx = args.out_pptx
    pptx_file, slide_count = create_presentation_file(
        title=title,
        subtitle=subtitle,
        slides_data=slides_data,
        theme_name=theme,
        output_path=local_pptx
    )

    if args.local_only:
        print(json.dumps({
            "status": "success",
            "title": title,
            "slides_count": slide_count,
            "local_path": pptx_file
        }, indent=2))
        return

    result = upload_and_convert_to_google_slides(
        pptx_path=pptx_file,
        title=title,
        share_type=args.share,
        role=args.role
    )
    result["slides_count"] = slide_count

    # Optional Preview Thumbnail
    if args.thumbnail and result.get("id"):
        try:
            t_path = f"/tmp/preview_{result['id']}.png"
            p_res = requests.get(f"https://slides.googleapis.com/v1/presentations/{result['id']}", headers={"Authorization": f"Bearer {get_token()}"}, timeout=15)
            first_slide_id = p_res.json()["slides"][0]["objectId"]
            render_slide_thumbnail(result["id"], first_slide_id, t_path)
            result["preview_thumbnail"] = t_path
        except Exception:
            pass

    if local_pptx:
        result["local_path"] = local_pptx
    elif os.path.exists(pptx_file) and not args.out_pptx:
        try:
            os.remove(pptx_file)
        except OSError:
            pass

    print(json.dumps(result, indent=2))


def cmd_read(args):
    """Inspect and read existing Google Slides presentation."""
    file_id = extract_id(args.id or args.url)
    if not file_id:
        print(json.dumps({"status": "error", "message": "ID atau URL Google Slides wajib disediakan."}, indent=2))
        sys.exit(1)

    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://slides.googleapis.com/v1/presentations/{file_id}"
    res = requests.get(url, headers=headers, timeout=20)

    if res.status_code != 200:
        print(json.dumps({"status": "error", "code": res.status_code, "message": res.text}, indent=2))
        sys.exit(1)

    data = res.json()
    title = data.get("title", "")
    slides = data.get("slides", [])

    slides_summary = []
    for idx, s in enumerate(slides):
        elements = s.get("pageElements", [])
        texts = []
        for el in elements:
            shape = el.get("shape", {})
            text_el = shape.get("text", {})
            for te in text_el.get("textElements", []):
                run = te.get("textRun", {})
                content = run.get("content", "").strip()
                if content:
                    texts.append(content)
        slides_summary.append({
            "index": idx + 1,
            "element_count": len(elements),
            "text_content": texts
        })

    result = {
        "status": "success",
        "id": file_id,
        "title": title,
        "slide_count": len(slides),
        "url": f"https://docs.google.com/presentation/d/{file_id}/edit",
        "slides": slides_summary
    }
    print(json.dumps(result, indent=2))


def cmd_replace_text(args):
    """Replace text in an existing Google Slides presentation in realtime."""
    file_id = extract_id(args.id or args.url)
    find_text = args.find
    replace_text = args.replace
    match_case = args.match_case

    if not file_id or not find_text:
        print(json.dumps({"status": "error", "message": "ID dan teks pencarian (--find) wajib diisi."}, indent=2))
        sys.exit(1)

    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"https://slides.googleapis.com/v1/presentations/{file_id}:batchUpdate"

    req_body = {
        "requests": [
            {
                "replaceAllText": {
                    "containsText": {
                        "text": find_text,
                        "matchCase": match_case
                    },
                    "replaceText": replace_text
                }
            }
        ]
    }

    res = requests.post(url, headers=headers, json=req_body, timeout=20)
    if res.status_code != 200:
        print(json.dumps({"status": "error", "code": res.status_code, "message": res.text}, indent=2))
        sys.exit(1)

    data = res.json()
    replies = data.get("replies", [{}])
    occurrences = replies[0].get("replaceAllText", {}).get("occurrencesChanged", 0)

    print(json.dumps({
        "status": "success",
        "id": file_id,
        "find_text": find_text,
        "replace_text": replace_text,
        "occurrences_changed": occurrences,
        "url": f"https://docs.google.com/presentation/d/{file_id}/edit"
    }, indent=2))


def cmd_export_pdf(args):
    """Export Google Slides to a local PDF file."""
    file_id = extract_id(args.id or args.url)
    out_path = args.out or f"workspace/presentation_{file_id}.pdf"

    if not file_id:
        print(json.dumps({"status": "error", "message": "ID atau URL Google Slides wajib disediakan."}, indent=2))
        sys.exit(1)

    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://docs.google.com/presentation/d/{file_id}/export/pdf"

    res = requests.get(url, headers=headers, timeout=60)
    if res.status_code != 200:
        print(json.dumps({"status": "error", "code": res.status_code, "message": res.text}, indent=2))
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(res.content)

    print(json.dumps({
        "status": "success",
        "id": file_id,
        "pdf_path": out_path,
        "bytes_downloaded": len(res.content)
    }, indent=2))


def cmd_status(args):
    """Check authentication and slides service readiness."""
    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        user_res = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers=headers, timeout=10)
        user_email = user_res.json().get("email", "unknown") if user_res.status_code == 200 else "unknown"

        slides_api_active = False
        s_res = requests.get("https://slides.googleapis.com/v1/presentations/test_id", headers=headers, timeout=10)
        if s_res.status_code == 404:
            slides_api_active = True
        elif s_res.status_code == 403 and "disabled" not in s_res.text:
            slides_api_active = True

        print(json.dumps({
            "status": "ready",
            "account": user_email,
            "drive_conversion": True,
            "native_slides_api": slides_api_active,
            "themes": list(THEMES.keys()),
            "verified_icons": list(VERIFIED_ICONS.keys()),
            "message": "Aina Google Slides Architecture 2.0 is fully operational."
        }, indent=2))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2))
        sys.exit(1)


def cmd_delete_element(args):
    file_id = resolve_file_id(args.id, args.url)
    if not file_id:
        print(json.dumps({"status": "error", "message": "ID atau URL wajib diisi."}, indent=2))
        sys.exit(1)
    if not args.objects:
        print(json.dumps({"status": "error", "message": "Daftar objectId (--objects) wajib diisi."}, indent=2))
        sys.exit(1)

    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    reqs = [{"deleteObject": {"objectId": oid}} for oid in args.objects]
    res = requests.post(
        f"https://slides.googleapis.com/v1/presentations/{file_id}:batchUpdate",
        headers=headers,
        json={"requests": reqs},
        timeout=30
    )
    if res.status_code == 200:
        print(json.dumps({"status": "success", "id": file_id, "deleted_objects": args.objects}, indent=2))
    else:
        print(json.dumps({"status": "error", "code": res.status_code, "message": res.text}, indent=2))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Aina Google Slides CLI 2.0")
    subparsers = parser.add_subparsers(dest="command")

    # Status
    subparsers.add_parser("status", help="Cek status otorisasi dan kesiapan Google Slides")

    # Create
    p_create = subparsers.add_parser("create", help="Buat Google Slides baru dan bagikan tautannya")
    p_create.add_argument("--title", required=True, help="Judul Presentasi")
    p_create.add_argument("--subtitle", default="", help="Subjudul atau keterangan pembuka")
    p_create.add_argument("--theme", default="navy", choices=list(THEMES.keys()), help="Tema warna slide")
    p_create.add_argument("--slides-json", default="", help="JSON string atau path berkas JSON struktur slide")
    p_create.add_argument("--share", default="anyone", choices=["anyone", "user", "domain", "none"], help="Akses sharing")
    p_create.add_argument("--role", default="writer", choices=["reader", "writer", "commenter"], help="Hak akses link")
    p_create.add_argument("--out-pptx", default="", help="Path lokal untuk salinan berkas .pptx")
    p_create.add_argument("--thumbnail", action="store_true", help="Generate thumbnail preview otomatis")
    p_create.add_argument("--local-only", action="store_true", help="Hanya generate berkas PPTX lokal")

    # Enhance (Adopted from eranw2000/google-slides-skill)
    p_enh = subparsers.add_parser("enhance", help="Poles dan perindah deck Google Slides yang sudah ada")
    p_enh.add_argument("--id", default="", help="ID Dokumen Google Slides")
    p_enh.add_argument("--url", default="", help="URL Dokumen Google Slides")
    p_enh.add_argument("--theme", default="navy", choices=list(THEMES.keys()), help="Tema warna target")
    p_enh.add_argument("--icons", action="store_true", help="Tambahkan ikon otomatis di pojok slide konten")
    p_enh.add_argument("--no-backup", action="store_true", help="Lewati pembuatan backup (tidak disarankan)")
    p_enh.add_argument("--verify", action="store_true", help="Render thumbnail untuk verifikasi visual")

    # Backup
    p_bak = subparsers.add_parser("backup", help="Buat salinan cadangan [BACKUP YYYY-MM-DD] dari deck")
    p_bak.add_argument("--id", default="", help="ID Dokumen Google Slides")
    p_bak.add_argument("--url", default="", help="URL Dokumen Google Slides")

    # Thumbnail
    p_thm = subparsers.add_parser("thumbnail", help="Render slide ke gambar PNG untuk verifikasi visual")
    p_thm.add_argument("--id", default="", help="ID Dokumen Google Slides")
    p_thm.add_argument("--url", default="", help="URL Dokumen Google Slides")
    p_thm.add_argument("--index", type=int, default=1, help="Nomor slide yang ingin di-render (1-based)")
    p_thm.add_argument("--out", default="", help="Path berkas output PNG")
    p_thm.add_argument("--all", action="store_true", help="Render seluruh slide")
    p_thm.add_argument("--out-dir", default="", help="Direktori target bila merender seluruh slide")

    # Brand Extract
    p_ext = subparsers.add_parser("brand-extract", help="Ekstrak palet warna dan font dari website")
    p_ext.add_argument("--url", required=True, help="URL Website atau Brand Kit")

    # Read / Inspect
    p_read = subparsers.add_parser("read", help="Baca dan periksa isi dokumen Google Slides yang sudah ada")
    p_read.add_argument("--id", default="", help="ID Dokumen Google Slides")
    p_read.add_argument("--url", default="", help="URL Dokumen Google Slides")

    # Replace Text
    p_replace = subparsers.add_parser("replace-text", help="Ganti teks dalam Google Slides secara realtime")
    p_replace.add_argument("--id", default="", help="ID Dokumen Google Slides")
    p_replace.add_argument("--url", default="", help="URL Dokumen Google Slides")
    p_replace.add_argument("--find", required=True, help="Teks yang dicari")
    p_replace.add_argument("--replace", required=True, help="Teks pengganti")
    p_replace.add_argument("--match-case", action="store_true", help="Pencarian case-sensitive")

    # Delete Element
    p_del = subparsers.add_parser("delete-element", help="Hapus elemen (tabel, gambar, shape dummy) dari slide")
    p_del.add_argument("--id", default="", help="ID Dokumen Google Slides")
    p_del.add_argument("--url", default="", help="URL Dokumen Google Slides")
    p_del.add_argument("--objects", nargs="+", required=True, help="Daftar objectId elemen yang ingin dihapus")

    # Export PDF
    p_export = subparsers.add_parser("export-pdf", help="Ekspor Google Slides ke berkas PDF lokal")
    p_export.add_argument("--id", default="", help="ID Dokumen Google Slides")
    p_export.add_argument("--url", default="", help="URL Dokumen Google Slides")
    p_export.add_argument("--out", default="", help="Path berkas output PDF")

    args = parser.parse_args()
    if args.command == "status":
        cmd_status(args)
    elif args.command == "create":
        cmd_create(args)
    elif args.command == "enhance":
        cmd_enhance(args)
    elif args.command == "backup":
        cmd_backup(args)
    elif args.command == "thumbnail":
        cmd_thumbnail(args)
    elif args.command == "brand-extract":
        cmd_brand_extract(args)
    elif args.command == "read":
        cmd_read(args)
    elif args.command == "replace-text":
        cmd_replace_text(args)
    elif args.command == "delete-element":
        cmd_delete_element(args)
    elif args.command == "export-pdf":
        cmd_export_pdf(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
