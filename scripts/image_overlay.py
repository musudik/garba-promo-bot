"""
Generates branded square graphics for recurring, data-driven post types
(countdown, "selling fast", early bird, sponsor spotlight, food stalls,
sponsorship call-for-partners) WITHOUT any AI image generation — just
Pillow drawing a fixed template with dynamic text plugged in.

This keeps every post visually consistent and on-brand automatically,
and needs zero new design work per post. Swap in a real photo as the
background any time by passing background_photo=<path>.
"""
import os
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")

# Brand palette pulled from the event flyer (black + gold)
BG_TOP = (12, 10, 8)
BG_BOTTOM = (28, 22, 15)
GOLD = (212, 168, 60)
WHITE = (245, 245, 245)
SIZE = (1080, 1080)


def _fitted_font(draw, text, font_path, max_width, start_size, min_size=28):
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            return font
        size -= 4
    return ImageFont.truetype(font_path, min_size)


def _vertical_gradient(size, top_color, bottom_color):
    img = Image.new("RGB", size, top_color)
    draw = ImageDraw.Draw(img)
    h = size[1]
    for y in range(h):
        t = y / h
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    return img


def render_post_image(
    label: str,
    big_text: str,
    subtext: str,
    footer: str,
    output_path: str,
    background_photo: str = None,
):
    """
    label:      small caps tag at top, e.g. "COUNTDOWN", "EARLY BIRD"
    big_text:   large centered headline, e.g. "45 DAYS TO GO", "SELLING FAST"
    subtext:    supporting line below, e.g. "Apexa Pandya Live in Concert"
    footer:     bottom strip, e.g. "25 OCT 2026 · #GarbaGermany"
    background_photo: optional path to a real photo to use as backdrop
                       instead of the plain gradient (photo gets a dark
                       overlay so text stays readable)
    """
    if background_photo and os.path.isfile(background_photo):
        img = Image.open(background_photo).convert("RGB")
        img = img.resize(SIZE)
        overlay = Image.new("RGB", SIZE, (0, 0, 0))
        img = Image.blend(img, overlay, alpha=0.55)
    else:
        img = _vertical_gradient(SIZE, BG_TOP, BG_BOTTOM)

    draw = ImageDraw.Draw(img)
    w, h = SIZE
    margin = 70

    # Gold border frame
    draw.rectangle([margin // 2, margin // 2, w - margin // 2, h - margin // 2], outline=GOLD, width=4)

    # Top brand strip
    brand_font = ImageFont.truetype(FONT_BOLD, 34)
    draw.text((margin, margin), "FUSION4EVENTS", font=brand_font, fill=GOLD)

    # Label pill
    label_font = ImageFont.truetype(FONT_BOLD, 40)
    label_text = label.upper()
    lb = draw.textbbox((0, 0), label_text, font=label_font)
    lw, lh = lb[2] - lb[0], lb[3] - lb[1]
    pill_x0, pill_y0 = (w - lw) // 2 - 30, 175
    pill_x1, pill_y1 = (w + lw) // 2 + 30, 175 + lh + 30
    draw.rounded_rectangle([pill_x0, pill_y0, pill_x1, pill_y1], radius=30, fill=GOLD)
    draw.text(((w - lw) // 2, pill_y0 + 12), label_text, font=label_font, fill=(20, 15, 10))

    # Big headline, auto-fit width
    max_text_width = w - 2 * margin - 40
    big_font = _fitted_font(draw, big_text, FONT_BOLD, max_text_width, start_size=140, min_size=48)
    bb = draw.textbbox((0, 0), big_text, font=big_font)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    by = (h - bh) // 2 - 20
    draw.text(((w - bw) // 2, by), big_text, font=big_font, fill=WHITE)

    # Subtext
    sub_font = _fitted_font(draw, subtext, FONT_REGULAR, max_text_width, start_size=44, min_size=26)
    sb = draw.textbbox((0, 0), subtext, font=sub_font)
    sw = sb[2] - sb[0]
    draw.text(((w - sw) // 2, by + bh + 40), subtext, font=sub_font, fill=GOLD)

    # Footer strip
    footer_font = ImageFont.truetype(FONT_REGULAR, 30)
    fb = draw.textbbox((0, 0), footer, font=footer_font)
    fw = fb[2] - fb[0]
    draw.text(((w - fw) // 2, h - margin - 40), footer, font=footer_font, fill=WHITE)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, quality=92)
    return output_path
