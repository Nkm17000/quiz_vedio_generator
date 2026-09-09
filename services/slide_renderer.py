from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from config import ASSETS_DIR, VIDEO_HEIGHT, VIDEO_WIDTH

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_HINDI = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"


def _font(size, bold=False, hindi=False):
    candidates = []
    if hindi:
        candidates += [FONT_HINDI, "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf"]
    candidates += [FONT_BOLD if bold else FONT_REGULAR]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _gradient():
    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
    pixels = image.load()
    top = (2, 13, 24)
    bottom = (10, 42, 67)
    for y in range(VIDEO_HEIGHT):
        t = y / (VIDEO_HEIGHT - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(VIDEO_WIDTH):
            pixels[x, y] = color
    return image


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
        logo = Image.open(ASSETS_DIR / "logo.png").convert("RGBA").resize((240, 240))
        mask = Image.new("L", logo.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 239, 239), fill=255)
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


def _draw_wrapped(draw, text, font, box, fill, line_gap=8, align="center"):
    left, top, right, bottom = box
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= right - left:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)

    y = top
    for item in lines:
        bbox = draw.textbbox((0, 0), item, font=font)
        width = bbox[2] - bbox[0]
        x = left if align == "left" else left + ((right - left) - width) / 2
        draw.text((x, y), item, font=font, fill=fill)
        y += bbox[3] - bbox[1] + line_gap
    return y


def render_question(q, index, timer, output):
    image = _base_canvas()
    draw = ImageDraw.Draw(image, "RGBA")

    logo = _logo()
    logo_x = (VIDEO_WIDTH - logo.width) // 2
    image.alpha_composite(logo, (logo_x, 210)) if image.mode == "RGBA" else image.paste(logo, (logo_x, 210), logo)

    draw.text((VIDEO_WIDTH // 2, 485), f"{timer}", font=_font(82, bold=True), fill=(255, 204, 0), anchor="mm")

    en, hi = _question_parts(q)
    y = 580
    y = _draw_wrapped(draw, f"Q{index + 1}. {en}", _font(46, bold=True), (70, y, VIDEO_WIDTH - 70, 980), "white", 12)
    if hi:
        y += 18
        _draw_wrapped(draw, hi, _font(30, hindi=True), (90, y, VIDEO_WIDTH - 90, 1080), "#cce6ff", 8)

    options = q.get("options", [])
    y = 1120
    for i, option in enumerate(options[:4]):
        en_opt, hi_opt = _option_parts(option)
        box = (70, y, VIDEO_WIDTH - 70, y + 145)
        draw.rounded_rectangle(box, radius=18, fill=(255, 255, 255, 13), outline=(0, 195, 255, 255), width=2)
        draw.text((105, y + 22), f"{chr(65 + i)}. {en_opt}", font=_font(31), fill="white")
        if hi_opt:
            draw.text((105, y + 72), hi_opt, font=_font(22, hindi=True), fill="#b3d9ff")
        y += 170

    draw.text((VIDEO_WIDTH // 2, 1850), "Comment your answer!", font=_font(28, bold=True), fill="#00ff9d", anchor="mm")
    image.convert("RGB").save(output, quality=92)


def render_answer(q, index, output):
    image = _base_canvas()
    draw = ImageDraw.Draw(image, "RGBA")
    logo = _logo()
    logo_x = (VIDEO_WIDTH - logo.width) // 2
    image.paste(logo, (logo_x, 160), logo)

    en, hi = _question_parts(q)
    y = 470
    y = _draw_wrapped(draw, f"Q{index + 1}. {en}", _font(42, bold=True), (70, y, VIDEO_WIDTH - 70, 790), "white", 10)
    if hi:
        y += 12
        y = _draw_wrapped(draw, hi, _font(28, hindi=True), (80, y, VIDEO_WIDTH - 80, 860), "#cce6ff", 8)

    y = max(y + 25, 880)
    for i, option in enumerate(q.get("options", [])[:4]):
        en_opt, hi_opt = _option_parts(option)
        correct = i == q.get("answer_index")
        box = (70, y, VIDEO_WIDTH - 70, y + 130)
        fill = (0, 255, 157, 220) if correct else (255, 255, 255, 13)
        outline = (0, 255, 157, 255) if correct else (0, 195, 255, 255)
        draw.rounded_rectangle(box, radius=14, fill=fill, outline=outline, width=2)
        text_fill = "black" if correct else "white"
        draw.text((105, y + 20), f"{chr(65 + i)}. {en_opt}", font=_font(30, bold=correct), fill=text_fill)
        if hi_opt:
            draw.text((105, y + 68), hi_opt, font=_font(21, hindi=True), fill="#1a1a1a" if correct else "#b3d9ff")
        y += 150

    explanation = q.get("explanation", "")
    if isinstance(explanation, dict):
        explanation = f"{explanation.get('en', '')}\n{explanation.get('hi', '')}".strip()
    if explanation:
        draw.rounded_rectangle((70, y + 10, VIDEO_WIDTH - 70, min(y + 300, VIDEO_HEIGHT - 70)), radius=15, fill=(255, 204, 0, 20), outline=(255, 204, 0, 255), width=2)
        _draw_wrapped(draw, f"💡 {explanation}", _font(25), (95, y + 35, VIDEO_WIDTH - 95, min(y + 280, VIDEO_HEIGHT - 90)), "#ffcc00", 8)

    image.convert("RGB").save(output, quality=92)
