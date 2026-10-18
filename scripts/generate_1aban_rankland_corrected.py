#!/usr/bin/env python3
"""Generate the corrected Rankland plan for the 1 Aban 1405 MAZ exam.

The schedule keeps the approved standard core (47 hours / 495 tests per
week and the fixed daily distribution) while applying the execution rules
from RANKLAND_PLANNING_PLAYBOOK.md.

Dependencies:
    pip install -r requirements-pdf.txt
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "examples" / "1aban-1405-rankland-corrected.json"
DEFAULT_OUTPUT = ROOT / "برنامه جدیید" / "برنامه-اصلاح‌شده-رتبه‌لند-۱-آبان-۱۴۰۵.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 22
GOLD = HexColor("#D7AD3E")
GOLD_DARK = HexColor("#8A6500")
NAVY = HexColor("#17365D")
INK = HexColor("#202938")
MUTED = HexColor("#667085")
LINE = HexColor("#D7DCE3")
BG = HexColor("#F5F7FA")
BIO = HexColor("#EAF7EF")
MATH = HexColor("#EEF2FF")
PHYSICS = HexColor("#EAF5FC")
CHEM = HexColor("#FFF4DF")
STUDY = HexColor("#FFFBEA")
ALERT = HexColor("#FDECEC")
SOFT_GOLD = HexColor("#FFFAE9")

SUBJECT_COLORS = {
    "زیست": BIO,
    "ریاضی": MATH,
    "فیزیک": PHYSICS,
    "شیمی": CHEM,
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
    return get_display(arabic_reshaper.reshape(str(text)))


def fa_digits(value: object) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def text_width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(shaped(text), font, size)


def ellipsize(text: str, max_width: float, font: str, size: float) -> str:
    value = str(text)
    if text_width(value, font, size) <= max_width:
        return value
    while value and text_width(f"{value}…", font, size) > max_width:
        value = value[:-1].rstrip()
    return f"{value}…" if value else "…"


def wrap_text(
    text: str,
    max_width: float,
    font: str,
    size: float,
    max_lines: int | None = None,
) -> list[str]:
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
    if max_lines is not None and len(lines) > max_lines:
        kept = lines[:max_lines]
        remainder = " ".join(lines[max_lines - 1 :])
        kept[-1] = ellipsize(remainder, max_width, font, size)
        return kept
    return lines


def draw_rtl(
    c: canvas.Canvas,
    text: object,
    x_right: float,
    y: float,
    font: str = "FA",
    size: float = 8,
    color: Color = INK,
) -> None:
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawRightString(x_right, y, shaped(text))


def draw_center(
    c: canvas.Canvas,
    text: object,
    x: float,
    y: float,
    font: str = "FA",
    size: float = 8,
    color: Color = INK,
) -> None:
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(x, y, shaped(text))


def draw_lines_rtl(
    c: canvas.Canvas,
    lines: list[str],
    x_right: float,
    y_top: float,
    font: str,
    size: float,
    leading: float,
    color: Color = INK,
) -> float:
    y = y_top
    for line in lines:
        draw_rtl(c, line, x_right, y, font, size, color)
        y -= leading
    return y


def subject_family(subject: str) -> str:
    for family in SUBJECT_COLORS:
        if subject.startswith(family):
            return family
    return ""


def validate(data: dict) -> None:
    days = data["days"]
    if len(days) != 12:
        raise ValueError(f"Expected 12 study days, got {len(days)}")

    expected_daily_hours = [8, 7, 9, 7, 9, 7]
    expected_daily_tests = [70, 55, 100, 85, 100, 85]
    expected_subjects = {
        "زیست": (15, 120),
        "ریاضی": (11, 150),
        "فیزیک": (12, 150),
        "شیمی": (9, 75),
    }

    for week in (1, 2):
        current = [day for day in days if day["week"] == week]
        if [day["hours"] for day in current] != expected_daily_hours:
            raise ValueError(f"Week {week}: wrong daily hours")
        if [day["tests"] for day in current] != expected_daily_tests:
            raise ValueError(f"Week {week}: wrong daily tests")
        if sum(day["hours"] for day in current) != 47:
            raise ValueError(f"Week {week}: hours do not sum to 47")
        if sum(day["tests"] for day in current) != 495:
            raise ValueError(f"Week {week}: tests do not sum to 495")

        totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for day in current:
            if sum(box["hours"] for box in day["boxes"]) != day["hours"]:
                raise ValueError(f"{day['date']}: box hours mismatch")
            if sum(box["tests"] for box in day["boxes"]) != day["tests"]:
                raise ValueError(f"{day['date']}: box tests mismatch")
            for box in day["boxes"]:
                family = subject_family(box["subject"])
                if not family:
                    raise ValueError(f"Unknown subject: {box['subject']}")
                totals[family][0] += box["hours"]
                totals[family][1] += box["tests"]
                if (
                    box["tests"]
                    and "همهٔ گزینه" in box["detail"]
                    and "نه همهٔ گزینه" not in box["detail"]
                ):
                    raise ValueError(f"Forbidden blanket analysis rule: {box}")

        for family, expected in expected_subjects.items():
            if tuple(totals[family]) != expected:
                raise ValueError(
                    f"Week {week}: {family} total {tuple(totals[family])}, expected {expected}"
                )

    if sum(day["hours"] for day in days) != 94:
        raise ValueError("Two-week hours do not sum to 94")
    if sum(day["tests"] for day in days) != 990:
        raise ValueError("Two-week tests do not sum to 990")
    if sum(len(day["boxes"]) for day in days) != 54:
        raise ValueError("The standard two-week plan must contain 54 boxes")

    last_day = days[-1]
    if any(
        box["kind"] == "study" and "مبحث سنگین جدید ممنوع" not in box["detail"]
        for box in last_day["boxes"]
    ):
        raise ValueError("Last day contains an unmarked study box")


def draw_logo(c: canvas.Canvas, x: float, y: float) -> None:
    c.setFillColor(GOLD)
    c.circle(x, y, 18, fill=1, stroke=0)
    draw_center(c, "ر", x, y - 7, "FA-Bold", 19, white)


def draw_header(
    c: canvas.Canvas,
    meta: dict,
    page_number: int,
    week_label: str,
    date_range: str,
) -> float:
    top = PAGE_H - 22
    draw_logo(c, PAGE_W - MARGIN - 18, top - 18)
    draw_rtl(c, meta["title"], PAGE_W - MARGIN - 44, top - 12, "FA-Bold", 14.2, INK)
    draw_rtl(c, meta["subtitle"], PAGE_W - MARGIN - 44, top - 31, "FA", 7.9, MUTED)

    c.setStrokeColor(GOLD)
    c.setLineWidth(1.3)
    c.line(MARGIN, top - 47, PAGE_W - MARGIN, top - 47)

    y = top - 77
    gap = 7
    box_w = (PAGE_W - 2 * MARGIN - 2 * gap) / 3
    info = [week_label, date_range, f"صفحهٔ {fa_digits(page_number)} از ۵"]
    for index, value in enumerate(info):
        x = MARGIN + index * (box_w + gap)
        c.setFillColor(SOFT_GOLD if index == 0 else white)
        c.setStrokeColor(GOLD)
        c.roundRect(x, y, box_w, 23, 4, fill=1, stroke=1)
        draw_center(c, value, x + box_w / 2, y + 7.5, "FA-Bold" if index == 0 else "FA", 7.2, INK)

    draw_rtl(c, meta["note"], PAGE_W - MARGIN, y - 12, "FA", 6.2, HexColor("#9B2C2C"))
    return y - 20


def draw_footer(c: canvas.Canvas, page_number: int) -> None:
    y = 17
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.7)
    c.line(MARGIN, y + 9, PAGE_W - MARGIN, y + 9)
    draw_rtl(
        c,
        "رتبه‌لند اصلاح‌شده | تحلیل: غلط، سفید، شک‌دار، سپس درستِ نکته‌دار",
        PAGE_W - MARGIN,
        y,
        "FA",
        6.1,
        MUTED,
    )
    draw_rtl(c, f"۱ آبان ۱۴۰۵ | {fa_digits(page_number)}", MARGIN + 94, y, "FA", 6.1, MUTED)


def draw_task_row(
    c: canvas.Canvas,
    box: dict,
    index: int,
    x: float,
    y: float,
    w: float,
    h: float,
) -> None:
    family = subject_family(box["subject"])
    fill = SUBJECT_COLORS[family] if box["kind"] == "test" else STUDY
    c.setFillColor(fill)
    c.setStrokeColor(LINE)
    c.rect(x, y, w, h, fill=1, stroke=1)

    metric_w = 72
    subject_w = 92
    center_x = x + metric_w
    center_w = w - metric_w - subject_w
    subject_x = x + w - subject_w

    c.setStrokeColor(LINE)
    c.line(center_x, y, center_x, y + h)
    c.line(subject_x, y, subject_x, y + h)

    # Metrics on the visual left.
    hours = fa_digits(box["hours"])
    tests = fa_digits(box["tests"]) if box["tests"] else "—"
    draw_center(c, f"{hours} ساعت", x + metric_w / 2, y + h * 0.59, "FA-Bold", 7.2, INK)
    draw_center(c, f"{tests} تست", x + metric_w / 2, y + h * 0.27, "FA", 6.5, MUTED)

    # Subject and role on the visual right.
    c.setStrokeColor(GOLD_DARK)
    c.rect(x + w - 11, y + h - 13, 7, 7, fill=0, stroke=1)
    subject_lines = wrap_text(box["subject"], subject_w - 14, "FA-Bold", 7.0, 2)
    draw_lines_rtl(c, subject_lines, x + w - 14, y + h - 12, "FA-Bold", 7.0, 8.5, INK)
    draw_rtl(c, box["role"], x + w - 14, y + 5.5, "FA", 5.6, GOLD_DARK)

    # Topic and execution detail in the center.
    pad = 6
    topic_size = 6.8 if h >= 39 else 6.3
    detail_size = 5.6 if h >= 39 else 5.2
    topic_lines = wrap_text(box["topic"], center_w - 2 * pad, "FA-Bold", topic_size, 2)
    after = draw_lines_rtl(
        c,
        topic_lines,
        subject_x - pad,
        y + h - 11,
        "FA-Bold",
        topic_size,
        topic_size + 1.5,
        INK,
    )
    detail = ellipsize(box["detail"], center_w - 2 * pad, "FA", detail_size)
    draw_rtl(c, detail, subject_x - pad, max(y + 4.5, after - 1), "FA", detail_size, MUTED)

    draw_center(c, fa_digits(index), subject_x + 8, y + h / 2 - 2, "FA-Bold", 6.2, GOLD_DARK)


def draw_day_card(
    c: canvas.Canvas,
    day: dict,
    x: float,
    y_top: float,
    w: float,
    h: float,
) -> None:
    header_h = 27
    c.setFillColor(white)
    c.setStrokeColor(GOLD_DARK)
    c.setLineWidth(0.8)
    c.roundRect(x, y_top - h, w, h, 4, fill=1, stroke=1)
    c.setFillColor(GOLD)
    c.rect(x, y_top - header_h, w, header_h, fill=1, stroke=0)

    draw_rtl(c, f"{day['name']} {day['date']}", x + w - 8, y_top - 18, "FA-Bold", 9.2, INK)
    draw_center(c, day["phase"], x + w * 0.53, y_top - 18, "FA", 7.0, INK)
    total = f"جمع: {fa_digits(day['hours'])} ساعت | {fa_digits(day['tests'])} تست"
    draw_center(c, total, x + 84, y_top - 18, "FA-Bold", 6.7, INK)

    row_h = (h - header_h) / len(day["boxes"])
    for index, box in enumerate(day["boxes"], start=1):
        row_y = y_top - header_h - index * row_h
        draw_task_row(c, box, index, x, row_y, w, row_h)


def draw_friday_card(
    c: canvas.Canvas,
    friday: dict,
    x: float,
    y_top: float,
    w: float,
    h: float,
) -> None:
    c.setFillColor(ALERT)
    c.setStrokeColor(HexColor("#B84343"))
    c.roundRect(x, y_top - h, w, h, 4, fill=1, stroke=1)
    draw_rtl(c, f"{friday['date']} ـ {friday['title']}", x + w - 9, y_top - 18, "FA-Bold", 8.5, HexColor("#8B2C2C"))
    detail = ellipsize(friday["detail"], w - 18, "FA", 6.6)
    draw_rtl(c, detail, x + w - 9, y_top - 36, "FA", 6.6, INK)


def draw_schedule_page(
    c: canvas.Canvas,
    meta: dict,
    days: list[dict],
    page_number: int,
    week_label: str,
    date_range: str,
    friday: dict | None = None,
) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    start_y = draw_header(c, meta, page_number, week_label, date_range)
    bottom = 35
    gap = 7
    friday_h = 54 if friday else 0
    available = start_y - bottom - friday_h - (3 if friday else 2) * gap
    card_h = available / 3
    y_top = start_y
    for day in days:
        draw_day_card(c, day, MARGIN, y_top, PAGE_W - 2 * MARGIN, card_h)
        y_top -= card_h + gap
    if friday:
        draw_friday_card(c, friday, MARGIN, y_top, PAGE_W - 2 * MARGIN, friday_h)
    draw_footer(c, page_number)
    c.showPage()


def draw_metric(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    value: str,
    note: str,
    accent: Color,
) -> None:
    c.setFillColor(white)
    c.setStrokeColor(accent)
    c.roundRect(x, y, w, h, 5, fill=1, stroke=1)
    c.setFillColor(accent)
    c.roundRect(x + w - 7, y, 7, h, 3, fill=1, stroke=0)
    draw_rtl(c, title, x + w - 14, y + h - 17, "FA-Bold", 7.0, MUTED)
    draw_rtl(c, value, x + w - 14, y + h - 39, "FA-Bold", 14, accent)
    draw_rtl(c, note, x + w - 14, y + 8, "FA", 5.8, MUTED)


def draw_scopes_table(c: canvas.Canvas, data: dict, y_top: float) -> float:
    x = MARGIN
    w = PAGE_W - 2 * MARGIN
    header_h = 23
    row_h = 36
    col_widths = [w * 0.15, w * 0.41, w * 0.44]
    table_h = header_h + row_h * len(data["scopes"])
    c.setFillColor(white)
    c.setStrokeColor(LINE)
    c.roundRect(x, y_top - table_h, w, table_h, 4, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.rect(x, y_top - header_h, w, header_h, fill=1, stroke=0)
    headers = ["درس", "هفتهٔ اول: جاری", "هفتهٔ دوم: مرور پایه"]
    cursor = x
    for i, header in enumerate(headers):
        draw_center(c, header, cursor + col_widths[i] / 2, y_top - 15, "FA-Bold", 6.8, white)
        cursor += col_widths[i]

    for row_index, scope in enumerate(data["scopes"]):
        row_top = y_top - header_h - row_index * row_h
        if row_index % 2:
            c.setFillColor(HexColor("#FAFBFC"))
            c.rect(x, row_top - row_h, w, row_h, fill=1, stroke=0)
        values = [scope["subject"], scope["current"], scope["base"]]
        cursor = x
        for col_index, value in enumerate(values):
            c.setStrokeColor(LINE)
            c.line(cursor, row_top, cursor, row_top - row_h)
            lines = wrap_text(value, col_widths[col_index] - 10, "FA-Bold" if col_index == 0 else "FA", 6.1, 2)
            first_y = row_top - 14 if len(lines) == 1 else row_top - 11
            for line_no, line in enumerate(lines):
                draw_center(
                    c,
                    line,
                    cursor + col_widths[col_index] / 2,
                    first_y - line_no * 9,
                    "FA-Bold" if col_index == 0 else "FA",
                    6.1,
                    INK,
                )
            cursor += col_widths[col_index]
        c.setStrokeColor(LINE)
        c.line(x, row_top - row_h, x + w, row_top - row_h)
    return y_top - table_h


def draw_guide_page(c: canvas.Canvas, data: dict, page_number: int) -> None:
    meta = data["meta"]
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    start_y = draw_header(c, meta, page_number, "راهنمای اجرا و کنترل", "نسخهٔ استاندارد")

    gap = 7
    metric_w = (PAGE_W - 2 * MARGIN - 3 * gap) / 4
    metric_y = start_y - 67
    metrics = [
        ("دو هفته", "۹۴ ساعت", "۱۲ روز مطالعه", NAVY),
        ("کل تست", "۹۹۰ تست", "آزمون جمعه جداست", HexColor("#8B2C2C")),
        ("هر هفته", "۴۷ / ۴۹۵", "هسته بدون کاهش", HexColor("#177245")),
        ("باکس‌ها", "۵۴ باکس", "۲۷ باکس در هفته", GOLD_DARK),
    ]
    for index, item in enumerate(metrics):
        draw_metric(c, MARGIN + index * (metric_w + gap), metric_y, metric_w, 58, *item)

    y = metric_y - 19
    draw_rtl(c, "بودجهٔ کنترل‌شدهٔ آزمون", PAGE_W - MARGIN, y, "FA-Bold", 9.3, NAVY)
    y = draw_scopes_table(c, data, y - 8) - 17

    # Execution rules, two columns.
    draw_rtl(c, "قواعد اجرایی اصلاح‌شده", PAGE_W - MARGIN, y, "FA-Bold", 9.3, NAVY)
    y -= 13
    col_gap = 13
    col_w = (PAGE_W - 2 * MARGIN - col_gap) / 2
    left_x = MARGIN
    right_x = MARGIN + col_w + col_gap
    notes = data["execution_notes"]
    columns = [notes[4:], notes[:4]]  # visual left, then visual right
    box_h = 125
    for col_index, items in enumerate(columns):
        x = left_x if col_index == 0 else right_x
        c.setFillColor(white)
        c.setStrokeColor(LINE)
        c.roundRect(x, y - box_h, col_w, box_h, 4, fill=1, stroke=1)
        line_y = y - 15
        for item in items:
            c.setFillColor(GOLD)
            c.circle(x + col_w - 9, line_y + 2, 2.3, fill=1, stroke=0)
            lines = wrap_text(item, col_w - 24, "FA", 6.0, 3)
            line_y = draw_lines_rtl(c, lines, x + col_w - 16, line_y, "FA", 6.0, 8.3, INK) - 5

    y = y - box_h - 14
    c.setFillColor(ALERT)
    c.setStrokeColor(HexColor("#B84343"))
    c.roundRect(MARGIN, y - 62, PAGE_W - 2 * MARGIN, 62, 5, fill=1, stroke=1)
    draw_rtl(c, "دو هشدار امکان‌پذیری", PAGE_W - MARGIN - 9, y - 17, "FA-Bold", 8.2, HexColor("#8B2C2C"))
    warning1 = "۱) محدودهٔ تابع حدود ۷۷ صفحه است؛ این برنامه فقط وقتی استاندارد می‌ماند که بخش‌های پایه مرور باشند، نه آموزش کامل از صفر."
    warning2 = "۲) فاصله‌گذاری کامل شش باکس زیست با جفت‌روز و تست روزانهٔ ثابت جمع نمی‌شود؛ این خروجی هستهٔ ثابت را مقدم کرده است."
    draw_rtl(c, ellipsize(warning1, PAGE_W - 2 * MARGIN - 18, "FA", 6.3), PAGE_W - MARGIN - 9, y - 34, "FA", 6.3, INK)
    draw_rtl(c, ellipsize(warning2, PAGE_W - 2 * MARGIN - 18, "FA", 6.3), PAGE_W - MARGIN - 9, y - 50, "FA", 6.3, INK)

    source_y = y - 78
    draw_rtl(c, "منبع:", PAGE_W - MARGIN, source_y, "FA-Bold", 6.7, GOLD_DARK)
    draw_rtl(c, ellipsize(meta["source"], PAGE_W - 2 * MARGIN - 48, "FA", 6.2), PAGE_W - MARGIN - 38, source_y, "FA", 6.2, MUTED)
    draw_rtl(c, meta["scope"], PAGE_W - MARGIN, source_y - 13, "FA", 6.2, MUTED)
    draw_rtl(c, meta["formula_version"], PAGE_W - MARGIN, source_y - 26, "FA", 6.2, MUTED)

    draw_footer(c, page_number)
    c.showPage()


def generate(data_path: Path, output_path: Path) -> None:
    register_fonts()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    validate(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=A4, pageCompression=1)
    c.setTitle(data["meta"]["title"])
    c.setAuthor("Rankland corrected planning playbook")
    c.setSubject("Corrected standard plan for MAZ exam, 1 Aban 1405")
    c.setCreator("Arena.ai Agent Mode")

    days = data["days"]
    draw_schedule_page(
        c,
        data["meta"],
        days[0:3],
        1,
        "هفتهٔ اول ـ دوازدهم جاری",
        "۱۸ تا ۲۰ مهر",
    )
    draw_schedule_page(
        c,
        data["meta"],
        days[3:6],
        2,
        "هفتهٔ اول ـ دوازدهم جاری",
        "۲۱ تا ۲۴ مهر",
        data["fridays"]["week1"],
    )
    draw_schedule_page(
        c,
        data["meta"],
        days[6:9],
        3,
        "هفتهٔ دوم ـ دوازدهم، مرور پایه",
        "۲۵ تا ۲۷ مهر",
    )
    draw_schedule_page(
        c,
        data["meta"],
        days[9:12],
        4,
        "هفتهٔ دوم ـ دوازدهم، مرور پایه",
        "۲۸ مهر تا ۱ آبان",
        data["fridays"]["target"],
    )
    draw_guide_page(c, data, 5)
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
