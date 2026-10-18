#!/usr/bin/env python3
"""دریافت متن/زیرنویس ویدیو (یوتیوب/آپارات) برای یادگیری روش‌ها.

ترتیب تلاش (اولین موفق برنده):
  1) youtube-transcript-api   (سریع‌ترین، بدون کلید)
  2) yt-dlp --write-sub/--write-auto-sub
  3) webpeel (npx)
خروجی: web-capture/video-<slug>.md
نکته: داخل سندباکس فعلی اینترنت عمومی مسدود است؛ در آن حالت این اسکریپت خطای شبکه می‌دهد و
مسیر جایگزین، دریافت ترنسکریپت صفحهٔ watch با fetcher پلتفرم است (مثل video-doctorsemi-1402.md).
"""
import re
import subprocess
import sys
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "web-capture"
OUT.mkdir(exist_ok=True)


def slug(url: str) -> str:
    m = re.search(r"(?:v=|/v/|watch\?v=)([\w-]{6,})", url)
    return m.group(1) if m else re.sub(r"\W+", "-", url)[:60]


def via_yta(url: str):
    from youtube_transcript_api import YouTubeTranscriptApi
    vid = slug(url)
    api = YouTubeTranscriptApi()
    tr = api.fetch(vid, languages=["fa", "en"])
    return "\n".join(f"[{int(s.start//60):02d}:{int(s.start%60):02d}] {s.text}" for s in tr)


def via_ytdlp(url: str):
    out = OUT / f"_subs_{slug(url)}"
    subprocess.run(
        ["yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
         "--sub-langs", "fa,en", "--sub-format", "vtt", "-o", str(out), url],
        check=True, capture_output=True, timeout=300)
    vtts = sorted(OUT.glob(f"_subs_{slug(url)}*.vtt"))
    return vtts[0].read_text(encoding="utf-8", errors="replace") if vtts else ""


def via_webpeel(url: str):
    r = subprocess.run(["webpeel", url], check=True, capture_output=True, timeout=300)
    return r.stdout.decode("utf-8", "replace")


def main(url: str):
    for name, fn in (("youtube-transcript-api", via_yta), ("yt-dlp", via_ytdlp), ("webpeel", via_webpeel)):
        try:
            text = fn(url)
            if text and len(text) > 200:
                dst = OUT / f"video-{slug(url)}.md"
                dst.write_text(f"# capture {url}\n# via {name}\n\n{text}\n", encoding="utf-8")
                print(f"OK via {name} -> {dst} ({len(text)} chars)")
                return 0
        except Exception as e:  # noqa: BLE001
            print(f"fail {name}: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
    print("همهٔ مسیرها شکست خوردند؛ از fetcher پلتفرم روی صفحهٔ watch استفاده کنید.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else input("video url: ")))
