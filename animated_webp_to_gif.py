#!/usr/bin/env python3
"""
Recursively find *.webp under 原图/ (by default). Animated WebP -> same-stem .gif
(then remove the .webp). Static WebP unchanged. Default 10 worker threads.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from PIL import Image, ImageSequence
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "This script requires Pillow. Install it with: python3 -m pip install pillow"
    ) from exc


# 只处理已编号的成品动图（避免误处理未编号的素材）
OUTPUT_NAME_RE = re.compile(r"^(\d+)\.webp$", re.IGNORECASE)

DEFAULT_JOBS = 10
_log_lock = threading.Lock()


def _log(*args, file=sys.stdout, **kwargs) -> None:
    with _log_lock:
        print(*args, file=file, **kwargs)


def convert_one(path: Path, root: Path, dry_run: bool) -> str:
    try:
        if not is_animated_webp(path):
            return "skip_static"
    except OSError as e:
        _log(f"[skip] {path}: {e}", file=sys.stderr)
        return "error"
    gif_path = path.with_suffix(".gif")
    rel = path.relative_to(root)
    if dry_run:
        _log(f"would convert: {rel} -> {gif_path.name}")
        return "ok"
    try:
        webp_to_gif(path, gif_path)
        path.unlink()
        _log(f"{rel} -> {gif_path.name} (animated)")
        return "ok"
    except Exception as e:
        _log(f"[error] {path}: {e}", file=sys.stderr)
        if gif_path.exists():
            try:
                gif_path.unlink()
            except OSError:
                pass
        return "error"


def is_animated_webp_image(im: Image.Image) -> bool:
    if im.format != "WEBP":
        return False
    return bool(
        getattr(im, "is_animated", False) or getattr(im, "n_frames", 1) > 1
    )


def is_animated_webp(path: Path) -> bool:
    with Image.open(path) as im:
        return is_animated_webp_image(im)


def save_animated_webp_image_to_gif(im: Image.Image, dst: Path) -> None:
    if im.format != "WEBP":
        raise ValueError("expected WebP image")
    loop = im.info.get("loop", 0)
    frames: list[Image.Image] = []
    durations: list[int] = []
    for frame in ImageSequence.Iterator(im):
        rgba = frame.convert("RGBA")
        frames.append(rgba)
        d = frame.info.get(
            "duration", im.info.get("duration", im.info.get("gif_duration", 100))
        )
        try:
            durations.append(int(d) if d is not None else 100)
        except (TypeError, ValueError):
            durations.append(100)

    if len(frames) == 0:
        raise ValueError("no frames")
    if len(durations) < len(frames):
        durations.extend([durations[-1]] * (len(frames) - len(durations)))

    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=".gif", delete=False, dir=dst.parent
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        if len(frames) == 1:
            frames[0].save(
                tmp_path,
                format="GIF",
                duration=durations[0],
                loop=loop,
            )
        else:
            frames[0].save(
                tmp_path,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=loop,
                disposal=2,
            )
        tmp_path.replace(dst)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def webp_bytes_to_gif(data: bytes, dst: Path) -> None:
    with Image.open(io.BytesIO(data)) as im:
        save_animated_webp_image_to_gif(im, dst)


def webp_to_gif(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        save_animated_webp_image_to_gif(im, dst)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert animated WebP under 原图/ to GIF (in place); "
            "static WebP unchanged. Only numbered N.webp files are considered."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        default="原图",
        type=Path,
        help="Root directory to scan (default: 原图).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be converted.",
    )
    parser.add_argument(
        "--all-webp",
        action="store_true",
        help="Process any *.webp, not only numbered N.webp.",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        metavar="N",
        help=f"Parallel worker threads (default: {DEFAULT_JOBS}).",
    )
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 1

    webp_files = sorted(root.rglob("*.webp"))
    converted = 0
    skipped_static = 0
    skipped_name = 0
    errors = 0

    candidates: list[Path] = []
    for path in webp_files:
        if not args.all_webp and not OUTPUT_NAME_RE.match(path.name):
            skipped_name += 1
            continue
        candidates.append(path)

    workers = max(1, args.jobs)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for outcome in pool.map(
            lambda p: convert_one(p, root, args.dry_run), candidates
        ):
            if outcome == "ok":
                converted += 1
            elif outcome == "skip_static":
                skipped_static += 1
            else:
                errors += 1

    print(
        f"Done. converted={converted}, skipped_static_webp={skipped_static}, "
        f"skipped_unnumbered={skipped_name}, errors={errors} ({workers} workers)"
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
