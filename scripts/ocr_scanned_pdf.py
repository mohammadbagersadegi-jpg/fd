#!/usr/bin/env python3
"""Create a searchable PDF from an image-only Persian PDF without changing its appearance.

The original PDF pages are preserved byte-for-byte at the page-content level; an invisible
Unicode text layer is added from Tesseract OCR. OCR checkpoints are written per page, so an
interrupted run can be resumed safely.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pymupdf
from PIL import Image
import tesserocr
from tesserocr import PSM, RIL

FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.replace("\x0c", " ").split())


def ocr_document(
    source: Path,
    checkpoint_dir: Path,
    tessdata: Path,
    dpi: int,
    language: str,
) -> list[dict]:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(source)
    results: list[dict] = []

    with tesserocr.PyTessBaseAPI(
        path=str(tessdata.resolve()), lang=language, psm=PSM.AUTO
    ) as api:
        api.SetVariable("preserve_interword_spaces", "1")
        for page_number, page in enumerate(document):
            checkpoint = checkpoint_dir / f"page-{page_number + 1:04d}.json"
            if checkpoint.exists():
                data = json.loads(checkpoint.read_text(encoding="utf-8"))
                results.append(data)
                print(
                    f"[{source.name}] {page_number + 1}/{len(document)} cached",
                    flush=True,
                )
                continue

            started = time.monotonic()
            pixmap = page.get_pixmap(
                dpi=dpi, alpha=False, colorspace=pymupdf.csRGB
            )
            image = Image.frombytes(
                "RGB", [pixmap.width, pixmap.height], pixmap.samples
            )
            api.SetImage(image)
            api.Recognize()
            full_text = (api.GetUTF8Text() or "").strip()
            mean_confidence = float(api.MeanTextConf())

            scale_x = page.rect.width / pixmap.width
            scale_y = page.rect.height / pixmap.height
            words: list[list] = []
            iterator = api.GetIterator()
            while iterator:
                value = clean_text(iterator.GetUTF8Text(RIL.WORD))
                if value:
                    box = iterator.BoundingBox(RIL.WORD)
                    confidence = float(iterator.Confidence(RIL.WORD))
                    if box and confidence >= 15:
                        x0, y0, x1, y1 = box
                        words.append(
                            [
                                round(x0 * scale_x, 3),
                                round(y0 * scale_y, 3),
                                round(x1 * scale_x, 3),
                                round(y1 * scale_y, 3),
                                value,
                                round(confidence, 2),
                            ]
                        )
                if not iterator.Next(RIL.WORD):
                    break

            data = {
                "page": page_number + 1,
                "width": round(page.rect.width, 3),
                "height": round(page.rect.height, 3),
                "dpi": dpi,
                "language": language,
                "mean_confidence": mean_confidence,
                "text": full_text,
                "words": words,
            }
            temporary = checkpoint.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            temporary.replace(checkpoint)
            results.append(data)
            elapsed = time.monotonic() - started
            print(
                f"[{source.name}] {page_number + 1}/{len(document)} "
                f"words={len(words)} conf={mean_confidence:.0f} time={elapsed:.1f}s",
                flush=True,
            )

    return results


def write_text_outputs(source: Path, results: list[dict], output_dir: Path) -> None:
    text_dir = output_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    text_path = text_dir / f"{source.stem}-OCR.txt"
    chunks = []
    for item in results:
        chunks.append(f"\n\n===== صفحهٔ اسکن {item['page']} =====\n\n{item['text']}")
    text_path.write_text("".join(chunks).strip() + "\n", encoding="utf-8")

    manifest = {
        "source": source.name,
        "pages": len(results),
        "average_confidence": round(
            sum(item["mean_confidence"] for item in results) / max(len(results), 1),
            2,
        ),
        "pages_with_text": sum(bool(item["text"].strip()) for item in results),
        "word_count": sum(len(item["words"]) for item in results),
        "ocr_language": results[0]["language"] if results else None,
        "dpi": results[0]["dpi"] if results else None,
    }
    (text_dir / f"{source.stem}-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_searchable_pdf(
    source: Path, results: list[dict], output: Path, title: str | None
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(source)
    if len(document) != len(results):
        raise RuntimeError(
            f"Page mismatch: source has {len(document)}, OCR has {len(results)}"
        )

    font_name = "ocr-persian"
    for index, (page, item) in enumerate(zip(document, results), start=1):
        page.insert_font(fontname=font_name, fontfile=FONT_FILE)
        for x0, y0, x1, y1, word, _confidence in item["words"]:
            rect = pymupdf.Rect(x0, y0, x1, y1)
            if rect.is_empty or rect.height < 0.5:
                continue
            font_size = max(2.0, min(rect.height * 0.82, 20.0))
            baseline = max(rect.y0 + font_size, rect.y1 - rect.height * 0.08)
            try:
                page.insert_text(
                    (rect.x0, baseline),
                    word,
                    fontsize=font_size,
                    fontname=font_name,
                    render_mode=3,
                    overlay=True,
                )
            except Exception as exc:
                print(
                    f"warning: page {index}, skipped word {word!r}: {exc}",
                    file=sys.stderr,
                )

    metadata = dict(document.metadata or {})
    if title:
        metadata["title"] = title
    metadata["keywords"] = "OCR, Persian, searchable PDF"
    metadata["producer"] = "Tesseract 5.5.1 + PyMuPDF; original scan preserved"
    document.set_metadata(metadata)

    temporary = output.with_suffix(".pdf.tmp")
    document.save(
        temporary,
        garbage=4,
        deflate=True,
        deflate_fonts=True,
        clean=False,
    )
    document.close()
    temporary.replace(output)


def validate(source: Path, output: Path, results: list[dict]) -> dict:
    source_document = pymupdf.open(source)
    output_document = pymupdf.open(output)
    extracted = [len(page.get_text("text").strip()) for page in output_document]
    report = {
        "source": source.name,
        "output": output.name,
        "source_pages": len(source_document),
        "output_pages": len(output_document),
        "source_size": source.stat().st_size,
        "output_size": output.stat().st_size,
        "ocr_pages_with_text": sum(bool(item["text"].strip()) for item in results),
        "pdf_pages_with_extractable_text": sum(count > 0 for count in extracted),
        "extracted_characters": sum(extracted),
        "average_confidence": round(
            sum(item["mean_confidence"] for item in results) / max(len(results), 1),
            2,
        ),
        "page_count_match": len(source_document) == len(output_document),
    }
    if not report["page_count_match"]:
        raise RuntimeError("Output page count differs from source")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--tessdata", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--language", default="fas")
    parser.add_argument("--title")
    parser.add_argument("--text-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checkpoint_dir = args.work_dir / "checkpoints" / args.source.stem
    results = ocr_document(
        args.source, checkpoint_dir, args.tessdata, args.dpi, args.language
    )
    write_text_outputs(args.source, results, args.work_dir)
    if args.text_only:
        return
    build_searchable_pdf(args.source, results, args.output, args.title)
    report = validate(args.source, args.output, results)
    report_path = args.work_dir / "text" / f"{args.source.stem}-validation.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
