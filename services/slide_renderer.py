from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import ASSETS_DIR, PAGE_URL, VIDEO_HEIGHT, VIDEO_WIDTH

# Bundled fonts make GitHub Actions rendering deterministic.
FONT_REGULAR = ASSETS_DIR / "fonts" / "DejaVuSans.ttf"
FONT_BOLD = ASSETS_DIR / "fonts" / "DejaVuSans-Bold.ttf"
FONT_HINDI = ASSETS_DIR / "fonts" / "NotoSansDevanagari-Regular.ttf"
FONT_HINDI_BOLD = ASSETS_DIR / "fonts" / "NotoSansDevanagari-Regular.ttf"

SYSTEM_FONT_REGULARS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]
SYSTEM_FONT_BOLDS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
SYSTEM_FONT_HINDI = [
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagariUI-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.ttf",
]

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F\u1CD0-\u1CFF\uA8E0-\uA8FF]")
BYLINE = "By Nitin Mittal Innovations"


def _contains_hindi(text):
    return bool(DEVANAGARI_RE.search(str(text or "")))


def _first_existing(paths):
    for path in paths:
        path = Path(path)
        if path.exists():
            return path
    return None


def _font(size, bold=False, hindi=False):
    size = max(10, int(size))
    if hindi:
        path = _first_existing([FONT_HINDI_BOLD if bold else FONT_HINDI, *SYSTEM_FONT_HINDI])
    else:
        path = _first_existing([
            FONT_BOLD if bold else FONT_REGULAR,
            *(SYSTEM_FONT_BOLDS if bold else SYSTEM_FONT_REGULARS),
        ])
    if path:
        try:
            return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
        except Exception:
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _gradient():
    top = (2, 13, 24)
    bottom = (10, 42, 67)
    strip = Image.new("RGB", (1, VIDEO_HEIGHT))
    pixels = strip.load()
    for y in range(VIDEO_HEIGHT):
        t = y / max(1, VIDEO_HEIGHT - 1)
        pixels[0, y] = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
    return strip.resize((VIDEO_WIDTH, VIDEO_HEIGHT))


_BACKGROUND = None
_LOGO = None


def _base_canvas():
    global _BACKGROUND
    if _BACKGROUND is None:
        _BACKGROUND = _gradient()
    return _BACKGROUND.copy()


def _logo():
    """Create a genuinely circular logo without distorting the source artwork."""
    global _LOGO
    if _LOGO is not None:
        return _LOGO

    logo_path = ASSETS_DIR / "logo.png"
    source = Image.open(logo_path).convert("RGBA")

    # The supplied artwork contains a large white canvas around the actual
    # circular Smart Learning Lab mark. Crop that whitespace first so the mark
    # stays proportional instead of stretching the original 451x375 image.
    crop = source.crop((90, 25, 380, 315))
    crop.thumbnail((204, 204), Image.Resampling.LANCZOS)

    badge_size = 230
    badge = Image.new("RGBA", (badge_size, badge_size), (0, 0, 0, 0))

    # Subtle shadow for separation from the dark video background.
    shadow = Image.new("RGBA", (badge_size, badge_size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse((8, 10, badge_size - 2, badge_size - 2), fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    badge.alpha_composite(shadow)

    # Clean white circular badge.
    mask = Image.new("L", (badge_size, badge_size), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, badge_size - 2, badge_size - 2), fill=255)
    white_circle = Image.new("RGBA", (badge_size, badge_size), (255, 255, 255, 255))
    white_circle.putalpha(mask)
    badge.alpha_composite(white_circle)

    x = (badge_size - crop.width) // 2
    y = (badge_size - crop.height) // 2
    crop_mask = Image.new("L", crop.size, 0)
    ImageDraw.Draw(crop_mask).ellipse((0, 0, crop.width - 1, crop.height - 1), fill=255)
    crop.putalpha(crop_mask)
    badge.alpha_composite(crop, (x, y))

    _LOGO = badge
    return _LOGO


def _question_parts(q):
    data = q.get("question", "")
    if isinstance(data, dict):
        return str(data.get("en", "")).strip(), str(data.get("hi", "")).strip()
    return str(data).strip(), ""


def _option_parts(option):
    if isinstance(option, dict):
        return str(option.get("en", "")).strip(), str(option.get("hi", "")).strip()
    return str(option).strip(), ""


def _clean_display_text(text):
    text = str(text or "").replace("\r", "").strip()
    # Avoid tofu from unsupported emoji in the bundled educational fonts.
    text = text.replace("💡", "Explanation:")
    return text


def _char_is_devanagari(ch):
    return bool(DEVANAGARI_RE.match(ch))


def _script_runs(text):
    """Split mixed Hindi/English text so every character uses a safe font."""
    text = _clean_display_text(text)
    if not text:
        return []

    runs = []
    current = ""
    current_hindi = None

    def flush():
        nonlocal current
        if current:
            runs.append((current, bool(current_hindi)))
            current = ""

    for ch in text:
        if ch.isspace():
            current += ch
            continue
        is_hindi = _char_is_devanagari(ch)
        if current_hindi is None:
            current_hindi = is_hindi
        elif is_hindi != current_hindi:
            flush()
            current_hindi = is_hindi
        current += ch

    flush()
    return runs


def _text_width(draw, text, size, bold=False, force_hindi=None):
    text = _clean_display_text(text)
    if not text:
        return 0
    if force_hindi is not None:
        font = _font(size, bold=bold, hindi=force_hindi)
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]

    return int(round(sum(
        draw.textlength(run, font=_font(size, bold=bold, hindi=is_hindi))
        for run, is_hindi in _script_runs(text)
    )))


def _wrap_lines(draw, text, size, max_width, bold=False, force_hindi=None):
    text = _clean_display_text(text)
    if not text:
        return []

    words = re.findall(r"\S+|\s+", text)
    lines = []
    line = ""

    def width(value):
        return _text_width(draw, value, size, bold=bold, force_hindi=force_hindi)

    for token in words:
        if token.isspace():
            if line:
                line += " "
            continue

        candidate = token if not line else f"{line.rstrip()} {token}"
        if width(candidate) <= max_width:
            line = candidate
            continue

        if line.strip():
            lines.append(line.strip())
            line = ""

        if width(token) <= max_width:
            line = token
            continue

        chunk = ""
        for char in token:
            candidate = chunk + char
            if chunk and width(candidate) > max_width:
                lines.append(chunk)
                chunk = char
            else:
                chunk = candidate
        line = chunk

    if line.strip():
        lines.append(line.strip())
    return lines


def _draw_mixed_line(draw, text, y, box, size, fill, bold=False, align="center", force_hindi=None):
    left, _, right, _ = box
    text = _clean_display_text(text)
    if not text:
        return

    runs = [(text, force_hindi)] if force_hindi is not None else _script_runs(text)
    metrics = []
    total_width = 0
    for run, is_hindi in runs:
        font = _font(size, bold=bold, hindi=bool(is_hindi))
        width = draw.textlength(run, font=font)
        bbox = draw.textbbox((0, 0), run, font=font)
        metrics.append((run, font, width, bbox))
        total_width += width

    if align == "left":
        x = left
    elif align == "right":
        x = right - total_width
    else:
        x = left + ((right - left) - total_width) / 2

    # Common baseline prevents Hindi matras and Latin glyphs from appearing
    # vertically misaligned in the same sentence.
    baseline = y + max(bbox[3] for _, _, _, bbox in metrics)
    for run, font, width, bbox in metrics:
        draw_y = baseline - bbox[3]
        draw.text((x, draw_y), run, font=font, fill=fill)
        x += width


def _draw_wrapped(draw, text, size, box, fill, bold=False, line_gap=8, align="center", force_hindi=None):
    left, top, right, bottom = box
    lines = _wrap_lines(draw, text, size, max(1, right - left), bold=bold, force_hindi=force_hindi)
    line_height = max(1, int(size * 1.18))
    y = top
    for item in lines:
        if y + line_height > bottom:
            break
        _draw_mixed_line(draw, item, y, box, size, fill, bold=bold, align=align, force_hindi=force_hindi)
        y += line_height + line_gap
    return min(y, bottom)


def _draw_wrapped_fit(draw, text, box, fill, start_size, min_size, bold=False, hindi=None, line_gap=8, align="center"):
    left, top, right, bottom = box
    force_hindi = hindi
    for size in range(int(start_size), int(min_size) - 1, -1):
        lines = _wrap_lines(draw, text, size, right - left, bold=bold, force_hindi=force_hindi)
        line_height = max(1, int(size * 1.18))
        needed = len(lines) * line_height + max(0, len(lines) - 1) * line_gap
        if needed <= bottom - top:
            y = top
            for item in lines:
                _draw_mixed_line(draw, item, y, box, size, fill, bold=bold, align=align, force_hindi=force_hindi)
                y += line_height + line_gap
            return y
    return _draw_wrapped(draw, text, int(min_size), box, fill, bold=bold, line_gap=line_gap, align=align, force_hindi=force_hindi)


def _draw_logo_center(image, y):
    logo = _logo()
    x = (VIDEO_WIDTH - logo.width) // 2
    image.alpha_composite(logo, (x, y))
    return y + logo.height


def _draw_byline(draw, y, size=22):
    draw.text(
        (VIDEO_WIDTH // 2, y),
        BYLINE,
        font=_font(size, bold=True),
        fill=(185, 207, 225, 255),
        anchor="mm",
    )


def _draw_option(draw, y, index, en_opt, hi_opt, height=132, correct=False):
    box = (70, y, VIDEO_WIDTH - 70, y + height)
    # Use fully opaque fills because the final slide is exported to JPEG;
    # semi-transparent RGBA fills would lose their intended compositing and
    # appear as white boxes after RGB conversion.
    fill = (0, 214, 142) if correct else (18, 43, 62)
    outline = (0, 255, 157) if correct else (0, 195, 255)
    draw.rounded_rectangle(box, radius=16, fill=fill, outline=outline, width=2)

    text_fill = "black" if correct else "white"
    hi_fill = "#1a1a1a" if correct else "#b3d9ff"

    _draw_wrapped_fit(
        draw, f"{chr(65 + index)}. {en_opt}",
        (105, y + 13, VIDEO_WIDTH - 105, y + 59), text_fill,
        start_size=29, min_size=22, bold=correct, line_gap=1, align="left", hindi=False,
    )

    # Some source records repeat the English option in the `hi` field. Do not
    # print the same answer twice; only show a Hindi line when it adds content.
    show_hi = hi_opt and hi_opt.strip().casefold() != en_opt.strip().casefold()
    if show_hi:
        _draw_wrapped_fit(
            draw, hi_opt,
            (105, y + 63, VIDEO_WIDTH - 105, y + height - 10), hi_fill,
            start_size=21, min_size=15, line_gap=1, align="left", hindi=None,
        )
    return y + height


def render_question(q, index, timer, output):
    image = _base_canvas().convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")

    _draw_logo_center(image, 115)
    draw.text((VIDEO_WIDTH // 2, 385), str(timer), font=_font(74, bold=True), fill=(255, 204, 0), anchor="mm")

    en, hi = _question_parts(q)
    y = 470
    y = _draw_wrapped_fit(
        draw, f"Q{index + 1}. {en}",
        (65, y, VIDEO_WIDTH - 65, 755), "white",
        start_size=48, min_size=36, bold=True, line_gap=7, hindi=False,
    )
    if hi:
        y += 8
        y = _draw_wrapped_fit(
            draw, hi,
            (75, y, VIDEO_WIDTH - 75, 875), "#cce6ff",
            start_size=31, min_size=22, line_gap=5, hindi=None,
        )

    options = q.get("options", [])[:4]
    option_height = 132
    option_gap = 14
    total_options_height = len(options) * option_height + max(0, len(options) - 1) * option_gap
    footer_y = 1815
    option_start = max(950, int(y + 25))
    max_start = footer_y - total_options_height - 55
    option_start = min(option_start, max_start)

    oy = option_start
    for i, option in enumerate(options):
        en_opt, hi_opt = _option_parts(option)
        _draw_option(draw, oy, i, en_opt, hi_opt, height=option_height, correct=False)
        oy += option_height + option_gap

    draw.text(
        (VIDEO_WIDTH // 2, footer_y),
        "Comment your answer!",
        font=_font(26, bold=True),
        fill="#00ff9d",
        anchor="mm",
    )
    image.convert("RGB").save(output, quality=92, optimize=True)


def render_answer(q, index, output):
    image = _base_canvas().convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")

    _draw_logo_center(image, 75)

    en, hi = _question_parts(q)
    y = 335
    y = _draw_wrapped_fit(
        draw, f"Q{index + 1}. {en}",
        (65, y, VIDEO_WIDTH - 65, 575), "white",
        start_size=43, min_size=32, bold=True, line_gap=6, hindi=False,
    )
    if hi:
        y += 7
        y = _draw_wrapped_fit(
            draw, hi,
            (75, y, VIDEO_WIDTH - 75, 675), "#cce6ff",
            start_size=28, min_size=20, line_gap=4, hindi=None,
        )

    options = q.get("options", [])[:4]
    option_height = 112
    option_gap = 10
    footer_y = 1810
    footer_reserve = 90
    explanation_reserve = 245 if q.get("explanation") else 35
    options_total = len(options) * option_height + max(0, len(options) - 1) * option_gap
    option_start = max(710, int(y + 18))
    max_option_start = footer_y - footer_reserve - explanation_reserve - options_total
    option_start = min(option_start, max_option_start)

    oy = option_start
    for i, option in enumerate(options):
        en_opt, hi_opt = _option_parts(option)
        correct = i == q.get("answer_index")
        _draw_option(draw, oy, i, en_opt, hi_opt, height=option_height, correct=correct)
        oy += option_height + option_gap

    explanation = q.get("explanation", "")
    if isinstance(explanation, dict):
        explanation_en = str(explanation.get("en", "")).strip()
        explanation_hi = str(explanation.get("hi", "")).strip()
    else:
        explanation_en = str(explanation).strip()
        explanation_hi = ""

    if explanation_en or explanation_hi:
        top = oy + 10
        bottom = min(1700, top + 225)
        if bottom > top + 35:
            draw.rounded_rectangle(
                (70, top, VIDEO_WIDTH - 70, bottom),
                radius=15,
                fill=(38, 37, 25),
                outline=(255, 204, 0),
                width=2,
            )
            ey = top + 18
            if explanation_en:
                ey = _draw_wrapped_fit(
                    draw, explanation_en,
                    (95, ey, VIDEO_WIDTH - 95, bottom - 70), "#ffcc00",
                    start_size=25, min_size=18, line_gap=4, align="left", hindi=False,
                )
            if explanation_hi and ey < bottom - 20:
                ey += 4
                _draw_wrapped_fit(
                    draw, explanation_hi,
                    (95, ey, VIDEO_WIDTH - 95, bottom - 15), "#ffcc00",
                    start_size=22, min_size=16, line_gap=3, align="left", hindi=None,
                )

    # Clear, consistent attribution at the bottom-middle of every answer slide.
    _draw_byline(draw, footer_y, size=22)
    image.convert("RGB").save(output, quality=92, optimize=True)


def render_final_cta(output):
    """Final branded CTA slide with the configurable Smart Learning Lab page."""
    image = _base_canvas().convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")

    _draw_logo_center(image, 190)

    draw.text(
        (VIDEO_WIDTH // 2, 510),
        "SMART LEARNING LAB",
        font=_font(46, bold=True),
        fill="white",
        anchor="mm",
    )
    draw.text(
        (VIDEO_WIDTH // 2, 575),
        "LEARN • PRACTICE • GROW",
        font=_font(25, bold=True),
        fill="#00ff9d",
        anchor="mm",
    )

    draw.rounded_rectangle(
        (95, 700, VIDEO_WIDTH - 95, 1075),
        radius=28,
        fill=(18, 43, 62),
        outline=(0, 195, 255),
        width=2,
    )
    draw.text(
        (VIDEO_WIDTH // 2, 785),
        "Continue your practice",
        font=_font(34, bold=True),
        fill="white",
        anchor="mm",
    )
    draw.text(
        (VIDEO_WIDTH // 2, 845),
        "Courses • Quizzes • Practice",
        font=_font(24),
        fill="#cce6ff",
        anchor="mm",
    )

    url = PAGE_URL or "https://smartlearninglab-react.pages.dev"
    # Keep the URL readable and inside the CTA card even if a custom domain is used.
    _draw_wrapped_fit(
        draw, url,
        (125, 920, VIDEO_WIDTH - 125, 1025), "#00ff9d",
        start_size=29, min_size=18, bold=True, line_gap=2, align="center", hindi=False,
    )

    _draw_byline(draw, 1175, size=24)
    draw.text(
        (VIDEO_WIDTH // 2, 1270),
        "Thank you for learning with us!",
        font=_font(27, bold=True),
        fill="#cce6ff",
        anchor="mm",
    )

    image.convert("RGB").save(output, quality=92, optimize=True)
