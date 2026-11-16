#!/usr/bin/env python3
"""Build a podcast RSS feed from every audio file in episodes/.

Usage: build_feed.py <base_url> <output_dir>

- Each file's GUID is derived from its filename, so adding a new file
  never changes the identity of existing episodes.
- Each file's publish date is the date it was first committed to git,
  so dates stay stable too. (Needs a full clone: fetch-depth 0.)
- Title comes from the ID3 title tag if present, else the filename.
"""
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

try:
    from mutagen import File as MutagenFile
except ImportError:  # feed still works without durations/tags
    MutagenFile = None

FEED_TITLE = "Claude Audio"
FEED_DESCRIPTION = "Personal narrations."
FEED_AUTHOR = "John"
EPISODES_DIR = Path("episodes")
AUDIO_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4b": "audio/mp4",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
}


def first_commit_date(path: Path) -> datetime:
    """Date the file was first added to git; falls back to file mtime."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%aI", "--", str(path)],
            capture_output=True, text=True, check=True,
        ).stdout.split()
        if out:
            return datetime.fromisoformat(out[-1])
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def read_tags(path: Path):
    """Return (title, duration_seconds) from the file's tags, if readable."""
    title, duration = None, None
    if MutagenFile is not None:
        try:
            easy = MutagenFile(path, easy=True)
            if easy is not None:
                if easy.tags and easy.tags.get("title"):
                    title = str(easy.tags["title"][0]).strip() or None
                if getattr(easy, "info", None) and easy.info.length:
                    duration = int(round(easy.info.length))
        except Exception:
            pass
    return title, duration


def fmt_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    base_url = sys.argv[1].rstrip("/")
    out_dir = Path(sys.argv[2])
    out_eps = out_dir / "episodes"
    out_eps.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p for p in EPISODES_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_TYPES
    ) if EPISODES_DIR.is_dir() else []

    episodes = []
    for p in files:
        title, duration = read_tags(p)
        episodes.append({
            "path": p,
            "title": title or p.stem.replace("_", " ").replace("-", " ").strip(),
            "duration": duration,
            "date": first_commit_date(p),
            "guid": "claude-audio-" + hashlib.sha1(p.name.encode()).hexdigest(),
            "url": f"{base_url}/episodes/{quote(p.name)}",
            "size": p.stat().st_size,
            "type": AUDIO_TYPES[p.suffix.lower()],
        })
        shutil.copy2(p, out_eps / p.name)

    episodes.sort(key=lambda e: (e["date"], e["path"].name), reverse=True)
    now = format_datetime(datetime.now(timezone.utc))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">',
        "<channel>",
        f"<title>{escape(FEED_TITLE)}</title>",
        f"<link>{escape(base_url)}/</link>",
        f"<description>{escape(FEED_DESCRIPTION)}</description>",
        "<language>en-us</language>",
        f"<lastBuildDate>{now}</lastBuildDate>",
        f"<itunes:author>{escape(FEED_AUTHOR)}</itunes:author>",
        "<itunes:block>Yes</itunes:block>",
    ]
    for e in episodes:
        lines += [
            "<item>",
            f"<title>{escape(e['title'])}</title>",
            f"<guid isPermaLink=\"false\">{e['guid']}</guid>",
            f"<pubDate>{format_datetime(e['date'])}</pubDate>",
            f"<enclosure url=\"{escape(e['url'], {chr(34): '&quot;'})}\" "
            f"length=\"{e['size']}\" type=\"{e['type']}\"/>",
        ]
        if e["duration"]:
            lines.append(f"<itunes:duration>{fmt_duration(e['duration'])}</itunes:duration>")
        lines.append("</item>")
    lines += ["</channel>", "</rss>", ""]

    (out_dir / "feed.xml").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><meta name=robots content=noindex>"
        f"<title>{escape(FEED_TITLE)}</title>"
        f"<p>{len(episodes)} episode(s). Feed: <a href=\"feed.xml\">feed.xml</a></p>\n",
        encoding="utf-8",
    )
    (out_dir / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    print(f"Built feed with {len(episodes)} episode(s) at {base_url}/feed.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
