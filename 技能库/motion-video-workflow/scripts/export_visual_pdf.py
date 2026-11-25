#!/usr/bin/env python3
"""Extract explicitly selected frames and build a timestamped PDF on macOS."""
import argparse
import concurrent.futures
import hashlib
import json
import math
import platform
import shutil
import subprocess
from pathlib import Path

from chapters import seconds


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(path, base):
    path = Path(path)
    return (path if path.is_absolute() else base / path).resolve()


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True))


def load_chapters(path, duration):
    if not path:
        return []
    if path.suffix.lower() == ".json":
        value = read_json(path)
        rows = value["chapters"] if isinstance(value, dict) else value
    else:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                start, title = line.strip().split(maxsplit=1)
                rows.append({"start": start, "title": title})
    result = []
    for row in rows:
        time, title = seconds(row["start"]), row["title"].strip()
        if time >= duration or not title or "\n" in title or "\r" in title:
            raise ValueError("Invalid PDF chapter")
        if result and time <= result[-1]["start"]:
            raise ValueError("PDF chapter times must strictly increase")
        result.append({"start": time, "title": title})
    return result


def build(args):
    if platform.system() != "Darwin":
        raise ValueError("This dependency-free PDF backend needs macOS; use the available PDF skill elsewhere")
    for tool in ("ffmpeg", "ffprobe", "clang"):
        if not shutil.which(tool):
            raise ValueError(f"Missing {tool}; use the available PDF skill or existing environment")
    args.out = args.out.resolve()
    if args.out.suffix.lower() != ".pdf":
        raise ValueError("--out must end in .pdf")
    if not 1 <= args.workers <= 4:
        raise ValueError("--workers must be between 1 and 4")
    data = read_json(args.manifest)
    if not isinstance(data, dict):
        raise ValueError("Manifest must be a JSON object")
    base = args.manifest.resolve().parent
    video = resolve(args.video or data.get("source_video"), base) if (
        args.video or data.get("source_video")) else None
    details = probe(video) if video else None
    duration = seconds(details["format"]["duration"] if video else data["duration"])
    chapters = load_chapters(args.chapters, duration)
    entries = data.get("frames", data.get("pages"))
    if not isinstance(entries, list) or not entries:
        raise ValueError("Manifest needs a nonempty frames or pages list")
    pages = []
    for row in entries:
        if not isinstance(row, dict) or not isinstance(row.get("title"), str):
            raise ValueError("Each frame needs a text title")
        time = seconds(row["time"])
        start = seconds(row.get("scene_start", row.get("start", time)))
        end = seconds(row.get("scene_end", row.get("end", duration)))
        if not 0 <= start <= time < end <= duration + .001:
            raise ValueError(f"Frame or scene outside its source duration: {row}")
        title = row["title"].strip()
        if not title or "\n" in title:
            raise ValueError("Each frame needs a single-line title")
        page = {"time": time, "start": start, "end": end,
                "title": title, "state": row.get("state", "完整画面")}
        if not video:
            page["image"] = str(resolve(row["file"], base))
            if not Path(page["image"]).is_file():
                raise ValueError(f"Missing preview image: {page['image']}")
        pages.append(page)
    pages.sort(key=lambda row: row["time"])
    if len({row["time"] for row in pages}) != len(pages):
        raise ValueError("Duplicate frame times; select independent states explicitly")
    work = args.out.parent / (args.out.stem + "_assets")
    work.mkdir(parents=True, exist_ok=True)
    if video:
        fingerprint = {"path": str(video), "bytes": video.stat().st_size,
                       "mtime_ns": video.stat().st_mtime_ns}
        key = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()[:12]

        def extract(pair):
            index, page = pair
            frame_key = hashlib.sha256(str(page["time"]).encode()).hexdigest()[:8]
            image = work / f"{index:04}_{key}_{frame_key}.jpg"
            if not image.exists():
                subprocess.run([
                    "ffmpeg", "-y", "-v", "error", "-threads", "2", "-ss", str(page["time"]),
                    "-i", str(video), "-frames:v", "1", "-q:v", "2", str(image)
                ], check=True, capture_output=True)
            page["image"] = str(image)

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(extract, enumerate(pages, 1)))
    else:
        fingerprint = {"preview": data.get("source_label", "同版预览；非最终成片时间")}
    first = next(s for s in probe(Path(pages[0]["image"]))["streams"] if s["codec_type"] == "video")
    width = 960 if first["width"] >= first["height"] else 540
    height = math.ceil(width * first["height"] / first["width"]) + 52
    front = 1 + math.ceil(len(chapters) / 10)
    for chapter in chapters:
        candidates = [i for i, p in enumerate(pages) if p["start"] <= chapter["start"] < p["end"]]
        if not candidates:
            candidates = [i for i, p in enumerate(pages) if p["time"] >= chapter["start"]]
        chapter["pdf_page"] = (candidates[0] if candidates else len(pages) - 1) + front + 1
    count = front + len(pages)
    checks = sorted({1, front + 1, count} | {
        round(1 + (count - 1) * i / min(8, count - 1)) for i in range(min(8, count - 1) + 1)
    })
    if args.check_pages:
        checks = sorted(set(checks) | {int(n) for n in args.check_pages.split(",")})
    if any(n < 1 or n > count for n in checks):
        raise ValueError("QA page outside PDF page count")
    job = {"output": str(args.out), "title": args.title or data.get("title", args.out.stem),
           "source_label": video.name if video else fingerprint["preview"],
           "page_width": width, "page_height": height, "pages": pages,
           "chapters": chapters, "check_pages": checks, "qa_dir": str(work / "qa"),
           "report": str(work / "report.json"), "source_fingerprint": fingerprint}
    job_path = work / "job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    source = Path(__file__).with_name("visual_pdf_macos.m")
    binary = work / ("native_pdf_" + hashlib.sha256(source.read_bytes()).hexdigest()[:12])
    if not binary.exists():
        subprocess.run(["clang", "-fobjc-arc", "-O2", str(source), "-framework", "Foundation",
                        "-framework", "CoreGraphics", "-framework", "CoreText",
                        "-framework", "ImageIO", "-o", str(binary)], check=True, capture_output=True)
    subprocess.run([str(binary), str(job_path)], check=True)
    report = read_json(work / "report.json")
    if report["pages"] != count or report["frames"] != len(pages):
        raise ValueError("Generated PDF count mismatch")
    print(f"{args.out}\nInspect the re-rendered pages in {work / 'qa'} before delivery.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--title")
    parser.add_argument("--chapters", type=Path, help="Resolved chapter JSON or HH:MM:SS title TXT")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--check-pages", help="Additional PDF page numbers to re-render, e.g. 3,12,18")
    args = parser.parse_args()
    try:
        build(args)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.decode(errors="replace") if isinstance(
            exc, subprocess.CalledProcessError) and isinstance(exc.stderr, bytes) else str(exc)
        parser.error(detail or str(exc))


if __name__ == "__main__":
    main()
