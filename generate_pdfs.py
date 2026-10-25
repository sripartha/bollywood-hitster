import os
import json
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics import renderPDF

os.makedirs("/workspace/bollywood-hitster/pdfs", exist_ok=True)

with open("/workspace/bollywood-hitster/catalog.json") as f:
    catalog = json.load(f)

# Single brand color ONLY for the "BOLLYGOOD" brand name; everything else is 100% pure Black & Dark Gray
# Zero background fills (fill=0) so colored cardstock or clear/translucent labels show through and zero background ink is wasted!
BRAND_COLOR = colors.HexColor("#c1121f")  # Classic BollyGood crimson
BLACK = colors.HexColor("#000000")
DARK_GRAY = colors.HexColor("#222222")
LIGHT_GRAY = colors.HexColor("#c4c4cc")

def truncate_text(c, text, font_name, font_size, max_width):
    if c.stringWidth(text, font_name, font_size) <= max_width:
        return text
    while len(text) > 3 and c.stringWidth(text + "...", font_name, font_size) > max_width:
        text = text[:-1]
    return text + "..."

def wrap_two_lines(c, text, font_name, font_size, max_width):
    words = text.split()
    line1 = ""
    idx = 0
    while idx < len(words):
        test = (line1 + " " + words[idx]).strip()
        if c.stringWidth(test, font_name, font_size) <= max_width:
            line1 = test
            idx += 1
        else:
            break
    if not line1 and words:
        line1 = truncate_text(c, words[0], font_name, font_size, max_width)
        idx = 1
    rest = " ".join(words[idx:])
    line2 = truncate_text(c, rest, font_name, font_size, max_width) if rest else ""
    return line1, line2

def draw_qr_widget(c, cx, cy, qr_size, item):
    qx = cx - qr_size / 2.0
    qy = cy - qr_size / 2.0
    qr_payload = f"https://sripartha.github.io/bollywood-hitster/?card={item['card_id']}&sp={item['spotify_id']}"
    qr_widget = QrCodeWidget(qr_payload, barLevel="M", barFillColor=BLACK, barBorder=0)
    bounds = qr_widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    d = Drawing(qr_size, qr_size, transform=[qr_size / w, 0, 0, qr_size / h, 0, 0])
    d.add(qr_widget)
    renderPDF.draw(d, c, qx, qy)

# ==============================================================================
# 1. AVERY 5371 / 8371 PRE-PERFORATED COMPACT CARDS (3.5" x 2.0", 10-UP, 1-SIDED ANSWERS)
# ==============================================================================
def draw_avery5371_answer_card(c, x, y, w, h, item):
    # Safe inset inside each 3.5" x 2.0" perforated card (no background fill -> fill=0)
    pad = 0.12 * inch
    ix, iy = x + pad, y + pad
    iw, ih = w - 2 * pad, h - 2 * pad

    c.setStrokeColor(BLACK)
    c.setLineWidth(1.2)
    c.roundRect(ix, iy, iw, ih, 6, stroke=1, fill=0)

    # Top bar: BOLLYGOOD (crimson bold) on left, #A-001 (black bold) on right
    c.setFillColor(BRAND_COLOR)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(ix + 8, iy + ih - 0.21 * inch, "BOLLYGOOD")

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 9.0)
    c.drawRightString(ix + iw - 8, iy + ih - 0.21 * inch, f"#{item['card_label']}")

    # Thin black divider under top bar
    c.setStrokeColor(BLACK)
    c.setLineWidth(0.7)
    line_y = iy + ih - 0.27 * inch
    c.line(ix + 6, line_y, ix + iw - 6, line_y)

    # Left column: Giant Year
    left_w = 1.12 * inch
    left_cx = ix + left_w / 2.0 + 0.03 * inch
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 31)
    c.drawCentredString(left_cx, iy + ih * 0.42, str(item["year"]))

    # Vertical separator between Year and Song details
    sep_x = ix + left_w + 0.04 * inch
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(0.6)
    c.line(sep_x, iy + 0.10 * inch, sep_x, line_y - 0.06 * inch)

    # Right column: Song Title + Film/No-Film + Vocal/Music/Cast
    rx = sep_x + 0.08 * inch
    rw = (ix + iw - 8) - rx

    # Song Title (1 or 2 lines)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 10.5)
    l1, l2 = wrap_two_lines(c, item["title"], "Helvetica-Bold", 10.5, rw)
    if l2:
        c.drawString(rx, line_y - 0.19 * inch, l1)
        c.drawString(rx, line_y - 0.34 * inch, l2)
        film_y = line_y - 0.52 * inch
    else:
        c.drawString(rx, line_y - 0.22 * inch, l1)
        film_y = line_y - 0.43 * inch

    # Film or NO FILM (Indipop) • Artist
    c.setFillColor(BLACK)
    if item.get("is_no_film"):
        c.setFont("Helvetica-Bold", 8.2)
        nf_str = truncate_text(c, f"NO FILM (Indipop) • {item['singers']}", "Helvetica-Bold", 8.2, rw)
        c.drawString(rx, film_y, nf_str)
    else:
        c.setFont("Helvetica-BoldOblique", 9.0)
        mv_str = truncate_text(c, f"Film: {item['movie']}", "Helvetica-BoldOblique", 9.0, rw)
        c.drawString(rx, film_y, mv_str)

    # Vocal / Music / Cast in crisp dark gray/black
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 7.2)
    s_line = truncate_text(c, f"Vocal: {item['singers']}", "Helvetica", 7.2, rw)
    m_line = truncate_text(c, f"Music: {item['music_director']}", "Helvetica", 7.2, rw)
    st_line = truncate_text(c, f"Cast: {item['stars']}", "Helvetica", 7.2, rw)
    c.drawString(rx, iy + 0.38 * inch, s_line)
    c.drawString(rx, iy + 0.24 * inch, m_line)
    c.drawString(rx, iy + 0.10 * inch, st_line)

def generate_avery5371_answers_pdf(deck_letter, songs, out_path):
    """
    Avery 5371 / 8371 standard 10-up business card template:
    Card size: 3.5" x 2.0", 2 cols x 5 rows = 10 per page
    Margins: 0.75" left/right, 0.5" top/bottom, 0" gap
    """
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter
    cols, rows = 2, 5
    card_w, card_h = 3.5 * inch, 2.0 * inch
    margin_x = 0.75 * inch
    margin_y = 0.5 * inch

    per_page = cols * rows
    total_pages = (len(songs) + per_page - 1) // per_page

    for p_idx in range(total_pages):
        batch = songs[p_idx * per_page : (p_idx + 1) * per_page]
        for i, item in enumerate(batch):
            r = i // cols
            col = i % cols
            x = margin_x + col * card_w
            y = page_h - margin_y - (r + 1) * card_h
            draw_avery5371_answer_card(c, x, y, card_w, card_h, item)
        c.showPage()

    c.save()
    print(f"Generated Avery 5371 1-Sided Answer Cards PDF: {out_path} ({total_pages} pages)")

# ==============================================================================
# 2. AVERY 22805 (1.5"x1.5" 20-UP) & AVERY 22806 (2.0"x2.0" 12-UP) SQUARE QR STICKERS
# ==============================================================================
def draw_square_qr_sticker(c, x, y, size, item, show_cut_border=False):
    if show_cut_border:
        c.setStrokeColor(LIGHT_GRAY)
        c.setLineWidth(0.4)
        c.setDash(2, 2)
        c.rect(x, y, size, size, stroke=1, fill=0)
        c.setDash()

    cx = x + size / 2.0
    # Top brand in crimson
    top_font = 7.8 if size <= 1.55 * inch else 9.2
    bot_font = 7.5 if size <= 1.55 * inch else 8.8
    top_offset = 0.18 * inch if size <= 1.55 * inch else 0.22 * inch
    bot_offset = 0.10 * inch if size <= 1.55 * inch else 0.14 * inch

    c.setFillColor(BRAND_COLOR)
    c.setFont("Helvetica-Bold", top_font)
    c.drawCentredString(cx, y + size - top_offset, "BOLLYGOOD")

    # Crisp black QR code in middle (no background fill -> works on clear/translucent or white sticker sheets!)
    qr_size = size * 0.64
    cy = y + size * 0.49
    draw_qr_widget(c, cx, cy, qr_size, item)

    # Bottom Card ID so Sri knows which card (#A-001) to stick it onto
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", bot_font)
    c.drawCentredString(cx, y + bot_offset, f"DECK {item['deck']} • #{item['card_num']:03d}")

def generate_avery22805_qr_stickers_pdf(deck_letter, songs, out_path):
    """
    Avery 22805 standard 1.5" x 1.5" square labels (20 per page, 4 cols x 5 rows):
    Left/Right margin: 0.75", Top/Bottom margin: 0.5", Col gap: 0.3125", Row gap: 0.5"
    """
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter
    cols, rows = 4, 5
    size = 1.5 * inch
    margin_x = 0.75 * inch
    margin_y = 0.5 * inch
    col_gap = 0.3125 * inch
    row_gap = 0.5 * inch

    per_page = cols * rows
    total_pages = (len(songs) + per_page - 1) // per_page

    for p_idx in range(total_pages):
        batch = songs[p_idx * per_page : (p_idx + 1) * per_page]
        for i, item in enumerate(batch):
            r = i // cols
            col = i % cols
            x = margin_x + col * (size + col_gap)
            y = page_h - margin_y - (r + 1) * size - r * row_gap
            draw_square_qr_sticker(c, x, y, size, item, show_cut_border=False)
        c.showPage()

    c.save()
    print(f"Generated Avery 22805 (1.5\"x1.5\") QR Stickers PDF: {out_path} ({total_pages} pages)")

def generate_avery22806_qr_stickers_pdf(deck_letter, songs, out_path):
    """
    Avery 22806 standard 2.0" x 2.0" square labels (12 per page, 3 cols x 4 rows):
    Left/Right margin: 0.75", Top/Bottom margin: 0.625", Col gap: 0.5", Row gap: 0.583"
    """
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter
    cols, rows = 3, 4
    size = 2.0 * inch
    margin_x = 0.75 * inch
    margin_y = 0.625 * inch
    col_gap = 0.5 * inch
    row_gap = 0.583 * inch

    per_page = cols * rows
    total_pages = (len(songs) + per_page - 1) // per_page

    for p_idx in range(total_pages):
        batch = songs[p_idx * per_page : (p_idx + 1) * per_page]
        for i, item in enumerate(batch):
            r = i // cols
            col = i % cols
            x = margin_x + col * (size + col_gap)
            y = page_h - margin_y - (r + 1) * size - r * row_gap
            draw_square_qr_sticker(c, x, y, size, item, show_cut_border=False)
        c.showPage()

    c.save()
    print(f"Generated Avery 22806 (2.0\"x2.0\") QR Stickers PDF: {out_path} ({total_pages} pages)")

# ==============================================================================
# 3. AVERY 5160 / 8160 / 18660 PAIRED BUSINESS-CARD STICKERS (2.625" x 1.0", 30-UP, 15 SONGS/PAGE)
#    + PRINT-READY BOLLYGOOD 3.5" x 2.0" MASTER BUSINESS CARD PDF (FOR VISTAPRINT / GOTPRINT / MOO)
# ==============================================================================
def draw_avery5160_qr_label(c, x, y, w, h, item):
    """
    2.625" x 1.0" label for the QR side of a pre-printed BollyGood business card.
    Compact QR code (0.82" x 0.82") on left + DECK A • #001 in bold black on right.
    No background fill (works on clear Avery 18660 or white Avery 5160 labels).
    """
    qr_size = 0.80 * inch
    qx_center = x + 0.14 * inch + qr_size / 2.0
    qy_center = y + h / 2.0
    draw_qr_widget(c, qx_center, qy_center, qr_size, item)

    tx = x + 0.14 * inch + qr_size + 0.12 * inch
    c.setFillColor(BRAND_COLOR)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawString(tx, y + h - 0.32 * inch, "BOLLYGOOD")

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12.0)
    c.drawString(tx, y + h - 0.54 * inch, f"DECK {item['deck']} • #{item['card_num']:03d}")

    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 7.2)
    c.drawString(tx, y + 0.22 * inch, "Scan QR in BollyGood App")

def draw_avery5160_answer_label(c, x, y, w, h, item):
    """
    2.625" x 1.0" label for the Answer side of a pre-printed BollyGood business card.
    Giant Year on the left (0.85" wide) + Song Title, Film/No-Film, Singers & #A-001 on the right (1.7" wide).
    Pure black text, zero background fill!
    """
    left_w = 0.84 * inch
    left_cx = x + 0.06 * inch + left_w / 2.0

    # Giant Year on left
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 22.0)
    c.drawCentredString(left_cx, y + 0.44 * inch, str(item["year"]))

    # Card ID right below year
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(left_cx, y + 0.20 * inch, f"#{item['card_label']}")

    # Thin vertical divider
    sep_x = x + 0.06 * inch + left_w + 0.04 * inch
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(0.5)
    c.line(sep_x, y + 0.12 * inch, sep_x, y + h - 0.12 * inch)

    # Right side details (1.62" wide)
    rx = sep_x + 0.06 * inch
    rw = (x + w - 0.08 * inch) - rx

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 8.8)
    title_str = truncate_text(c, item["title"], "Helvetica-Bold", 8.8, rw)
    c.drawString(rx, y + h - 0.24 * inch, title_str)

    if item.get("is_no_film"):
        c.setFont("Helvetica-Bold", 7.2)
        film_str = truncate_text(c, f"NO FILM • {item['singers']}", "Helvetica-Bold", 7.2, rw)
    else:
        c.setFont("Helvetica-BoldOblique", 7.6)
        film_str = truncate_text(c, f"Film: {item['movie']}", "Helvetica-BoldOblique", 7.6, rw)
    c.drawString(rx, y + h - 0.42 * inch, film_str)

    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 6.6)
    s_line = truncate_text(c, f"Vocal: {item['singers']}", "Helvetica", 6.6, rw)
    m_line = truncate_text(c, f"Music: {item['music_director']}", "Helvetica", 6.6, rw)
    st_line = truncate_text(c, f"Cast: {item['stars']}", "Helvetica", 6.6, rw)
    c.drawString(rx, y + h - 0.58 * inch, s_line)
    c.drawString(rx, y + h - 0.72 * inch, m_line)
    c.drawString(rx, y + h - 0.86 * inch, st_line)

def generate_avery5160_business_card_stickers_pdf(deck_letter, songs, out_path):
    """
    Avery 5160 / 8160 / 18660 standard 30-up address labels:
    3 cols x 10 rows = 30 labels per page (15 songs per page = 10 pages per 150-card deck!)
    Label size: 2.625" x 1.0"
    Top/Bottom margin: 0.5", Left/Right margin: 0.1875", Horizontal gap: 0.125", Vertical gap: 0.0"
    Each song uses 2 consecutive labels: [QR Label #A-001] + [Answer Label #A-001]
    """
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter
    cols, rows = 3, 10
    lbl_w, lbl_h = 2.625 * inch, 1.0 * inch
    margin_x = 0.1875 * inch
    margin_y = 0.5 * inch
    col_gap = 0.125 * inch

    songs_per_page = 15  # 30 labels / 2 labels per song
    total_pages = (len(songs) + songs_per_page - 1) // songs_per_page

    for p_idx in range(total_pages):
        batch = songs[p_idx * songs_per_page : (p_idx + 1) * songs_per_page]
        # Build flat list of 30 label slots: (type, item)
        slots = []
        for item in batch:
            slots.append(("QR", item))
            slots.append(("ANS", item))

        for slot_idx, (ltype, item) in enumerate(slots):
            r = slot_idx // cols
            col = slot_idx % cols
            x = margin_x + col * (lbl_w + col_gap)
            y = page_h - margin_y - (r + 1) * lbl_h
            if ltype == "QR":
                draw_avery5160_qr_label(c, x, y, lbl_w, lbl_h, item)
            else:
                draw_avery5160_answer_label(c, x, y, lbl_w, lbl_h, item)

        c.showPage()

    c.save()
    print(f"Generated Avery 5160 Business-Card Stickers PDF: {out_path} ({total_pages} pages)")

def generate_business_card_master_pdf(out_path):
    """
    Print-ready single 3.5" x 2.0" Business Card master (with 0.125" bleed -> 3.75" x 2.25" page)
    that Sri can upload to Vistaprint / GotPrint / Moo to order 300+ glossy UV-coated cards.
    Shows the crimson BOLLYGOOD header at top and a clean alignment frame below where the
    2.625" x 1.0" Avery 5160 sticker sits!
    """
    bleed = 0.125 * inch
    trim_w, trim_h = 3.5 * inch, 2.0 * inch
    page_w, page_h = trim_w + 2 * bleed, trim_h + 2 * bleed

    c = canvas.Canvas(out_path, pagesize=(page_w, page_h))

    # Outer border inside safe area
    safe_pad = bleed + 0.12 * inch
    sw = page_w - 2 * safe_pad
    sh = page_h - 2 * safe_pad
    c.setStrokeColor(BLACK)
    c.setLineWidth(1.5)
    c.roundRect(safe_pad, safe_pad, sw, sh, 8, stroke=1, fill=0)

    cx = page_w / 2.0
    # Crimson BOLLYGOOD header at top
    c.setFillColor(BRAND_COLOR)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(cx, page_h - bleed - 0.42 * inch, "BOLLYGOOD")

    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica-Bold", 7.0)
    c.drawCentredString(cx, page_h - bleed - 0.56 * inch, "THE BOLLYWOOD MUSIC TIMELINE GAME")

    # Subtle alignment frame for 2.625" x 1.0" Avery 5160/18660 sticker
    stk_w, stk_h = 2.625 * inch, 1.0 * inch
    sx = (page_w - stk_w) / 2.0
    sy = bleed + 0.20 * inch
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(0.6)
    c.setDash(3, 3)
    c.roundRect(sx, sy, stk_w, stk_h, 4, stroke=1, fill=0)
    c.setDash()

    c.showPage()
    c.save()
    print(f"Generated Master Business Card Template PDF: {out_path}")

# ==============================================================================
# 4. COMPACT 2.0" x 2.0" MINI-SQUARE DUPLEX CARDS (20 PER SHEET, 4x5 GRID)
#    & COMPACT 1.75" x 1.75" PAIRED STICKERS (10 PAIRS PER PAGE)
# ==============================================================================
def draw_compact_square_answer(c, x, y, size, item, pad_inch=0.12):
    # Outer cut guide
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(0.4)
    c.setDash(2, 2)
    c.rect(x, y, size, size, stroke=1, fill=0)
    c.setDash()

    # Generous inset padding so 2-3mm duplex shift stays cleanly inside card; fill=0 (no background fill)
    pad = pad_inch * inch
    ix, iy = x + pad, y + pad
    iw, ih = size - 2 * pad, size - 2 * pad

    c.setStrokeColor(BLACK)
    c.setLineWidth(1.2)
    c.roundRect(ix, iy, iw, ih, 6, stroke=1, fill=0)

    # Top row: BOLLYGOOD in crimson, #A-001 in black
    c.setFillColor(BRAND_COLOR)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(ix + 5, iy + ih - 0.16 * inch, "BOLLYGOOD")

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawRightString(ix + iw - 5, iy + ih - 0.16 * inch, f"#{item['card_label']}")

    c.setStrokeColor(BLACK)
    c.setLineWidth(0.5)
    c.line(ix + 4, iy + ih - 0.20 * inch, ix + iw - 4, iy + ih - 0.20 * inch)

    cx = ix + iw / 2.0

    # Giant Year
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(cx, iy + ih - 0.54 * inch, str(item["year"]))

    # Song Title
    c.setFont("Helvetica-Bold", 8.2)
    l1, l2 = wrap_two_lines(c, item["title"], "Helvetica-Bold", 8.2, iw - 10)
    if l2:
        c.drawCentredString(cx, iy + ih - 0.70 * inch, l1)
        c.drawCentredString(cx, iy + ih - 0.82 * inch, l2)
        next_y = iy + ih - 0.94 * inch
    else:
        c.drawCentredString(cx, iy + ih - 0.74 * inch, l1)
        next_y = iy + ih - 0.90 * inch

    # Film / No-Film box (fill=0)
    box_h = 0.34 * inch
    box_y = next_y - box_h + 0.03 * inch
    c.setStrokeColor(BLACK)
    c.setLineWidth(0.8)
    c.roundRect(ix + 4, box_y, iw - 8, box_h, 4, stroke=1, fill=0)

    if item.get("is_no_film"):
        c.setFillColor(DARK_GRAY)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawCentredString(cx, box_y + box_h - 0.11 * inch, "NO FILM (INDIPOP) • ARTIST:")
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 7.4)
        art_str = truncate_text(c, item["singers"], "Helvetica-Bold", 7.4, iw - 14)
        c.drawCentredString(cx, box_y + 0.07 * inch, art_str)
    else:
        c.setFillColor(DARK_GRAY)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawCentredString(cx, box_y + box_h - 0.11 * inch, "FILM:")
        c.setFillColor(BLACK)
        c.setFont("Helvetica-BoldOblique", 7.6)
        mov_str = truncate_text(c, item["movie"], "Helvetica-BoldOblique", 7.6, iw - 14)
        c.drawCentredString(cx, box_y + 0.07 * inch, mov_str)

    # Bottom metadata
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 5.6)
    s_line = truncate_text(c, f"Vocal: {item['singers']}", "Helvetica", 5.6, iw - 10)
    m_line = truncate_text(c, f"Music: {item['music_director']}", "Helvetica", 5.6, iw - 10)
    st_line = truncate_text(c, f"Cast: {item['stars']}", "Helvetica", 5.6, iw - 10)
    c.drawCentredString(cx, iy + 0.25 * inch, s_line)
    c.drawCentredString(cx, iy + 0.15 * inch, m_line)
    c.drawCentredString(cx, iy + 0.05 * inch, st_line)

def draw_compact_square_qr(c, x, y, size, item, pad_inch=0.12):
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(0.4)
    c.setDash(2, 2)
    c.rect(x, y, size, size, stroke=1, fill=0)
    c.setDash()

    pad = pad_inch * inch
    ix, iy = x + pad, y + pad
    iw, ih = size - 2 * pad, size - 2 * pad

    c.setStrokeColor(BLACK)
    c.setLineWidth(1.2)
    c.roundRect(ix, iy, iw, ih, 6, stroke=1, fill=0)

    cx = ix + iw / 2.0
    c.setFillColor(BRAND_COLOR)
    c.setFont("Helvetica-Bold", 8.2)
    c.drawCentredString(cx, iy + ih - 0.19 * inch, "BOLLYGOOD")

    qr_size = iw * 0.64
    cy = iy + ih * 0.49
    draw_qr_widget(c, cx, cy, qr_size, item)

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 7.8)
    c.drawCentredString(cx, iy + 0.10 * inch, f"DECK {item['deck']} • #{item['card_num']:03d}")

def generate_duplex_cardstock_pdf(deck_letter, songs, out_path):
    """
    Compact 2.0" x 2.0" Mini-Square Cards (4 cols x 5 rows = 20 cards per sheet, 8 sheets / 16 pages per deck)
    """
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter

    cols, rows = 4, 5
    card_size = 2.0 * inch
    grid_w = cols * card_size
    grid_h = rows * card_size
    margin_x = (page_w - grid_w) / 2.0
    margin_y = (page_h - grid_h) / 2.0

    per_page = cols * rows
    total_sheets = (len(songs) + per_page - 1) // per_page

    for sheet_idx in range(total_sheets):
        batch = songs[sheet_idx * per_page : (sheet_idx + 1) * per_page]

        # ---- ODD PAGE: FRONTS (ANSWER SIDE) ----
        c.setFillColor(DARK_GRAY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin_x, page_h - 0.30 * inch, f"BOLLYGOOD — DECK {deck_letter} MINI-SQUARE 2\"x2\" CARDSTOCK (Sheet {sheet_idx + 1}/{total_sheets} • ANSWER SIDE)")
        c.setFont("Helvetica", 7.5)
        c.drawRightString(page_w - margin_x, page_h - 0.30 * inch, "Print 2-Sided (Flip on Long Edge) at 100% Actual Size")

        for i, item in enumerate(batch):
            r = i // cols
            col = i % cols
            x = margin_x + col * card_size
            y = page_h - margin_y - (r + 1) * card_size
            draw_compact_square_answer(c, x, y, card_size, item, pad_inch=0.12)

        c.showPage()

        # ---- EVEN PAGE: BACKS (QR CODE SIDE — HORIZONTALLY MIRRORED COLUMNS) ----
        c.setFillColor(DARK_GRAY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin_x, page_h - 0.30 * inch, f"BOLLYGOOD — DECK {deck_letter} MINI-SQUARE 2\"x2\" CARDSTOCK (Sheet {sheet_idx + 1}/{total_sheets} • QR BACK — MIRRORED)")
        c.setFont("Helvetica", 7.5)
        c.drawRightString(page_w - margin_x, page_h - 0.30 * inch, "Columns Mirrored (Col 4, 3, 2, 1) to Align with Front")

        for i, item in enumerate(batch):
            r = i // cols
            col = i % cols
            mirrored_col = (cols - 1) - col
            x = margin_x + mirrored_col * card_size
            y = page_h - margin_y - (r + 1) * card_size
            draw_compact_square_qr(c, x, y, card_size, item, pad_inch=0.12)

        c.showPage()

    c.save()
    print(f"Generated Compact 2\"x2\" Duplex Cardstock PDF: {out_path} ({total_sheets * 2} pages)")

def generate_stickers_pdf(deck_letter, songs, out_path):
    """
    Paired [QR] + [Answer] 1.75" x 1.75" compact square stickers, 10 pairs per page (15 pages per deck)
    """
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter

    sticker_size = 1.75 * inch
    rows = 5
    pair_gap = 0.25 * inch
    total_w = 4 * sticker_size + pair_gap
    total_h = rows * sticker_size
    margin_x = (page_w - total_w) / 2.0
    margin_y = (page_h - total_h) / 2.0 - 0.08 * inch

    songs_per_page = 10
    total_pages = (len(songs) + songs_per_page - 1) // songs_per_page

    for p_idx in range(total_pages):
        batch = songs[p_idx * songs_per_page : (p_idx + 1) * songs_per_page]

        c.setFillColor(DARK_GRAY)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(margin_x, page_h - 0.34 * inch, f"BOLLYGOOD — DECK {deck_letter} COMPACT 1.75\" PAIRED STICKERS (Page {p_idx + 1}/{total_pages})")
        c.setFont("Helvetica", 7.5)
        c.drawRightString(page_w - margin_x, page_h - 0.34 * inch, "Each pair = [QR Sticker] + [Answer Sticker] (No Background Ink)")

        for s_i, item in enumerate(batch):
            r = s_i // 2
            pair_col = s_i % 2
            base_x = margin_x + pair_col * (2 * sticker_size + pair_gap)
            y = page_h - margin_y - (r + 1) * sticker_size - 0.15 * inch

            scale = sticker_size / (2.0 * inch)

            # Left sticker of pair: QR Side
            c.saveState()
            c.translate(base_x, y)
            c.scale(scale, scale)
            draw_compact_square_qr(c, 0, 0, 2.0 * inch, item, pad_inch=0.08)
            c.restoreState()

            # Right sticker of pair: Answer Side
            c.saveState()
            c.translate(base_x + sticker_size, y)
            c.scale(scale, scale)
            draw_compact_square_answer(c, 0, 0, 2.0 * inch, item, pad_inch=0.08)
            c.restoreState()

        c.showPage()

    c.save()
    print(f"Generated Compact 1.75\" Paired Sticker PDF: {out_path} ({total_pages} pages)")

# ==============================================================================
# 5. RULES & MASTER SONG INDEX PDF
# ==============================================================================
def generate_rules_and_index_pdf(catalog, out_path):
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter

    c.setFillColor(BRAND_COLOR)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(0.6 * inch, page_h - 0.75 * inch, "BOLLYGOOD")
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.6 * inch, page_h - 1.00 * inch, "300 Verified Bollywood & Indipop Hits (1950s–2020s) • Official House Rules & Song Index")
    c.setStrokeColor(BLACK)
    c.setLineWidth(1.2)
    c.line(0.6 * inch, page_h - 1.12 * inch, page_w - 0.6 * inch, page_h - 1.12 * inch)

    y = page_h - 1.50 * inch
    rules = [
        ("1. PARTY PHONE SETUP (BEFORE STARTING)", [
            "• Connect the iPhone to the party Bluetooth speaker and open the BollyGood Web App in Safari.",
            "• Turn on Do Not Disturb (Control Center -> Focus -> Do Not Disturb) so personal notifications never pop up.",
            "• Keep-Awake is built into the web app so the phone can sit on the table without locking."
        ]),
        ("2. TEAM SETUP", [
            "• Split into two or more teams (Deck A = 150 cards, Deck B = 150 cards).",
            "• Deal each team 1 face-up starting card to begin their chronological Timeline, plus 2 BollyGood Tokens."
        ]),
        ("3. OPPOSING TEAM SCANS & PASSES THE CARD", [
            "• On Team A's turn, Team B draws the next card and scans the QR code on the iPhone.",
            "• While Team A listens to the sample, Team B can quietly pass around the Answer side of the physical card."
        ]),
        ("4. QUALIFY FIRST (FILM + SONG, OR 'NO FILM' + ARTIST + SONG) -> THEN GUESS THE YEAR WINDOW!", [
            "• IF IT IS A FILM SONG: The guessing team MUST name both the FILM NAME and the SONG TITLE.",
            "  (Naming the playback singer/artist is fun trivia, but is NOT required and gives no extra mileage on film songs.)",
            "• IF IT IS A NO-FILM (INDIPOP) SONG: The guessing team MUST say 'NO FILM' + the ARTIST NAME + the SONG TITLE!",
            "• Getting this right QUALIFIES the team to place the card into the proper YEAR WINDOW on their timeline!",
            "• If their Year Window placement is chronologically correct (same year as an adjacent card counts on either side),",
            "  they keep the card face-up in their timeline! First team to reach 10 Timeline Cards wins!"
        ]),
        ("5. INK-SAVER BLACK & WHITE CARD & STICKER DESIGN", [
            "• All cards and stickers use zero background ink (transparent background) with pure Black text and a single crimson",
            "  'BOLLYGOOD' header—zero decade color giveaways, and works on colored cardstock or clear/white Avery labels."
        ])
    ]

    for heading, bullets in rules:
        c.setFillColor(BRAND_COLOR)
        c.setFont("Helvetica-Bold", 11.0)
        c.drawString(0.6 * inch, y, heading)
        y -= 0.22 * inch
        c.setFillColor(BLACK)
        c.setFont("Helvetica", 9.8)
        for b in bullets:
            c.drawString(0.72 * inch, y, b)
            y -= 0.19 * inch
        y -= 0.14 * inch

    c.showPage()

    per_index_page = 50
    for idx_start in range(0, len(catalog), per_index_page):
        chunk = catalog[idx_start : idx_start + per_index_page]
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.5 * inch, page_h - 0.5 * inch, f"BOLLYGOOD MASTER SONG INDEX (Cards {chunk[0]['card_label']} to {chunk[-1]['card_label']})")
        c.setFont("Helvetica-Bold", 8)
        c.drawString(0.5 * inch, page_h - 0.72 * inch, "CARD")
        c.drawString(1.05 * inch, page_h - 0.72 * inch, "YEAR")
        c.drawString(1.55 * inch, page_h - 0.72 * inch, "SONG TITLE")
        c.drawString(3.85 * inch, page_h - 0.72 * inch, "FILM / NO FILM")
        c.drawString(5.75 * inch, page_h - 0.72 * inch, "ARTIST / SINGERS")
        c.line(0.5 * inch, page_h - 0.77 * inch, page_w - 0.5 * inch, page_h - 0.77 * inch)

        ry = page_h - 0.94 * inch
        c.setFont("Helvetica", 7.8)
        for item in chunk:
            c.drawString(0.5 * inch, ry, item["card_label"])
            c.drawString(1.05 * inch, ry, str(item["year"]))
            c.drawString(1.55 * inch, ry, truncate_text(c, item["title"], "Helvetica", 7.8, 2.2 * inch))
            film_txt = "NO FILM (Indipop)" if item.get("is_no_film") else item["movie"]
            c.drawString(3.85 * inch, ry, truncate_text(c, film_txt, "Helvetica", 7.8, 1.8 * inch))
            c.drawString(5.75 * inch, ry, truncate_text(c, item["singers"], "Helvetica", 7.8, 2.2 * inch))
            ry -= 0.185 * inch
        c.showPage()

    c.save()
    print(f"Generated Rules & Master Song Index PDF: {out_path}")

deck_a = [x for x in catalog if x["deck"] == "A"]
deck_b = [x for x in catalog if x["deck"] == "B"]

# 1. Pre-Perforated Compact Cards — 1-Sided Answer Fronts (Avery 5371 / 8371 10-up, 3.5" x 2.0")
generate_avery5371_answers_pdf("A", deck_a, "/workspace/bollywood-hitster/pdfs/Deck-A-Avery5371-Answers-1Sided.pdf")
generate_avery5371_answers_pdf("B", deck_b, "/workspace/bollywood-hitster/pdfs/Deck-B-Avery5371-Answers-1Sided.pdf")

# 2. Pre-Cut Square QR-Only Stickers for Card Backs (Avery 22805 1.5"x1.5" 20-up & Avery 22806 2.0"x2.0" 12-up)
generate_avery22805_qr_stickers_pdf("A", deck_a, "/workspace/bollywood-hitster/pdfs/Deck-A-QR-Stickers-Avery22805-1.5in.pdf")
generate_avery22805_qr_stickers_pdf("B", deck_b, "/workspace/bollywood-hitster/pdfs/Deck-B-QR-Stickers-Avery22805-1.5in.pdf")
generate_avery22806_qr_stickers_pdf("A", deck_a, "/workspace/bollywood-hitster/pdfs/Deck-A-QR-Stickers-Avery22806-2in.pdf")
generate_avery22806_qr_stickers_pdf("B", deck_b, "/workspace/bollywood-hitster/pdfs/Deck-B-QR-Stickers-Avery22806-2in.pdf")

# 3. Business-Card Sticker Set (Avery 5160 / 8160 / 18660 30-up, 2.625" x 1.0", 15 songs/page) + Master Business Card
generate_avery5160_business_card_stickers_pdf("A", deck_a, "/workspace/bollywood-hitster/pdfs/Deck-A-BusinessCard-Stickers-Avery5160.pdf")
generate_avery5160_business_card_stickers_pdf("B", deck_b, "/workspace/bollywood-hitster/pdfs/Deck-B-BusinessCard-Stickers-Avery5160.pdf")
generate_business_card_master_pdf("/workspace/bollywood-hitster/pdfs/BollyGood-BusinessCard-Master-3.5x2.pdf")

# 4. Compact 2.0" x 2.0" Mini-Square Duplex Cards (20 per sheet) & Paired 1.75" Square Stickers
generate_duplex_cardstock_pdf("A", deck_a, "/workspace/bollywood-hitster/pdfs/Deck-A-Cardstock-Duplex.pdf")
generate_duplex_cardstock_pdf("B", deck_b, "/workspace/bollywood-hitster/pdfs/Deck-B-Cardstock-Duplex.pdf")
generate_stickers_pdf("A", deck_a, "/workspace/bollywood-hitster/pdfs/Deck-A-Stickers.pdf")
generate_stickers_pdf("B", deck_b, "/workspace/bollywood-hitster/pdfs/Deck-B-Stickers.pdf")

# 5. Rules & Song Index PDFs
rules_path_1 = "/workspace/bollywood-hitster/pdfs/Bollywood-Hitster-Rules-and-Song-Index.pdf"
rules_path_2 = "/workspace/bollywood-hitster/pdfs/BollyGood-Rules-and-Song-Index.pdf"
generate_rules_and_index_pdf(catalog, rules_path_1)
shutil.copyfile(rules_path_1, rules_path_2)
print(f"Copied Rules PDF to: {rules_path_2}")
