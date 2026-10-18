#!/usr/bin/env python3
"""Put the corrected 1 Aban Rankland schedule into the original DOCX template.

This generator deliberately edits only ``word/document.xml`` inside the source
OOXML package.  Table geometry, paragraph/run formatting, embedded fonts,
images, relationships, styles, and all other template parts are copied byte for
byte.  It therefore requires the original Word file as ``--template`` input.

No third-party Python package is required.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "examples" / "1aban-1405-rankland-corrected.json"
DEFAULT_OUTPUT = (
    ROOT / "برنامه جدیید" / "برنامه-اصلاح‌شده-رتبه‌لند-۱-آبان-۱۴۰۵.docx"
)
DOCUMENT_XML = "word/document.xml"

PARAGRAPH_RE = re.compile(r"<w:p(?:\s[^>]*)?>.*?</w:p>", re.DOTALL)
TEXT_RE = re.compile(r"(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)", re.DOTALL)
DAY_HEADER_RE = re.compile(
    r"^(شنبه|یکشنبه|دوشنبه|سه[‌ ]شنبه|چهارشنبه|پنجشنبه|جمعه) \|"
)

# The template uses fixed-height rows.  These semantically equivalent compact
# instructions keep the corrected rules visible instead of letting Word clip a
# fifth line in the shorter rows on pages 2 and 4.  Topics, hours, tests, and
# the rule categories themselves are unchanged.
DOCX_DETAIL_OVERRIDES = {
    "حل حداکثر ۶۰د، ۱۰د تصحیح و تحلیل غلط/سفید/شک‌دار و نکته‌دار": (
        "حل تا ۶۰د؛ تحلیل غلط/سفید/شک‌دار/نکته‌دار"
    ),
    "زمان‌دار؛ حل حداکثر ۷۵د، ۱۰د تصحیح و تحلیل غلط/سفید/شک‌دار": (
        "زمان‌دار؛ حل تا ۷۵د؛ تحلیل غلط/سفید/شک‌دار"
    ),
    "۲۰ تست بازیابی از مرور دوشنبه؛ تحلیل غلط/سفید/شک‌دار": (
        "۲۰ تست بازیابی دوشنبه؛ تحلیل غلط/سفید/شک‌دار"
    ),
    "مرور سبک و بازیابی متن/شکل؛ مبحث سنگین جدید ممنوع": (
        "مرور سبک متن/شکل؛ بدون مبحث سنگین جدید"
    ),
}


@dataclass(frozen=True)
class Paragraph:
    start: int
    end: int
    xml: str
    text: str


def subject_family(subject: str) -> str:
    for family in ("زیست", "ریاضی", "فیزیک", "شیمی"):
        if subject.startswith(family):
            return family
    return ""


def docx_detail(value: str) -> str:
    """Return a fixed-row-safe wording without changing the instruction."""
    return DOCX_DETAIL_OVERRIDES.get(value, value)


def fa_digits(value: object) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def validate_data(data: dict) -> None:
    """Check the approved standard core before touching the template."""
    days = data.get("days", [])
    if len(days) != 12:
        raise ValueError(f"Expected 12 study days, got {len(days)}")

    expected_hours = [8, 7, 9, 7, 9, 7]
    expected_tests = [70, 55, 100, 85, 100, 85]
    expected_subjects = {
        "زیست": (15, 120),
        "ریاضی": (11, 150),
        "فیزیک": (12, 150),
        "شیمی": (9, 75),
    }

    for week in (1, 2):
        current = [day for day in days if day["week"] == week]
        if len(current) != 6:
            raise ValueError(f"Week {week}: expected 6 study days")
        if [day["hours"] for day in current] != expected_hours:
            raise ValueError(f"Week {week}: wrong daily-hour distribution")
        if [day["tests"] for day in current] != expected_tests:
            raise ValueError(f"Week {week}: wrong daily-test distribution")

        totals = {family: [0, 0] for family in expected_subjects}
        for day in current:
            if sum(box["hours"] for box in day["boxes"]) != day["hours"]:
                raise ValueError(f"{day['date']}: box hours do not match day total")
            if sum(box["tests"] for box in day["boxes"]) != day["tests"]:
                raise ValueError(f"{day['date']}: box tests do not match day total")
            for box in day["boxes"]:
                family = subject_family(box["subject"])
                if not family:
                    raise ValueError(f"Unknown subject: {box['subject']}")
                totals[family][0] += box["hours"]
                totals[family][1] += box["tests"]

        for family, expected in expected_subjects.items():
            if tuple(totals[family]) != expected:
                raise ValueError(
                    f"Week {week}: {family} total {tuple(totals[family])}, "
                    f"expected {expected}"
                )

    if sum(day["hours"] for day in days) != 94:
        raise ValueError("Two-week hours do not sum to 94")
    if sum(day["tests"] for day in days) != 990:
        raise ValueError("Two-week tests do not sum to 990")
    if sum(len(day["boxes"]) for day in days) != 54:
        raise ValueError("The two-week plan must contain 54 boxes")


def paragraph_text(paragraph_xml: str) -> str:
    return "".join(html.unescape(match.group(2)) for match in TEXT_RE.finditer(paragraph_xml))


def paragraphs(document_xml: str) -> list[Paragraph]:
    result: list[Paragraph] = []
    for match in PARAGRAPH_RE.finditer(document_xml):
        text = paragraph_text(match.group(0))
        if text:
            result.append(Paragraph(match.start(), match.end(), match.group(0), text))
    return result


def replace_paragraph_text(paragraph_xml: str, value: str) -> str:
    """Replace visible text while retaining the paragraph and run formatting."""
    matches = list(TEXT_RE.finditer(paragraph_xml))
    if not matches:
        raise ValueError("Cannot replace a paragraph that has no w:t element")

    replacement = escape(value, {'"': "&quot;"})
    chunks: list[str] = []
    cursor = 0
    for number, match in enumerate(matches):
        chunks.append(paragraph_xml[cursor : match.start()])
        chunks.append(match.group(1))
        chunks.append(replacement if number == 0 else "")
        chunks.append(match.group(3))
        cursor = match.end()
    chunks.append(paragraph_xml[cursor:])
    return "".join(chunks)


def find_unique_text(items: list[Paragraph], value: str) -> int:
    found = [index for index, item in enumerate(items) if item.text == value]
    if len(found) != 1:
        raise ValueError(f"Expected one paragraph {value!r}, found {len(found)}")
    return found[0]


def replace_all_exact(
    items: list[Paragraph], replacements: dict[int, str], old: str, new: str, count: int
) -> None:
    found = [index for index, item in enumerate(items) if item.text == old]
    if len(found) != count:
        raise ValueError(f"Expected {count} occurrences of {old!r}, found {len(found)}")
    for index in found:
        replacements[index] = new


def locate_day_end(items: list[Paragraph], start: int) -> int:
    for index in range(start + 1, len(items)):
        if DAY_HEADER_RE.match(items[index].text):
            return index
    return len(items)


def numeric_values_after(
    items: list[Paragraph], start: int, end: int, label: str
) -> list[str]:
    values: list[str] = []
    for index in range(start, end - 1):
        if items[index].text != label:
            continue
        candidate = items[index + 1].text
        if re.fullmatch(r"[۰-۹]+", candidate):
            values.append(candidate)
    return values


def build_replacements(items: list[Paragraph], data: dict) -> dict[int, str]:
    replacements: dict[int, str] = {}

    # The student remains a twelfth-grader in week 2; only the content is a
    # review of grade 10.  The source template labels both fields as grade 10.
    replace_all_exact(
        items,
        replacements,
        "هفته: ۲ ـ دهم",
        "هفته: ۲ ـ مرور پایهٔ دهم",
        2,
    )
    replace_all_exact(
        items,
        replacements,
        "تجربی / دهم",
        "تجربی / دوازدهم",
        2,
    )

    mapped_boxes = 0
    for day in data["days"]:
        header = f"{day['name']} | {day['date']}"
        start = find_unique_text(items, header)
        end = locate_day_end(items, start)
        cursor = start + 1

        for box in day["boxes"]:
            subject_text = f"☐ {box['subject']}"
            subject_index = next(
                (
                    index
                    for index in range(cursor, end)
                    if items[index].text == subject_text
                ),
                None,
            )
            if subject_index is None:
                raise ValueError(f"{header}: could not find box {subject_text!r}")
            if subject_index + 2 >= end:
                raise ValueError(f"{header}: incomplete box after {subject_text!r}")

            topic_index = subject_index + 1
            detail_index = subject_index + 2
            if items[topic_index].text.startswith(("☐ ", "ساعت:", "تست:")):
                raise ValueError(f"{header}: missing topic after {subject_text!r}")
            if items[detail_index].text.startswith(("☐ ", "ساعت:", "تست:")):
                raise ValueError(f"{header}: missing detail after {subject_text!r}")

            replacements[subject_index] = subject_text
            replacements[topic_index] = box["topic"]
            replacements[detail_index] = docx_detail(box["detail"])
            cursor = detail_index + 1
            mapped_boxes += 1

    if mapped_boxes != 54:
        raise ValueError(f"Expected to map 54 boxes, mapped {mapped_boxes}")

    friday_specs = [
        (
            "جمعه | ۲۴ مهر",
            data["fridays"]["week1"]["title"],
            data["fridays"]["week1"]["detail"],
        ),
        (
            "جمعه | ۱ آبان",
            data["fridays"]["target"]["title"],
            data["fridays"]["target"]["detail"],
        ),
    ]
    for header, title, detail in friday_specs:
        start = find_unique_text(items, header)
        end = locate_day_end(items, start)
        replacements[start + 1] = title
        task = next(
            (
                index
                for index in range(start + 1, end)
                if items[index].text == "☐ درس، آزمون یا مبحث:"
            ),
            None,
        )
        if task is None or task + 1 >= end:
            raise ValueError(f"{header}: could not locate Friday detail field")
        replacements[task + 1] = detail

    return replacements


def apply_replacements(
    document_xml: str, items: list[Paragraph], replacements: dict[int, str]
) -> str:
    chunks: list[str] = []
    cursor = 0
    for index, item in enumerate(items):
        chunks.append(document_xml[cursor : item.start])
        if index in replacements:
            chunks.append(replace_paragraph_text(item.xml, replacements[index]))
        else:
            chunks.append(item.xml)
        cursor = item.end
    chunks.append(document_xml[cursor:])
    return "".join(chunks)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_docx(template: Path, output: Path, document_xml: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)

    try:
        with zipfile.ZipFile(template, "r") as source, zipfile.ZipFile(
            temporary, "w"
        ) as target:
            target.comment = source.comment
            for info in source.infolist():
                payload = source.read(info.filename)
                if info.filename == DOCUMENT_XML:
                    payload = document_xml.encode("utf-8")
                target.writestr(info, payload)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def verify_output(template: Path, output: Path, data: dict) -> dict[str, int]:
    with zipfile.ZipFile(template) as source, zipfile.ZipFile(output) as result:
        if result.testzip() is not None:
            raise ValueError("The generated DOCX contains a corrupt ZIP member")
        if source.namelist() != result.namelist():
            raise ValueError("OOXML package entries changed")

        changed: list[str] = []
        for name in source.namelist():
            if digest(source.read(name)) != digest(result.read(name)):
                changed.append(name)
        if changed != [DOCUMENT_XML]:
            raise ValueError(f"Unexpected changed OOXML parts: {changed}")

        source_xml = source.read(DOCUMENT_XML).decode("utf-8")
        result_xml = result.read(DOCUMENT_XML).decode("utf-8")
        source_pages = source.read("docProps/app.xml")
        result_pages = result.read("docProps/app.xml")
        part_count = len(result.infolist())

    if source_xml.count('w:type="page"') != 3:
        raise ValueError("The template does not have the expected three page breaks")
    if result_xml.count('w:type="page"') != 3:
        raise ValueError("Generated DOCX page-break count changed")
    if source_pages != result_pages or b"<Pages>4</Pages>" not in result_pages:
        raise ValueError("Stored four-page template metadata changed")

    result_items = paragraphs(result_xml)
    texts = [item.text for item in result_items]
    for day in data["days"]:
        header = f"{day['name']} | {day['date']}"
        if texts.count(header) != 1:
            raise ValueError(f"Generated DOCX is missing day header {header!r}")
        start = texts.index(header)
        end = locate_day_end(result_items, start)
        for box in day["boxes"]:
            if box["topic"] not in texts or docx_detail(box["detail"]) not in texts:
                raise ValueError(f"Generated DOCX is missing content for {header}")

        actual_hours = numeric_values_after(result_items, start, end, "ساعت:")
        actual_tests = numeric_values_after(result_items, start, end, "تست:")
        expected_hours = [fa_digits(box["hours"]) for box in day["boxes"]]
        expected_tests = [fa_digits(box["tests"]) for box in day["boxes"]]
        if actual_hours != expected_hours or actual_tests != expected_tests:
            raise ValueError(f"Generated DOCX has wrong box totals for {header}")
        if fa_digits(day["hours"]) not in texts[start : start + 7]:
            raise ValueError(f"Generated DOCX has wrong daily hours for {header}")
        if fa_digits(day["tests"]) not in texts[start : start + 9]:
            raise ValueError(f"Generated DOCX has wrong daily tests for {header}")

    if texts.count("هفته: ۲ ـ مرور پایهٔ دهم") != 2:
        raise ValueError("Week-2 review label was not written twice")
    if texts.count("تجربی / دوازدهم") != 4:
        raise ValueError("Student grade is not twelfth grade on all four pages")
    if any(
        "تحلیل همهٔ گزینه‌ها" in text and "نه همهٔ گزینه‌ها" not in text
        for text in texts
    ):
        raise ValueError("An obsolete blanket-analysis instruction remains")

    return {
        "days": len(data["days"]),
        "boxes": sum(len(day["boxes"]) for day in data["days"]),
        "hours": sum(day["hours"] for day in data["days"]),
        "tests": sum(day["tests"] for day in data["days"]),
        "pages": 4,
        "ooxml_parts": part_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        type=Path,
        required=True,
        help="Original Rankland .docx file downloaded from Google Drive",
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.template.is_file():
        raise FileNotFoundError(f"Template not found: {args.template}")

    data = json.loads(args.data.read_text(encoding="utf-8"))
    validate_data(data)

    with zipfile.ZipFile(args.template) as archive:
        if archive.testzip() is not None:
            raise ValueError("The source template is corrupt")
        source_xml = archive.read(DOCUMENT_XML).decode("utf-8")

    source_items = paragraphs(source_xml)
    replacements = build_replacements(source_items, data)
    result_xml = apply_replacements(source_xml, source_items, replacements)
    if result_xml == source_xml:
        raise ValueError("No text changed in the template")

    write_docx(args.template, args.output, result_xml)
    summary = verify_output(args.template, args.output, data)
    print(f"Created: {args.output}")
    print(
        "QA: {days} days, {boxes} boxes, {hours} hours, {tests} tests, "
        "{pages} stored pages; only word/document.xml changed".format(**summary)
    )


if __name__ == "__main__":
    main()
