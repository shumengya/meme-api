#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import os
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
}


@dataclass(frozen=True)
class Job:
    source_label: str
    target_path: Path
    loader: Callable[[], bytes]


def is_image_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


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


def _read_zip_member(zip_path: Path, member_name: str) -> bytes:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.read(member_name)


def collect_directory_jobs(root: Path, output_base: Path) -> list[Job]:
    grouped: dict[Path, list[Path]] = {}
    for path in sorted(root.rglob("*")):
        if not is_image_path(path):
            continue
        grouped.setdefault(path.parent, []).append(path)

    jobs: list[Job] = []
    for directory in sorted(grouped):
        files = sorted(grouped[directory], key=lambda p: p.name)
        relative_dir = directory.relative_to(root)
        target_dir = output_base / relative_dir
        for index, path in enumerate(files, start=1):
            jobs.append(
                Job(
                    source_label=path.relative_to(root).as_posix(),
                    target_path=target_dir / f"{index}.webp",
                    loader=lambda p=path: p.read_bytes(),
                )
            )
    return jobs


def collect_zip_jobs(zip_path: Path, output_base: Path) -> list[Job]:
    grouped: dict[PurePosixPath, list[PurePosixPath]] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            member_path = PurePosixPath(info.filename)
            if member_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            grouped.setdefault(member_path.parent, []).append(member_path)

    jobs: list[Job] = []
    for directory in sorted(grouped, key=lambda p: str(p)):
        files = sorted(grouped[directory], key=lambda p: str(p.name))
        for index, member_path in enumerate(files, start=1):
            target_dir = output_base / Path(str(directory))
            jobs.append(
                Job(
                    source_label=member_path.as_posix(),
                    target_path=target_dir / f"{index}.webp",
                    loader=lambda name=member_path.as_posix(), zp=zip_path: _read_zip_member(
                        zp, name
                    ),
                )
            )
    return jobs


def collect_jobs(source: Path, output_base: Path | None) -> list[Job]:
    if source.is_dir():
        base = output_base if output_base is not None else source.parent / f"{source.name}-out"
        base.mkdir(parents=True, exist_ok=True)
        return collect_directory_jobs(source, base)

    if source.is_file() and source.suffix.lower() == ".zip":
        base = output_base if output_base is not None else source.parent / source.stem
        base.mkdir(parents=True, exist_ok=True)
        return collect_zip_jobs(source, base)

    if is_image_path(source):
        return [
            Job(
                source_label=source.name,
                target_path=source.parent / "1.webp",
                loader=lambda p=source: p.read_bytes(),
            )
        ]

    return []


def run_job(job: Job) -> tuple[bool, str, Path, bool | None, str | None]:
    try:
        data = job.loader()
        webp_data, animated = convert_to_webp(data)
        job.target_path.parent.mkdir(parents=True, exist_ok=True)
        job.target_path.write_bytes(webp_data)
        return True, job.source_label, job.target_path, animated, None
    except Exception as exc:
        return False, job.source_label, job.target_path, None, str(exc)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Convert images to WebP in place, with independent numbering per folder."
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=".",
        help="Source folder, image file, or .zip archive. Default: current directory.",
    )
    parser.add_argument(
        "--output-base",
        default=None,
        help="Output root. Default for folders: <source>-out next to the source. Default for zip: a folder next to the zip with the same name.",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=max(1, min(32, os.cpu_count() or 4)),
        help="Number of worker threads. Default: number of CPU cores.",
    )
    args = parser.parse_args(argv)

    source = Path(args.source).expanduser().resolve()
    output_base = Path(args.output_base).expanduser().resolve() if args.output_base else None

    jobs = collect_jobs(source, output_base)
    jobs.sort(key=lambda job: str(job.target_path))

    if not jobs:
        print(f"No supported images found in: {source}")
        return 1

    converted = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for ok, label, target, animated, error in pool.map(run_job, jobs):
            if ok:
                kind = "animated" if animated else "static"
                print(f"{label} -> {target} ({kind})")
                converted += 1
            else:
                print(f"[skip] {label}: {error}", file=sys.stderr)
                skipped += 1

    print(f"Done. converted={converted}, skipped={skipped}")
    return 0 if converted else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
