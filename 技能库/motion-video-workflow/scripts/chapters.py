#!/usr/bin/env python3
"""Validate selected chapter titles and format final-video timestamps. Stdlib only."""
import argparse
import json
import math
from pathlib import Path


def seconds(value):
    if isinstance(value, bool):
        raise ValueError("Time must be seconds or HH:MM:SS")
    if isinstance(value, str) and ":" in value:
        fields = value.split(":")
        if len(fields) != 3 or any(not s.isdigit() for s in fields):
            raise ValueError(f"Invalid HH:MM:SS: {value}")
        h, m, s = map(int, fields)
        if m >= 60 or s >= 60:
            raise ValueError(f"Invalid HH:MM:SS: {value}")
        value = h * 3600 + m * 60 + s
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Time must be finite and nonnegative")
    return value


def unit_starts(assembly_path):
    assembly = json.loads(assembly_path.read_text(encoding="utf-8"))
    starts = {}
    for part in assembly["parts"]:
        folder = Path(part["path"])
        if not folder.is_absolute():
            folder = assembly_path.parent / folder
        plan = json.loads((folder / "visual_plan.json").read_text(encoding="utf-8"))
        offset = seconds(part["global_start"])
        for unit in plan.get("units", []):
            key = int(unit["index"])
            if key in starts:
                raise ValueError(f"Ambiguous unit index: {key}")
            starts[key] = offset + seconds(unit["start"])
    return starts, seconds(assembly["duration"])


def format_chapters(entries, duration, starts, max_chapters, max_title, min_gap):
    if not isinstance(entries, list) or not 1 <= len(entries) <= max_chapters:
        raise ValueError(f"Provide 1 to {max_chapters} chapters")
    rows = []
    previous = None
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("title"), str):
            raise ValueError("Each chapter needs a text title")
        title = entry["title"].strip()
        if not title or len(title) > max_title or any(c in title for c in "\r\n\t"):
            raise ValueError(f"Title must be one line, 1-{max_title} characters: {title!r}")
        if ("start" in entry) == ("unit" in entry):
            raise ValueError("Each chapter needs exactly one of start or unit")
        if "unit" in entry:
            key = int(entry["unit"])
            if key not in starts:
                raise ValueError(f"Unit {key} not found; supply the matching --assembly")
            time = starts[key]
        else:
            time = seconds(entry["start"])
        if time >= duration:
            raise ValueError(f"Chapter is outside the video: {title}")
        whole = math.floor(time)
        if previous is None and whole != 0:
            raise ValueError("The first chapter must start at 00:00:00")
        if previous is not None and (whole <= previous or whole - previous < min_gap):
            raise ValueError(f"Chapters must increase with at least {min_gap:g}s gap: {title}")
        rows.append(f"{whole // 3600:02}:{whole // 60 % 60:02}:{whole % 60:02} {title}")
        previous = whole
    return "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON list or {chapters:[...]}")
    parser.add_argument("--assembly", type=Path)
    parser.add_argument("--duration", type=seconds, help="Final video duration in seconds or HH:MM:SS")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--max-chapters", type=int, default=10)
    parser.add_argument("--max-title-length", type=int, default=16)
    parser.add_argument("--min-gap", type=float, default=5)
    args = parser.parse_args()
    try:
        if (args.max_chapters < 1 or args.max_title_length < 1 or args.min_gap < 0
                or not math.isfinite(args.min_gap)):
            raise ValueError("Limits must be positive; min-gap may be zero")
        data = json.loads(args.input.read_text(encoding="utf-8"))
        entries = data["chapters"] if isinstance(data, dict) else data
        starts, assembled_duration = unit_starts(args.assembly) if args.assembly else ({}, None)
        if (assembled_duration is not None and args.duration is not None
                and abs(args.duration - assembled_duration) > .1):
            raise ValueError("Duration differs from the assembly; supply the final edited timeline")
        duration = args.duration if args.duration is not None else assembled_duration
        if duration is None or duration <= 0:
            raise ValueError("Supply final --duration or a matching --assembly")
        text = format_chapters(entries, duration, starts, args.max_chapters,
                               args.max_title_length, args.min_gap)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        print(text, end="")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
