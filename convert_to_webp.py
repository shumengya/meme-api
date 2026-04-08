#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

try:
    from PIL import Image, ImageSequence
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "This script requires Pillow. Install it with: python3 -m pip install pillow"
    ) from exc

from animated_webp_to_gif import webp_bytes_to_gif

IMAGE_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".jfif",
    ".jpeg",
    ".jpg",
    ".jpe",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}

# 已编号的成品：1.webp、42.gif（不参与转换；用于各子文件夹内续号）
OUTPUT_NAME_RE = re.compile(r"^(\d+)\.(webp|gif)$", re.IGNORECASE)

DEFAULT_SOURCE_DIR = Path("原图")


@dataclass(frozen=True)
class Job:
    source_label: str
    target_dir: Path
    index: int
    loader: Callable[[], bytes]
    # 磁盘上的源文件；转换成功后删除（zip 成员为 None）。与输出路径相同时不会删。
    source_file: Path | None = None


def is_image_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def is_numbered_asset_file(path: Path) -> bool:
    return path.is_file() and bool(OUTPUT_NAME_RE.match(path.name))


def max_index_in_directory(directory: Path) -> int:
    highest = 0
    if not directory.is_dir():
        return 0
    for p in directory.iterdir():
        if not p.is_file():
            continue
        m = OUTPUT_NAME_RE.match(p.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest


def convert_to_webp(data: bytes) -> tuple[bytes, bool]:
    with Image.open(io.BytesIO(data)) as im:
        is_animated = bool(
            getattr(im, "is_animated", False) or getattr(im, "n_frames", 1) > 1
        )

        if is_animated:
            frames = []
            durations = []
            loop = im.info.get("loop", 0)
            for frame in ImageSequence.Iterator(im):
                frames.append(frame.convert("RGBA"))
                durations.append(frame.info.get("duration", im.info.get("duration", 100)))

            output = io.BytesIO()
            frames[0].save(
                output,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=loop,
                lossless=True,
                method=4,
            )
            return output.getvalue(), True

        output = io.BytesIO()
        im.convert("RGBA").save(output, format="WEBP", lossless=True, method=4)
        return output.getvalue(), False


def is_animated_gif(data: bytes) -> bool:
    with Image.open(io.BytesIO(data)) as im:
        if im.format != "GIF":
            return False
        n_frames = getattr(im, "n_frames", 1)
        return bool(getattr(im, "is_animated", False) or n_frames > 1)


def is_animated_webp_bytes(data: bytes) -> bool:
    with Image.open(io.BytesIO(data)) as im:
        if im.format != "WEBP":
            return False
        return bool(
            getattr(im, "is_animated", False) or getattr(im, "n_frames", 1) > 1
        )


def _read_zip_member(zip_path: Path, member_name: str) -> bytes:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.read(member_name)


def collect_directory_jobs(
    source_root: Path, output_root: Path, *, delete_sources: bool
) -> list[Job]:
    grouped: dict[Path, list[Path]] = {}
    for path in sorted(source_root.rglob("*")):
        if not is_image_path(path):
            continue
        if is_numbered_asset_file(path):
            continue
        grouped.setdefault(path.parent, []).append(path)

    jobs: list[Job] = []
    for directory in sorted(grouped, key=lambda p: str(p)):
        files = sorted(grouped[directory], key=lambda p: p.name)
        target_dir = output_root / directory.relative_to(source_root)
        next_i = max_index_in_directory(target_dir) + 1
        for path in files:
            jobs.append(
                Job(
                    source_label=path.relative_to(source_root).as_posix(),
                    target_dir=target_dir,
                    index=next_i,
                    loader=lambda p=path: p.read_bytes(),
                    source_file=path if delete_sources else None,
                )
            )
            next_i += 1
    return jobs


def collect_zip_jobs(zip_path: Path, output_root: Path) -> list[Job]:
    grouped: dict[PurePosixPath, list[PurePosixPath]] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            member_path = PurePosixPath(info.filename)
            suf = member_path.suffix.lower()
            if suf not in IMAGE_EXTENSIONS:
                continue
            if OUTPUT_NAME_RE.match(member_path.name):
                continue
            grouped.setdefault(member_path.parent, []).append(member_path)

    jobs: list[Job] = []
    for directory in sorted(grouped, key=lambda p: str(p)):
        files = sorted(grouped[directory], key=lambda p: str(p.name))
        target_dir = output_root / Path(str(directory))
        next_i = max_index_in_directory(target_dir) + 1
        for member_path in files:
            jobs.append(
                Job(
                    source_label=member_path.as_posix(),
                    target_dir=target_dir,
                    index=next_i,
                    loader=lambda name=member_path.as_posix(), zp=zip_path: _read_zip_member(
                        zp, name
                    ),
                )
            )
            next_i += 1
    return jobs


def _remove_source_if_any(job: Job, out: Path, kind: str) -> str:
    if job.source_file is None:
        return kind
    try:
        src = job.source_file.resolve()
        if src == out.resolve():
            return kind
        src.unlink()
        return f"{kind}; removed-source"
    except OSError as exc:
        print(
            f"[warn] ok: {out} ({kind}) but could not delete {job.source_file}: {exc}",
            file=sys.stderr,
        )
        return kind


def run_job(job: Job) -> tuple[bool, str, Path, str | None, str | None]:
    try:
        data = job.loader()
        job.target_dir.mkdir(parents=True, exist_ok=True)

        if is_animated_gif(data):
            out = job.target_dir / f"{job.index}.gif"
            out.write_bytes(data)
            kind = _remove_source_if_any(job, out, "gif-animated")
            return True, job.source_label, out, kind, None

        if is_animated_webp_bytes(data):
            out = job.target_dir / f"{job.index}.gif"
            webp_bytes_to_gif(data, out)
            kind = _remove_source_if_any(job, out, "animated-webp->gif")
            return True, job.source_label, out, kind, None

        webp_data, animated = convert_to_webp(data)
        out = job.target_dir / f"{job.index}.webp"
        out.write_bytes(webp_data)
        base = "animated-webp" if animated else "static-webp"
        kind = _remove_source_if_any(job, out, base)
        return True, job.source_label, out, kind, None
    except Exception as exc:
        return False, job.source_label, job.target_dir / f"{job.index}.?", None, str(exc)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read unnumbered images from 原图/ (by default), write numbered *.webp / *.gif "
            "into the same folder tree (in-place). Subfolders mirror 原图. "
            "Animated GIFs and animated WebPs become .gif; static images become lossless .webp. "
            "Next index per folder = max existing N in that folder + 1. "
            "By default unnumbered source files are deleted after a successful conversion."
        )
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        type=Path,
        help=f"Source root folder, single image, or .zip (default: {DEFAULT_SOURCE_DIR.as_posix()}/).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        dest="output_root",
        type=Path,
        help="Output root (default: same as source for folders/single file; for .zip default: <zip-stem>/).",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=10,
        help="Number of worker threads (default: 10).",
    )
    parser.add_argument(
        "--keep-sources",
        action="store_true",
        help="Keep unnumbered source files after conversion (default: delete them).",
    )
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    source = (
        args.source.expanduser().resolve()
        if args.source is not None
        else (cwd / DEFAULT_SOURCE_DIR).resolve()
    )
    jobs: list[Job] = []

    if source.is_dir():
        out_root = (
            args.output_root.expanduser().resolve()
            if args.output_root is not None
            else source
        )
        out_root.mkdir(parents=True, exist_ok=True)
        jobs = collect_directory_jobs(
            source, out_root, delete_sources=not args.keep_sources
        )
    elif source.is_file() and source.suffix.lower() == ".zip":
        out_root = (
            args.output_root.expanduser().resolve()
            if args.output_root is not None
            else (source.parent / source.stem).resolve()
        )
        out_root.mkdir(parents=True, exist_ok=True)
        jobs = collect_zip_jobs(source, out_root)
    elif is_image_path(source):
        if is_numbered_asset_file(source):
            print(f"Skip already-numbered file: {source}", file=sys.stderr)
            return 0
        target_dir = (
            args.output_root.expanduser().resolve()
            if args.output_root is not None
            else source.parent.resolve()
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        idx = max_index_in_directory(target_dir) + 1
        jobs = [
            Job(
                source_label=source.name,
                target_dir=target_dir,
                index=idx,
                loader=lambda p=source: p.read_bytes(),
                source_file=source if not args.keep_sources else None,
            )
        ]
    else:
        print(f"Not a folder, image, or zip: {source}", file=sys.stderr)
        return 1

    jobs.sort(key=lambda job: (str(job.target_dir), job.index))

    if not jobs:
        print(f"No new images to convert under: {source}")
        return 0

    converted = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for ok, label, target, kind, error in pool.map(run_job, jobs):
            if ok:
                print(f"{label} -> {target} ({kind})")
                converted += 1
            else:
                print(f"[skip] {label}: {error}", file=sys.stderr)
                skipped += 1

    print(f"Done. converted={converted}, skipped={skipped}")
    return 0 if converted else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
