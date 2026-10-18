#!/usr/bin/env python3
"""Generate the 1 Aban 1405 hybrid MAZ/Rankland comparison PDF.

Dependencies:
    pip install reportlab arabic-reshaper python-bidi

The plan data lives in examples/1aban-1405-hybrid.json so an agent can
change assumptions or slot assignments without editing the renderer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "examples" / "1aban-1405-hybrid.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "hybrid-maz-rankland-1aban-1405.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 22
GOLD = HexColor("#D7AD3E")
GOLD_DARK = HexColor("#9A7200")
NAVY = HexColor("#17365D")
INK = HexColor("#1F2937")
MUTED = HexColor("#667085")
LINE = HexColor("#D8DDE6")
BG = HexColor("#F7F8FA")
NEW_STUDY = HexColor("#EAF3FF")
NEW_TEST = HexColor("#EAF8F0")
DELAYED = HexColor("#E5F7F5")
REVIEW = HexColor("#FFF5DE")
REVIEW_TEST = HexColor("#F2EDFF")
FLEX = HexColor("#FFFBEA")
LOCKED = HexColor("#ECEFF3")
ANALYSIS = HexColor("#FDECEC")
STRATEGY = HexColor("#EEF0FF")

KIND_STYLE = {
    "new-study": ("مطالعهٔ جدید", NEW_STUDY, HexColor("#1D5FA7")),
    "new-test": ("تست نزدیک", NEW_TEST, HexColor("#177245")),
    "delayed-test": ("تست فاصله‌دار", DELAYED, HexColor("#087F79")),
    "review": ("مرور فعال", REVIEW, HexColor("#9A6300")),
    "review-test": ("مرور تستی", REVIEW_TEST, HexColor("#6741A5")),
    "flex": ("انعطاف", FLEX, GOLD_DARK),
    "locked": ("خارج از ظرفیت", LOCKED, MUTED),
    "analysis": ("تحلیل آزمون", ANALYSIS, HexColor("#A63B3B")),
    "strategy": ("استراتژی", STRATEGY, HexColor("#334EA2")),
}


def find_font(name: str) -> Path:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu") / name,
        ROOT / "assets" / name,
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"Font not found: {name}")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("FA", str(find_font("DejaVuSans.ttf"))))
    pdfmetrics.registerFont(TTFont("FA-Bold", str(find_font("DejaVuSans-Bold.ttf"))))


def shaped(text: object) -> str:
    raw = str(text)
    return get_display(arabic_reshaper.reshape(raw))


def fa_digits(value: object) -> str:
    trans = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(value).translate(trans)


def text_width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(shaped(text), font, size)


def wrap_text(text: str, max_width: float, font: str, size: float, max_lines: int | None = None) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if text_width(trial, font, size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    if max_lines and len(lines) > max_lines:
        kept = lines[:max_lines]
        remainder = " ".join(lines[max_lines - 1 :])
        while remainder and text_width(f"{remainder}…", font, size) > max_width:
            remainder = remainder[:-1].rstrip()
        kept[-1] = f"{remainder}…" if remainder else "…"
        return kept
    return lines


def draw_rtl(c: canvas.Canvas, text: str, x_right: float, y: float, font: str = "FA", size: float = 9, color: Color = INK) -> None:
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawRightString(x_right, y, shaped(text))


def draw_center(c: canvas.Canvas, text: str, x: float, y: float, font: str = "FA", size: float = 9, color: Color = INK) -> None:
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(x, y, shaped(text))


def draw_multiline_rtl(
    c: canvas.Canvas,
    text: str,
    x_right: float,
    y_top: float,
    max_width: float,
    font: str,
    size: float,
    leading: float,
    max_lines: int,
    color: Color = INK,
) -> float:
    lines = wrap_text(text, max_width, font, size, max_lines)
    y = y_top
    for line in lines:
        draw_rtl(c, line, x_right, y, font, size, color)
        y -= leading
    return y


def draw_header(c: canvas.Canvas, meta: dict, page: dict | None, page_number: int, label: str | None = None) -> float:
    top = PAGE_H - 22
    # Minimal logo mark, intentionally not copying a protected logo.
    c.setFillColor(GOLD)
    c.circle(PAGE_W - MARGIN - 19, top - 18, 18, fill=1, stroke=0)
    draw_center(c, "م", PAGE_W - MARGIN - 19, top - 24, "FA-Bold", 18, white)

    draw_rtl(c, meta["title"], PAGE_W - MARGIN - 45, top - 12, "FA-Bold", 15, INK)
    draw_rtl(c, meta["subtitle"], PAGE_W - MARGIN - 45, top - 31, "FA", 8.4, MUTED)

    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(MARGIN, top - 47, PAGE_W - MARGIN, top - 47)

    if page:
        info = [page["page_title"], page["week"], page["range"]]
    else:
        info = [label or "پیوست", meta["target_exam"], meta["range"]]
    box_y = top - 77
    box_h = 22
    gap = 7
    box_w = (PAGE_W - 2 * MARGIN - 2 * gap) / 3
    for index, value in enumerate(info):
        x = MARGIN + index * (box_w + gap)
        c.setFillColor(HexColor("#FFFCF4"))
        c.setStrokeColor(GOLD)
        c.roundRect(x, box_y, box_w, box_h, 3, fill=1, stroke=1)
        draw_center(c, value, x + box_w / 2, box_y + 7, "FA-Bold" if index == 0 else "FA", 7.5, INK)

    badge = meta["version"]
    draw_rtl(c, badge, PAGE_W - MARGIN, box_y - 12, "FA", 7, HexColor("#A63B3B"))
    draw_rtl(c, f"صفحهٔ {fa_digits(page_number)}", MARGIN + 43, box_y - 12, "FA", 7, MUTED)
    return box_y - 19


def draw_slot(c: canvas.Canvas, slot: dict, x: float, y: float, w: float, h: float, compact: bool) -> None:
    kind = slot["kind"]
    label, fill, accent = KIND_STYLE[kind]
    c.setFillColor(fill)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.55)
    c.rect(x, y, w, h, fill=1, stroke=1)

    pad = 5
    top = y + h - pad
    # Checkbox on the visual right.
    c.setStrokeColor(accent)
    c.setLineWidth(0.7)
    c.rect(x + w - pad - 7, top - 7, 7, 7, fill=0, stroke=1)
    draw_rtl(c, slot["subject"], x + w - pad - 11, top - 6.5, "FA-Bold", 7.3 if compact else 8.3, INK)

    # Kind label on the left.
    c.setFillColor(accent)
    c.roundRect(x + pad, top - 10, 52 if not compact else 45, 11, 3, fill=1, stroke=0)
    draw_center(c, label, x + pad + (26 if not compact else 22.5), top - 7.8, "FA-Bold", 5.5 if compact else 6.1, white)

    title_size = 7.4 if compact else 8.6
    detail_size = 6.3 if compact else 7.25
    title_y = top - (18 if compact else 20)
    title_lines = 1 if compact else 2
    after_title = draw_multiline_rtl(
        c,
        slot["title"],
        x + w - pad,
        title_y,
        w - 2 * pad,
        "FA-Bold",
        title_size,
        title_size + 2,
        title_lines,
        INK,
    )
    max_detail = 1 if compact else 2
    draw_multiline_rtl(
        c,
        slot["detail"],
        x + w - pad,
        after_title - 1,
        w - 2 * pad,
        "FA",
        detail_size,
        detail_size + 2,
        max_detail,
        MUTED,
    )

    c.setStrokeColor(HexColor("#D5D9E0"))
    c.setDash(1, 1)
    c.line(x + pad, y + 15, x + w - pad, y + 15)
    c.setDash()
    if kind == "locked":
        footer = "در جمع ظرفیت نیست"
    elif kind == "flex":
        footer = "۷۵ دقیقه؛ فقط در صورت نیاز"
    elif "test" in kind:
        footer = "۷۵ دقیقه | تعداد تست: ثبت واقعی"
    else:
        footer = "۷۵ دقیقه"
    draw_rtl(c, footer, x + w - pad, y + 5.2, "FA", 5.8 if compact else 6.4, MUTED)


def draw_day_card(c: canvas.Canvas, day: dict, x: float, y_top: float, w: float, h: float, compact: bool = False) -> None:
    header_h = 22
    c.setFillColor(GOLD)
    c.setStrokeColor(GOLD_DARK)
    c.roundRect(x, y_top - h, w, h, 3, fill=0, stroke=1)
    c.rect(x, y_top - header_h, w, header_h, fill=1, stroke=0)

    assigned = sum(1 for s in day["slots"] if s["kind"] not in {"locked", "flex"})
    flex_count = sum(1 for s in day["slots"] if s["kind"] == "flex")
    hours = assigned * 75 / 60
    if flex_count:
        total_label = f"{fa_digits(assigned)} قطعی + {fa_digits(flex_count)} انعطاف"
    else:
        total_label = f"{fa_digits(assigned)} زنگ قطعی | {fa_digits(hours).replace('.0', '')} ساعت"

    draw_rtl(c, f"{day['day']} {day['date']}", x + w - 7, y_top - 15, "FA-Bold", 9 if compact else 10, INK)
    draw_center(c, day["focus"], x + w * 0.52, y_top - 15, "FA", 6.4 if compact else 7.5, INK)
    draw_center(c, total_label, x + 73, y_top - 15, "FA-Bold", 6.2 if compact else 7, INK)

    grid_y_top = y_top - header_h
    row_h = (h - header_h) / 2
    col_w = w / 3
    for idx, slot in enumerate(day["slots"]):
        row = idx // 3
        col_rtl = idx % 3
        cell_x = x + (2 - col_rtl) * col_w
        cell_y = grid_y_top - (row + 1) * row_h
        draw_slot(c, slot, cell_x, cell_y, col_w, row_h, compact)


def draw_exam_card(c: canvas.Canvas, exam: dict, x: float, y_top: float, w: float, h: float) -> None:
    c.setFillColor(GOLD)
    c.setStrokeColor(GOLD_DARK)
    c.roundRect(x, y_top - h, w, h, 4, fill=0, stroke=1)
    c.rect(x, y_top - 25, w, 25, fill=1, stroke=0)
    draw_rtl(c, f"{exam['day']} {exam['date']} — {exam['title']}", x + w - 8, y_top - 17, "FA-Bold", 10, INK)
    draw_multiline_rtl(c, exam["detail"], x + w - 10, y_top - 43, w - 20, "FA", 8, 12, 3, INK)


def draw_footer(c: canvas.Canvas, meta: dict, page_number: int) -> None:
    y = 18
    c.setStrokeColor(GOLD)
    c.line(MARGIN, y + 9, PAGE_W - MARGIN, y + 9)
    draw_rtl(c, "خروجی مقایسه‌ای؛ نه برنامهٔ رسمی ماز و نه نسخهٔ شخصی‌سازی‌شده", PAGE_W - MARGIN, y, "FA", 6.2, MUTED)
    draw_rtl(c, f"آزمون {meta['target_exam']} | {fa_digits(page_number)}", MARGIN + 110, y, "FA", 6.2, MUTED)


def draw_plan_page(c: canvas.Canvas, meta: dict, page: dict, page_number: int) -> None:
    c.setFillColor(white)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    start_y = draw_header(c, meta, page, page_number)
    days = page["days"]
    has_exam = "exam_day" in page

    if len(days) == 3 and not has_exam:
        gap = 7
        card_h = (start_y - 43 - 2 * gap) / 3
        compact = False
    elif len(days) == 4:
        gap = 5
        card_h = (start_y - 42 - 3 * gap) / 4
        compact = True
    elif has_exam:
        gap = 6
        exam_h = 78
        card_h = (start_y - 43 - exam_h - 3 * gap) / 3
        compact = card_h < 185
    else:
        gap = 6
        card_h = (start_y - 43 - (len(days) - 1) * gap) / len(days)
        compact = card_h < 180

    y_top = start_y
    for day in days:
        draw_day_card(c, day, MARGIN, y_top, PAGE_W - 2 * MARGIN, card_h, compact)
        y_top -= card_h + gap
    if has_exam:
        draw_exam_card(c, page["exam_day"], MARGIN, y_top, PAGE_W - 2 * MARGIN, exam_h)

    draw_footer(c, meta, page_number)
    c.showPage()


def draw_metric(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str, value: str, note: str, accent: Color) -> None:
    c.setFillColor(white)
    c.setStrokeColor(accent)
    c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
    c.setFillColor(accent)
    c.roundRect(x + w - 8, y, 8, h, 3, fill=1, stroke=0)
    draw_rtl(c, title, x + w - 16, y + h - 18, "FA-Bold", 8, MUTED)
    draw_rtl(c, value, x + w - 16, y + h - 42, "FA-Bold", 16, accent)
    draw_rtl(c, note, x + w - 16, y + 10, "FA", 6.6, MUTED)


def draw_comparison_page(c: canvas.Canvas, data: dict, page_number: int) -> None:
    meta = data["meta"]
    cap = data["capacity"]
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    start_y = draw_header(c, meta, None, page_number, "پیوست: تفاوت و کنترل ظرفیت")

    gap = 7
    metric_w = (PAGE_W - 2 * MARGIN - 3 * gap) / 4
    metric_y = start_y - 72
    metrics = [
        ("نسخهٔ اصلی", f"{fa_digits(cap['original_hours'])} ساعت", f"{fa_digits(cap['original_tests'])} تست ثابت", HexColor("#A63B3B")),
        ("ظرفیت فرض‌شده", f"{fa_digits(cap['available_blocks'])} زنگ", "پیش از آزمون", NAVY),
        ("تکلیف قطعی", f"{fa_digits(cap['assigned_blocks'])} زنگ", f"{fa_digits(cap['assigned_hours'])} ساعت", HexColor("#177245")),
        ("انعطاف واقعی", f"{fa_digits(cap['flex_blocks'])} زنگ", f"{fa_digits(cap['flex_hours'])} ساعت", GOLD_DARK),
    ]
    for i, item in enumerate(metrics):
        draw_metric(c, MARGIN + i * (metric_w + gap), metric_y, metric_w, 62, *item)

    table_top = metric_y - 20
    table_x = MARGIN
    table_w = PAGE_W - 2 * MARGIN
    rows = [
        ("مبنای تخصیص", "باکس‌ها و عددهای ثابت", "بودجه، جدید/مروری و ظرفیت"),
        ("پایهٔ دانش‌آموز", "هفتهٔ دوم با برچسب دهم", "دوازدهم؛ مرور پایهٔ دهم"),
        ("زیست", "مطالعه و دو باکس تست همان روز", "یک مطالعه؛ تست دو روز بعد"),
        ("تعداد تست", "۲۰، ۲۵ و ۳۰ تست ثابت", "ثبت تعداد واقعی در ۷۵ دقیقه"),
        ("جمعهٔ میانی", "آزمون تمرینی ثابت", "تکمیل لقمه‌ها + یک زنگ انعطاف"),
        ("ظرفیت", "۹۴ ساعت از پیش تعیین‌شده", "۶۵ ساعت قطعی + ۷٫۵ ساعت انعطاف"),
        ("عقب‌افتادگی", "خانه‌های خالی بدون موتور انتقال", "زنگ انعطاف و بازچینی شب قبل"),
    ]
    header_h = 24
    row_h = 30
    col_widths = [table_w * 0.22, table_w * 0.37, table_w * 0.41]
    table_h = header_h + row_h * len(rows)
    c.setFillColor(white)
    c.setStrokeColor(LINE)
    c.roundRect(table_x, table_top - table_h, table_w, table_h, 4, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.rect(table_x, table_top - header_h, table_w, header_h, fill=1, stroke=0)
    headers = ["محور", "قالب اصلی رتبه‌لند", "نسخهٔ ترکیبی فعلی"]
    cursor = table_x
    for i, header in enumerate(headers):
        draw_center(c, header, cursor + col_widths[i] / 2, table_top - 16, "FA-Bold", 7.3, white)
        cursor += col_widths[i]

    for r, row in enumerate(rows):
        y_top = table_top - header_h - r * row_h
        if r % 2:
            c.setFillColor(HexColor("#FAFBFC"))
            c.rect(table_x, y_top - row_h, table_w, row_h, fill=1, stroke=0)
        cursor = table_x
        for i, cell in enumerate(row):
            c.setStrokeColor(LINE)
            c.line(cursor, y_top, cursor, y_top - row_h)
            draw_center(c, cell, cursor + col_widths[i] / 2, y_top - 18, "FA-Bold" if i == 0 else "FA", 6.4, INK)
            cursor += col_widths[i]
        c.setStrokeColor(LINE)
        c.line(table_x, y_top - row_h, table_x + table_w, y_top - row_h)

    assumptions_top = table_top - table_h - 18
    draw_rtl(c, "فرض‌های این نمونه", PAGE_W - MARGIN, assumptions_top, "FA-Bold", 10, NAVY)
    y = assumptions_top - 17
    for index, assumption in enumerate(data["assumptions"], start=1):
        draw_rtl(c, f"{fa_digits(index)}.", PAGE_W - MARGIN, y, "FA-Bold", 7, GOLD_DARK)
        lines = wrap_text(assumption, table_w - 24, "FA", 6.8, 2)
        for line in lines:
            draw_rtl(c, line, PAGE_W - MARGIN - 16, y, "FA", 6.8, INK)
            y -= 9
        y -= 3

    note_y = max(44, y - 4)
    c.setFillColor(HexColor("#FFF7DD"))
    c.setStrokeColor(GOLD)
    c.roundRect(MARGIN, note_y, table_w, 35, 5, fill=1, stroke=1)
    draw_rtl(c, "نتیجه:", PAGE_W - MARGIN - 8, note_y + 22, "FA-Bold", 8, GOLD_DARK)
    draw_rtl(c, "ظاهر دقیق رتبه‌لند حفظ شده، اما موتور ساعت و تست ثابت با منطق لقمه، فاصلهٔ حافظه‌ای و ظرفیت جایگزین شده است.", PAGE_W - MARGIN - 48, note_y + 22, "FA", 6.9, INK)
    draw_rtl(c, "برای نسخهٔ شخصی باید ساعت مدرسه، کلاس، سابقهٔ مطالعه و تسلط واقعی دانش‌آموز دریافت شود.", PAGE_W - MARGIN - 8, note_y + 9, "FA", 6.9, INK)

    draw_footer(c, meta, page_number)
    c.showPage()


def generate(data_path: Path, output_path: Path) -> None:
    register_fonts()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=A4, pageCompression=1)
    c.setTitle(data["meta"]["title"])
    c.setAuthor("MAZ Planning Playbook")
    c.setSubject("Hybrid MAZ allocation with Rankland visual format")

    for page_number, page in enumerate(data["pages"], start=1):
        draw_plan_page(c, data["meta"], page, page_number)
    draw_comparison_page(c, data, len(data["pages"]) + 1)
    c.save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    generate(args.data, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
