from pathlib import Path
import re
import unicodedata

from PIL import Image, ImageDraw, ImageFont

from config import ASSETS_DIR, VIDEO_HEIGHT, VIDEO_WIDTH

# All fonts are bundled with the repository. This makes rendering deterministic
# on GitHub Actions and avoids depending on whatever fonts happen to be installed.
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


def _contains_hindi(text):
    return bool(DEVANAGARI_RE.search(str(text or "")))


def _first_existing(paths):
    for path in paths:
        path = Path(path)
        if path.exists():
            return path
    return None


def _font(size, bold=False, hindi=False):
    """Load the correct font for a complete script run."""
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
    """Remove characters that commonly become tofu boxes in bundled fonts."""
    text = str(text or "").replace("\r", "").strip()
    # Emoji are intentionally removed/replaced because this educational design
    # uses text fonts, not an emoji font. Keeping them can create square boxes.
    text = text.replace("💡", "Explanation:")
    return text


def _char_is_devanagari(ch):
    return bool(DEVANAGARI_RE.match(ch))


def _script_runs(text):
    """Split mixed Hindi/English text into drawable font runs.

    This is the key fix for the intermittent square-box problem. A Hindi field
    is not necessarily Hindi-only: many source records contain English words,
    numbers, punctuation, or equations in the `hi` field. Rendering the entire
    field with a Devanagari-only font can turn those characters into tofu boxes.
    Each run now uses the appropriate bundled font.
    """
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
        # Keep whitespace attached to the preceding run. This preserves normal
        # spacing while allowing the next word to switch fonts cleanly.
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
    """Measure mixed-script text with the same fonts used to draw it."""
    text = _clean_display_text(text)
    if not text:
        return 0

    if force_hindi is not None:
        font = _font(size, bold=bold, hindi=force_hindi)
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]

    total = 0
    for run, is_hindi in _script_runs(text):
        font = _font(size, bold=bold, hindi=is_hindi)
        total += draw.textlength(run, font=font)
    return int(round(total))


def _wrap_lines(draw, text, size, max_width, bold=False, force_hindi=None):
    """Wrap mixed Hindi/English text without using a wrong-script font."""
    text = _clean_display_text(text)
    if not text:
        return []

    # Wrap by whitespace first. A token containing both Hindi and Latin is
    # measured using script-aware runs.
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

        # Break very long tokens character-by-character. Width is still
        # script-aware, so a Hindi/Latin transition cannot create tofu boxes.
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
    """Draw one line with per-script fonts and consistent vertical alignment."""
    left, _, right, _ = box
    text = _clean_display_text(text)
    if not text:
        return

    if force_hindi is not None:
        runs = [(text, force_hindi)]
    else:
        runs = _script_runs(text)

    widths = []
    total_width = 0
    for run, is_hindi in runs:
        font = _font(size, bold=bold, hindi=is_hindi)
        w = draw.textlength(run, font=font)
        widths.append((run, is_hindi, font, w))
        total_width += w

    if align == "left":
        x = left
    elif align == "right":
        x = right - total_width
    else:
        x = left + ((right - left) - total_width) / 2

    # Use a common baseline based on the tallest font in this line.
    ascent = max(font.getbbox("Ag")[3] for _, _, font, _ in widths) if widths else size
    baseline_y = y + ascent
    for run, is_hindi, font, w in widths:
        bbox = draw.textbbox((0, 0), run, font=font)
        # Anchor by top while compensating for font-specific bbox offsets.
        draw_y = baseline_y - bbox[3]
        draw.text((x, draw_y), run, font=font, fill=fill)
        x += w


def _draw_wrapped(draw, text, size, box, fill, bold=False, line_gap=8, align="center", force_hindi=None):
    left, top, right, bottom = box
    lines = _wrap_lines(draw, text, size, max(1, right - left), bold=bold, force_hindi=force_hindi)
    font_sample = _font(size, bold=bold, hindi=bool(force_hindi))
    line_height = max(1, int(size * 1.18))
    y = top

    for item in lines:
        if y + line_height > bottom:
            break
        _draw_mixed_line(draw, item, y, box, size, fill, bold=bold, align=align, force_hindi=force_hindi)
        y += line_height + line_gap
    return min(y, bottom)


def _draw_wrapped_fit(draw, text, box, fill, start_size, min_size, bold=False, hindi=None, line_gap=8, align="center"):
    """Draw the largest readable size that fits the available height.

    `hindi=None` means automatic mixed-script detection. `hindi=True` is kept
    only for compatibility and should be used when a field is guaranteed to be
    Devanagari-only. In normal quiz fields we use automatic detection so English
    values inside a Hindi field never render as boxes.
    """
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

    return _draw_wrapped(
        draw, text, int(min_size), box, fill,
        bold=bold, line_gap=line_gap, align=align, force_hindi=force_hindi,
    )


def _draw_option(draw, y, index, en_opt, hi_opt, height=132, correct=False):
    box = (70, y, VIDEO_WIDTH - 70, y + height)
    fill = (0, 255, 157, 220) if correct else (255, 255, 255, 13)
    outline = (0, 255, 157, 255) if correct else (0, 195, 255, 255)
    draw.rounded_rectangle(box, radius=16, fill=fill, outline=outline, width=2)

    text_fill = "black" if correct else "white"
    hi_fill = "#1a1a1a" if correct else "#b3d9ff"

    # English line: English font only.
    _draw_wrapped_fit(
        draw, f"{chr(65 + index)}. {en_opt}",
        (105, y + 14, VIDEO_WIDTH - 105, y + 57), text_fill,
        start_size=29, min_size=23, bold=correct, line_gap=2, align="left", hindi=False,
    )

    # Hindi line: AUTOMATIC mixed-script rendering. This is important because
    # many datasets intentionally put English answers/numbers in the `hi` field.
    if hi_opt:
        _draw_wrapped_fit(
            draw, hi_opt,
            (105, y + 62, VIDEO_WIDTH - 105, y + height - 12), hi_fill,
            start_size=21, min_size=16, line_gap=2, align="left", hindi=None,
        )
    return y + height


def render_question(q, index, timer, output):
    image = _base_canvas()
    draw = ImageDraw.Draw(image, "RGBA")

    logo = _logo()
    logo_x = (VIDEO_WIDTH - logo.width) // 2
    image.paste(logo, (logo_x, 145), logo)

    draw.text((VIDEO_WIDTH // 2, 400), str(timer), font=_font(74, bold=True), fill=(255, 204, 0), anchor="mm")

    en, hi = _question_parts(q)
    y = 500
    y = _draw_wrapped_fit(
        draw, f"Q{index + 1}. {en}",
        (65, y, VIDEO_WIDTH - 65, 800), "white",
        start_size=48, min_size=38, bold=True, line_gap=8, hindi=False,
    )
    if hi:
        y += 10
        y = _draw_wrapped_fit(
            draw, hi,
            (80, y, VIDEO_WIDTH - 80, 910), "#cce6ff",
            start_size=31, min_size=24, line_gap=6, hindi=None,
        )

    options = q.get("options", [])[:4]
    option_height = 132
    option_gap = 14
    total_options_height = len(options) * option_height + max(0, len(options) - 1) * option_gap
    footer_y = 1845
    option_start = max(980, int(y + 28))
    max_start = footer_y - total_options_height - 18
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
        start_size=43, min_size=34, bold=True, line_gap=7, hindi=False,
    )
    if hi:
        y += 8
        y = _draw_wrapped_fit(
            draw, hi,
            (75, y, VIDEO_WIDTH - 75, 720), "#cce6ff",
            start_size=28, min_size=22, line_gap=5, hindi=None,
        )

    options = q.get("options", [])[:4]
    option_height = 112
    option_gap = 10
    option_start = max(750, int(y + 20))
    explanation_reserve = 245 if q.get("explanation") else 40
    max_option_start = VIDEO_HEIGHT - 70 - explanation_reserve - (
        len(options) * option_height + max(0, len(options) - 1) * option_gap
    )
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
                start_size=25, min_size=19, line_gap=5, align="left", hindi=False,
            )
        if explanation_hi and ey < bottom - 20:
            ey += 5
            _draw_wrapped_fit(
                draw, explanation_hi,
                (95, ey, VIDEO_WIDTH - 95, bottom - 18), "#ffcc00",
                start_size=22, min_size=17, line_gap=4, align="left", hindi=None,
            )

    image.convert("RGB").save(output, quality=92, optimize=True)
