import os
import json
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

DECADE_COLORS = {
    "1950s": colors.HexColor("#b5651d"),
    "1960s": colors.HexColor("#d97706"),
    "1970s": colors.HexColor("#e11d48"),
    "1980s": colors.HexColor("#9333ea"),
    "1990s": colors.HexColor("#2563eb"),
    "2000s": colors.HexColor("#059669"),
    "2010s": colors.HexColor("#0891b2"),
    "2020s": colors.HexColor("#db2777"),
}

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

def draw_answer_card(c, x, y, size, item):
    dec_color = DECADE_COLORS.get(item["decade"], colors.HexColor("#4f46e5"))

    # Outer cut border (light dashed gray)
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.6)
    c.setDash(3, 3)
    c.rect(x, y, size, size, stroke=1, fill=0)
    c.setDash()

    # Inner card frame
    pad = 0.08 * inch
    ix, iy = x + pad, y + pad
    iw, ih = size - 2 * pad, size - 2 * pad

    c.setFillColor(colors.HexColor("#130b20"))
    c.setStrokeColor(dec_color)
    c.setLineWidth(2.2)
    c.roundRect(ix, iy, iw, ih, 8, stroke=1, fill=1)

    # Top header band
    band_h = 0.28 * inch
    c.setFillColor(dec_color)
    c.roundRect(ix, iy + ih - band_h, iw, band_h, 6, stroke=0, fill=1)
    c.rect(ix, iy + ih - band_h, iw, band_h / 2, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(ix + 7, iy + ih - 0.19 * inch, f"CARD {item['card_label']}")
    c.drawRightString(ix + iw - 7, iy + ih - 0.19 * inch, item["decade"])

    cx = ix + iw / 2.0

    # Giant Release Year
    c.setFillColor(colors.HexColor("#ffd166"))
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(cx, iy + ih - 0.72 * inch, str(item["year"]))

    # Song Title (1 or 2 lines)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10.5)
    l1, l2 = wrap_two_lines(c, item["title"], "Helvetica-Bold", 10.5, iw - 14)
    if l2:
        c.drawCentredString(cx, iy + ih - 0.94 * inch, l1)
        c.drawCentredString(cx, iy + ih - 1.10 * inch, l2)
        next_y = iy + ih - 1.24 * inch
    else:
        c.drawCentredString(cx, iy + ih - 0.99 * inch, l1)
        next_y = iy + ih - 1.18 * inch

    # Highlighted Qualification Box (Film vs No-Film + Artist)
    box_h = 0.48 * inch
    box_y = next_y - box_h + 0.05 * inch
    if item.get("is_no_film"):
        c.setFillColor(colors.HexColor("#3b1d08"))
        c.setStrokeColor(colors.HexColor("#ff9f1c"))
        c.setLineWidth(1.2)
        c.roundRect(ix + 6, box_y, iw - 12, box_h, 5, stroke=1, fill=1)

        c.setFillColor(colors.HexColor("#ff9f1c"))
        c.setFont("Helvetica-Bold", 7.2)
        c.drawCentredString(cx, box_y + box_h - 0.14 * inch, "NO FILM (INDIPOP) • MUST NAME ARTIST:")

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9.5)
        art_str = truncate_text(c, item["singers"], "Helvetica-Bold", 9.5, iw - 20)
        c.drawCentredString(cx, box_y + 0.10 * inch, art_str)
    else:
        c.setFillColor(colors.HexColor("#0c2930"))
        c.setStrokeColor(colors.HexColor("#00f5d4"))
        c.setLineWidth(1.0)
        c.roundRect(ix + 6, box_y, iw - 12, box_h, 5, stroke=1, fill=1)

        c.setFillColor(colors.HexColor("#00f5d4"))
        c.setFont("Helvetica-Bold", 7.0)
        c.drawCentredString(cx, box_y + box_h - 0.14 * inch, "FILM (REQUIRED WITH SONG TITLE):")

        c.setFillColor(colors.white)
        c.setFont("Helvetica-BoldOblique", 9.8)
        mov_str = truncate_text(c, item["movie"], "Helvetica-BoldOblique", 9.8, iw - 20)
        c.drawCentredString(cx, box_y + 0.10 * inch, mov_str)

    # Bottom Trivia Metadata (Singers, Music Director, Stars)
    meta_y = iy + 0.34 * inch
    c.setFillColor(colors.HexColor("#cbd5e1"))
    c.setFont("Helvetica", 6.8)
    s_line = truncate_text(c, f"Vocal: {item['singers']}", "Helvetica", 6.8, iw - 14)
    m_line = truncate_text(c, f"Music: {item['music_director']}", "Helvetica", 6.8, iw - 14)
    st_line = truncate_text(c, f"Cast: {item['stars']}", "Helvetica", 6.8, iw - 14)
    c.drawCentredString(cx, meta_y, s_line)
    c.drawCentredString(cx, meta_y - 0.12 * inch, m_line)
    c.drawCentredString(cx, meta_y - 0.24 * inch, st_line)

def draw_qr_card(c, x, y, size, item):
    # Outer cut border
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.6)
    c.setDash(3, 3)
    c.rect(x, y, size, size, stroke=1, fill=0)
    c.setDash()

    pad = 0.08 * inch
    ix, iy = x + pad, y + pad
    iw, ih = size - 2 * pad, size - 2 * pad

    c.setFillColor(colors.HexColor("#0d0814"))
    c.setStrokeColor(colors.HexColor("#ffd166"))
    c.setLineWidth(1.8)
    c.roundRect(ix, iy, iw, ih, 8, stroke=1, fill=1)

    cx = ix + iw / 2.0
    cy = iy + ih / 2.0 + 0.04 * inch

    # Decorative Bollywood vinyl grooves around QR
    c.setStrokeColor(colors.HexColor("#2d1942"))
    c.setLineWidth(1.0)
    c.circle(cx, cy, 0.92 * inch, stroke=1, fill=0)
    c.setStrokeColor(colors.HexColor("#ff2a85"))
    c.setLineWidth(0.7)
    c.circle(cx, cy, 0.85 * inch, stroke=1, fill=0)

    # Top title
    c.setFillColor(colors.HexColor("#ffd166"))
    c.setFont("Helvetica-Bold", 8.2)
    c.drawCentredString(cx, iy + ih - 0.21 * inch, "BOLLYWOOD HITSTER")

    # White QR container in center
    qr_box = 1.32 * inch
    qx = cx - qr_box / 2.0
    qy = cy - qr_box / 2.0
    c.setFillColor(colors.white)
    c.roundRect(qx, qy, qr_box, qr_box, 6, stroke=0, fill=1)

    # QR Code encoding card ID + Spotify ID for universal scanning
    qr_payload = f"https://sripartha.github.io/bollywood-hitster/?card={item['card_id']}&sp={item['spotify_id']}"
    qr_widget = QrCodeWidget(qr_payload, barLevel="M")
    bounds = qr_widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    d = Drawing(qr_box - 8, qr_box - 8, transform=[(qr_box - 8) / w, 0, 0, (qr_box - 8) / h, 0, 0])
    d.add(qr_widget)
    renderPDF.draw(d, c, qx + 4, qy + 4)

    # Bottom Card ID badge (no year/decade spoilers!)
    c.setFillColor(colors.HexColor("#00f5d4"))
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(cx, iy + 0.21 * inch, f"DECK {item['deck']}  •  #{item['card_num']:03d}")
    c.setFillColor(colors.HexColor("#b5a8c9"))
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(cx, iy + 0.08 * inch, "Scan QR or Type Card # in App")

def generate_duplex_cardstock_pdf(deck_letter, songs, out_path):
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter  # 8.5 x 11 inches

    cols, rows = 3, 4
    card_size = 2.5 * inch
    grid_w = cols * card_size  # 7.5"
    grid_h = rows * card_size  # 10.0"
    margin_x = (page_w - grid_w) / 2.0  # 0.5"
    margin_y = (page_h - grid_h) / 2.0  # 0.5"

    per_page = cols * rows  # 12 cards per sheet
    total_sheets = (len(songs) + per_page - 1) // per_page

    for sheet_idx in range(total_sheets):
        batch = songs[sheet_idx * per_page : (sheet_idx + 1) * per_page]

        # ---- ODD PAGE: FRONTS (DATA / ANSWER SIDE) ----
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin_x, page_h - 0.32 * inch, f"BOLLYWOOD HITSTER — DECK {deck_letter} CARDSTOCK (Sheet {sheet_idx + 1}/{total_sheets} • ANSWER SIDE)")
        c.setFont("Helvetica", 7.5)
        c.drawRightString(page_w - margin_x, page_h - 0.32 * inch, "Print 2-Sided (Flip on Long Edge) at 100% Actual Size")

        for i, item in enumerate(batch):
            r = i // cols
            col = i % cols
            x = margin_x + col * card_size
            y = page_h - margin_y - (r + 1) * card_size
            draw_answer_card(c, x, y, card_size, item)

        c.showPage()

        # ---- EVEN PAGE: BACKS (QR CODE SIDE — HORIZONTALLY MIRRORED COLUMNS) ----
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin_x, page_h - 0.32 * inch, f"BOLLYWOOD HITSTER — DECK {deck_letter} CARDSTOCK (Sheet {sheet_idx + 1}/{total_sheets} • QR BACK SIDE — MIRRORED FOR DUPLEX)")
        c.setFont("Helvetica", 7.5)
        c.drawRightString(page_w - margin_x, page_h - 0.32 * inch, "Columns Mirrored (Col 3, 2, 1) to Align with Front")

        for i, item in enumerate(batch):
            r = i // cols
            col = i % cols
            mirrored_col = (cols - 1) - col  # Flip horizontally so back matches front!
            x = margin_x + mirrored_col * card_size
            y = page_h - margin_y - (r + 1) * card_size
            draw_qr_card(c, x, y, card_size, item)

        c.showPage()

    c.save()
    print(f"Generated Duplex Cardstock PDF: {out_path} ({total_sheets * 2} pages)")

def generate_stickers_pdf(deck_letter, songs, out_path):
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter

    # Side-by-side paired sticker layout:
    # 2 song pairs per row x 3 rows = 6 songs (12 square 2.0"x2.0" stickers) per page!
    # Wait: let's see if 4 columns of 1.9" x 1.9" fits 2 pairs per row x 5 rows = 10 songs (20 stickers) per page!
    # 4 * 1.9" = 7.6" width; 5 * 1.9" = 9.5" height -> 10 songs per page = 15 pages per 150-card deck!
    sticker_size = 1.92 * inch
    cols, rows = 4, 5  # 2 pairs per row, 5 rows = 10 songs per page
    pair_gap = 0.18 * inch
    total_w = 4 * sticker_size + pair_gap
    total_h = rows * sticker_size
    margin_x = (page_w - total_w) / 2.0
    margin_y = (page_h - total_h) / 2.0 - 0.08 * inch

    songs_per_page = 10
    total_pages = (len(songs) + songs_per_page - 1) // songs_per_page

    for p_idx in range(total_pages):
        batch = songs[p_idx * songs_per_page : (p_idx + 1) * songs_per_page]

        c.setFillColor(colors.HexColor("#1e293b"))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(margin_x, page_h - 0.34 * inch, f"BOLLYWOOD HITSTER — DECK {deck_letter} PAIRED STICKER SHEET (Page {p_idx + 1}/{total_pages})")
        c.setFont("Helvetica", 7.5)
        c.drawRightString(page_w - margin_x, page_h - 0.34 * inch, "Each pair = [QR Front Sticker] + [Answer Back Sticker] for the same card!")

        for s_i, item in enumerate(batch):
            r = s_i // 2
            pair_col = s_i % 2  # 0 = left pair, 1 = right pair
            base_x = margin_x + pair_col * (2 * sticker_size + pair_gap)
            y = page_h - margin_y - (r + 1) * sticker_size - 0.15 * inch

            # Scale factor for 1.92" sticker vs 2.5" card
            scale = sticker_size / (2.5 * inch)

            # Left sticker of pair: QR Side
            c.saveState()
            c.translate(base_x, y)
            c.scale(scale, scale)
            draw_qr_card(c, 0, 0, 2.5 * inch, item)
            c.restoreState()

            # Right sticker of pair: Answer Side
            c.saveState()
            c.translate(base_x + sticker_size, y)
            c.scale(scale, scale)
            draw_answer_card(c, 0, 0, 2.5 * inch, item)
            c.restoreState()

        c.showPage()

    c.save()
    print(f"Generated Paired Sticker PDF: {out_path} ({total_pages} pages)")

def generate_rules_and_index_pdf(catalog, out_path):
    c = canvas.Canvas(out_path, pagesize=letter)
    page_w, page_h = letter

    # Page 1: Party Rules & Host Guide
    c.setFillColor(colors.HexColor("#0d0814"))
    c.rect(0, page_h - 1.3 * inch, page_w, 1.3 * inch, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#ffd166"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(0.6 * inch, page_h - 0.72 * inch, "BOLLYWOOD HITSTER — PARTY EDITION")
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 11)
    c.drawString(0.6 * inch, page_h - 1.0 * inch, "300 Verified Spotify Hits (1950s–2020s) • Official House Rules & Print Guide")

    y = page_h - 1.75 * inch
    rules = [
        ("1. PARTY PHONE SETUP (BEFORE STARTING)", [
            "• Connect the iPhone to the party Bluetooth speaker and open the Bollywood Hitster Web App in Safari.",
            "• Turn on Do Not Disturb (Control Center -> Focus -> Do Not Disturb) so personal notifications never pop up.",
            "• Keep-Awake is built into the web app so the phone can be passed around or sit on a stand without locking."
        ]),
        ("2. TEAM SETUP", [
            "• Split into two or more teams (Deck A = 150 cards, Deck B = 150 cards).",
            "• Deal each team 1 face-up starting card to begin their chronological Timeline, plus 2 Hitster Tokens."
        ]),
        ("3. OPPOSING TEAM SCANS & PASSES THE CARD", [
            "• On Team A's turn, Team B draws the next card and scans the QR code (or types the 3-digit Card #) on the iPhone.",
            "• The web app immediately plays Spotify's 30-second representative hook sampler over Bluetooth!",
            "• While Team A listens, Team B can quietly pass around the Data/Answer side of the physical card amongst themselves."
        ]),
        ("4. QUALIFY FIRST (FILM + SONG, OR 'NO FILM' + ARTIST + SONG) -> THEN GUESS THE YEAR WINDOW!", [
            "• IF IT IS A FILM SONG: The guessing team MUST name both the FILM NAME and the SONG TITLE.",
            "  (Naming the playback singer/artist is fun trivia, but is NOT required and gives no extra mileage on film songs.)",
            "• IF IT IS A NO-FILM (INDIPOP) SONG: The guessing team MUST say 'NO FILM' + the ARTIST NAME + the SONG TITLE!",
            "• Getting this right QUALIFIES the team to place the card into the proper YEAR WINDOW on their timeline!",
            "• If their Year Window placement is chronologically correct (same year as an adjacent card counts on either side),",
            "  they keep the card face-up in their timeline! First team to reach 10 Timeline Cards wins!"
        ]),
        ("5. PRINTING GUIDE (CARDSTOCK VS. STICKERS)", [
            "• 2-Sided Cardstock (Deck-A/B-Cardstock-Duplex.pdf): Print on 8.5\"x11\" US Letter cardstock at 100% Actual Size,",
            "  2-Sided (Flip on Long Edge). Even pages are horizontally mirrored so every QR back aligns with its Answer front!",
            "• Sticker Sheets (Deck-A/B-Stickers.pdf): Each card's QR sticker and Answer sticker sit right next to each other",
            "  with matching Card IDs (e.g., A-001) so you can peel and stick them onto blank playing/index cards effortlessly."
        ])
    ]

    for heading, bullets in rules:
        c.setFillColor(colors.HexColor("#7e22ce"))
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(0.6 * inch, y, heading)
        y -= 0.22 * inch
        c.setFillColor(colors.HexColor("#1e293b"))
        c.setFont("Helvetica", 9.8)
        for b in bullets:
            c.drawString(0.72 * inch, y, b)
            y -= 0.19 * inch
        y -= 0.14 * inch

    c.showPage()

    # Subsequent pages: Master 300-Song Index
    per_index_page = 50
    for idx_start in range(0, len(catalog), per_index_page):
        chunk = catalog[idx_start : idx_start + per_index_page]
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.5 * inch, page_h - 0.5 * inch, f"MASTER VERIFIED SONG INDEX (Cards {chunk[0]['card_label']} to {chunk[-1]['card_label']})")
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

generate_duplex_cardstock_pdf("A", deck_a, "/workspace/bollywood-hitster/pdfs/Deck-A-Cardstock-Duplex.pdf")
generate_duplex_cardstock_pdf("B", deck_b, "/workspace/bollywood-hitster/pdfs/Deck-B-Cardstock-Duplex.pdf")
generate_stickers_pdf("A", deck_a, "/workspace/bollywood-hitster/pdfs/Deck-A-Stickers.pdf")
generate_stickers_pdf("B", deck_b, "/workspace/bollywood-hitster/pdfs/Deck-B-Stickers.pdf")
generate_rules_and_index_pdf(catalog, "/workspace/bollywood-hitster/pdfs/Bollywood-Hitster-Rules-and-Song-Index.pdf")
