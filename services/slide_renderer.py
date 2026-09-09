from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

from config import ASSETS_DIR, VIDEO_HEIGHT, VIDEO_WIDTH

# Keep all fonts inside the repository so GitHub Actions does not depend on
# whatever fonts happen to be installed on the runner.
FONT_REGULAR = ASSETS_DIR / "fonts" / "DejaVuSans.ttf"
FONT_BOLD = ASSETS_DIR / "fonts" / "DejaVuSans-Bold.ttf"
FONT_HINDI = ASSETS_DIR / "fonts" / "NotoSansDevanagari-Regular.ttf"
FONT_HINDI_BOLD = ASSETS_DIR / "fonts" / "NotoSansDevanagari-Regular.ttf"

# Fallbacks are useful when running locally, but the bundled fonts are always
# preferred. Devanagari must never fall back to DejaVu, because that produces
# square boxes for Hindi glyphs.
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
    "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
]

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F\u1CD0-\u1CFF\uA8E0-\uA8FF]")


def _contains_hindi(text):
    return bool(DEVANAGARI_RE.search(str(text or "")))


def _first_existing(paths):
    for path in paths:
        path = Path(path)
        if path.exists():
            return path
    return None


def _font(size, bold=False, hindi=False):
    """Load a script-appropriate font, preferring repository-bundled fonts."""
    size = max(10, int(size))
    if hindi:
        path = _first_existing([FONT_HINDI_BOLD if bold else FONT_HINDI, *SYSTEM_FONT_HINDI])
    else:
        path = _first_existing([
            FONT_BOLD if bold else FONT_REGULAR,
            *(SYSTEM_FONT_BOLDS if bold else SYSTEM_FONT_REGULARS),
        ])
    if path:
        # RAQM provides proper shaping/positioning for Devanagari where Pillow
        # was built with libraqm. The fallback keeps the code compatible with
        # minimal local Pillow installations.
        try:
            return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
        except Exception:
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _gradient():
    # Create the static background efficiently instead of filling 2M pixels in
    # nested Python loops.
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
    global _LOGO
    if _LOGO is None:
        logo_path = ASSETS_DIR / "logo.png"
        logo = Image.open(logo_path).convert("RGBA").resize((210, 210), Image.Resampling.LANCZOS)
        mask = Image.new("L", logo.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, logo.width - 1, logo.height - 1), fill=255)
        logo.putalpha(mask)
        _LOGO = logo
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
    """Remove symbols that commonly render as tofu boxes with basic fonts."""
    text = str(text or "").replace("\r", "").strip()
    # The light-bulb emoji is not guaranteed by the bundled Latin/Devanagari
    # fonts. Use a plain text label instead of ever showing a missing-glyph box.
    text = text.replace("💡", "Explanation:")
    return text


def _wrap_lines(draw, text, font, max_width):
    """Wrap normal text and also break an unusually long token safely."""
    text = _clean_display_text(text)
    if not text:
        return []

    words = text.split()
    lines = []
    line = ""

    def width(value):
        if not value:
            return 0
        box = draw.textbbox((0, 0), value, font=font)
        return box[2] - box[0]

    for word in words:
        candidate = word if not line else f"{line} {word}"
        if width(candidate) <= max_width:
            line = candidate
            continue

        if line:
            lines.append(line)
            line = ""

        if width(word) <= max_width:
            line = word
            continue

        # Break a very long word/token by characters rather than allowing it
        # to run outside the video frame.
        chunk = ""
        for char in word:
            candidate = chunk + char
            if chunk and width(candidate) > max_width:
                lines.append(chunk)
                chunk = char
            else:
                chunk = candidate
        line = chunk

    if line:
        lines.append(line)
    return lines


def _draw_wrapped(draw, text, font, box, fill, line_gap=8, align="center"):
    left, top, right, bottom = box
    max_width = max(1, right - left)
    lines = _wrap_lines(draw, text, font, max_width)
    y = top
    line_height = max(1, int(font.size * 1.18))

    for item in lines:
        bbox = draw.textbbox((0, 0), item, font=font)
        width = bbox[2] - bbox[0]
        if align == "left":
            x = left
        elif align == "right":
            x = right - width
        else:
            x = left + (max_width - width) / 2
        draw.text((x, y), item, font=font, fill=fill)
        y += line_height + line_gap
        if y > bottom:
            break
    return min(y, bottom)


def _draw_wrapped_fit(draw, text, box, fill, start_size, min_size, bold=False, hindi=False, line_gap=8, align="center"):
    """Draw text with the largest readable size that fits the available height."""
    left, top, right, bottom = box
    for size in range(int(start_size), int(min_size) - 1, -1):
        font = _font(size, bold=bold, hindi=hindi)
        lines = _wrap_lines(draw, text, font, right - left)
        line_height = max(1, int(font.size * 1.18))
        needed = len(lines) * line_height + max(0, len(lines) - 1) * line_gap
        if needed <= bottom - top:
            y = top
            for item in lines:
                bbox = draw.textbbox((0, 0), item, font=font)
                width = bbox[2] - bbox[0]
                if align == "left":
                    x = left
                elif align == "right":
                    x = right - width
                else:
                    x = left + ((right - left) - width) / 2
                draw.text((x, y), item, font=font, fill=fill)
                y += line_height + line_gap
            return y
    # Last-resort rendering at the minimum size.
    font = _font(min_size, bold=bold, hindi=hindi)
    return _draw_wrapped(draw, text, font, box, fill, line_gap, align)


def _draw_option(draw, y, index, en_opt, hi_opt, height=132, correct=False):
    box = (70, y, VIDEO_WIDTH - 70, y + height)
    fill = (0, 255, 157, 220) if correct else (255, 255, 255, 13)
    outline = (0, 255, 157, 255) if correct else (0, 195, 255, 255)
    draw.rounded_rectangle(box, radius=16, fill=fill, outline=outline, width=2)

    text_fill = "black" if correct else "white"
    hi_fill = "#1a1a1a" if correct else "#b3d9ff"

    # Keep the English and Hindi lines vertically aligned and use a real
    # Devanagari font whenever the Hindi field contains Devanagari.
    draw.text(
        (105, y + 18),
        f"{chr(65 + index)}. {en_opt}",
        font=_font(29, bold=correct),
        fill=text_fill,
    )
    if hi_opt:
        draw.text(
            (105, y + 68),
            hi_opt,
            font=_font(21, hindi=True),
            fill=hi_fill,
        )
    return y + height


def render_question(q, index, timer, output):
    image = _base_canvas()
    draw = ImageDraw.Draw(image, "RGBA")

    logo = _logo()
    logo_x = (VIDEO_WIDTH - logo.width) // 2
    image.paste(logo, (logo_x, 145), logo)

    # Timer has its own fixed visual zone and never competes with the question.
    draw.text((VIDEO_WIDTH // 2, 400), str(timer), font=_font(74, bold=True), fill=(255, 204, 0), anchor="mm")

    en, hi = _question_parts(q)
    y = 500
    y = _draw_wrapped_fit(
        draw, f"Q{index + 1}. {en}",
        (65, y, VIDEO_WIDTH - 65, 800), "white",
        start_size=48, min_size=38, bold=True, line_gap=8,
    )
    if hi:
        y += 10
        y = _draw_wrapped_fit(
            draw, hi,
            (80, y, VIDEO_WIDTH - 80, 910), "#cce6ff",
            start_size=31, min_size=24, hindi=True, line_gap=6,
        )

    # Dynamic option placement prevents long bilingual questions from colliding
    # with the first option while preserving a consistent lower layout.
    options = q.get("options", [])[:4]
    option_height = 132
    option_gap = 14
    total_options_height = len(options) * option_height + max(0, len(options) - 1) * option_gap
    footer_y = 1845
    option_start = max(980, int(y + 28))
    max_start = footer_y - total_options_height - 18
    option_start = min(option_start, max_start)

    # If the question is unusually tall, slightly reduce option typography rather
    # than allowing any content to cross the footer. The boxes remain aligned.
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
    image = _base_canvas()
    draw = ImageDraw.Draw(image, "RGBA")

    logo = _logo()
    logo_x = (VIDEO_WIDTH - logo.width) // 2
    image.paste(logo, (logo_x, 115), logo)

    en, hi = _question_parts(q)
    y = 365
    y = _draw_wrapped_fit(
        draw, f"Q{index + 1}. {en}",
        (65, y, VIDEO_WIDTH - 65, 620), "white",
        start_size=43, min_size=34, bold=True, line_gap=7,
    )
    if hi:
        y += 8
        y = _draw_wrapped_fit(
            draw, hi,
            (75, y, VIDEO_WIDTH - 75, 720), "#cce6ff",
            start_size=28, min_size=22, hindi=True, line_gap=5,
        )

    options = q.get("options", [])[:4]
    option_height = 112
    option_gap = 10
    option_start = max(750, int(y + 20))
    # Reserve space for explanation and footer-like bottom margin.
    explanation_reserve = 245 if q.get("explanation") else 40
    max_option_start = VIDEO_HEIGHT - 70 - explanation_reserve - (len(options) * option_height + max(0, len(options) - 1) * option_gap)
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
        top = oy + 12
        bottom = min(VIDEO_HEIGHT - 65, top + 235)
        draw.rounded_rectangle(
            (70, top, VIDEO_WIDTH - 70, bottom),
            radius=15,
            fill=(255, 204, 0, 20),
            outline=(255, 204, 0, 255),
            width=2,
        )
        ey = top + 22
        if explanation_en:
            ey = _draw_wrapped_fit(
                draw, explanation_en,
                (95, ey, VIDEO_WIDTH - 95, bottom - 70), "#ffcc00",
                start_size=25, min_size=19, line_gap=5, align="left",
            )
        if explanation_hi and ey < bottom - 20:
            ey += 5
            _draw_wrapped_fit(
                draw, explanation_hi,
                (95, ey, VIDEO_WIDTH - 95, bottom - 18), "#ffcc00",
                start_size=22, min_size=17, hindi=True, line_gap=4, align="left",
            )

    image.convert("RGB").save(output, quality=92, optimize=True)
