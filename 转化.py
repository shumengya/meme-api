#!/usr/bin/env python3
"""
一键：从 原图/ 读取素材 → 输出到 原图-已处理/（默认）。

- 未编号、格式不符的：转为编号 .webp / .gif，并按最长边缩放（默认 250px）。
- 已符合 N.webp / N.gif 的：复制到 原图-已处理/ 后同样按最长边缩放（默认 250px）。

默认保留 原图 中源文件；需清理可加 --delete-sources。依赖 Pillow。
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import tempfile
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

try:
    from PIL import Image, ImageSequence
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "需要 Pillow：python -m pip install pillow"
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
    ".webp",
}

OUTPUT_NAME_RE = re.compile(r"^(\d+)\.(webp|gif)$", re.IGNORECASE)

DEFAULT_SOURCE_DIR = Path("原图")
DEFAULT_OUTPUT_DIR = Path("原图-已处理")
DEFAULT_MAX_SIDE = 250
DEFAULT_JOBS = 10

_print_lock = threading.Lock()


def _log(*args, file=sys.stdout, **kwargs) -> None:
    with _print_lock:
        print(*args, file=file, **kwargs)


@dataclass(frozen=True)
class Job:
    source_label: str
    target_dir: Path
    index: int
    loader: Callable[[], bytes]
    source_file: Path | None = None
    # 若设置：直接写入 target_dir / dest_name（已编号成品复制，不转码、不缩放）
    dest_name: str | None = None


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


def encode_to_webp_bytes(data: bytes) -> tuple[bytes, bool]:
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
                durations.append(
                    frame.info.get("duration", im.info.get("duration", 100))
                )

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
        grouped.setdefault(path.parent, []).append(path)

    jobs: list[Job] = []
    for directory in sorted(grouped, key=lambda p: str(p)):
        files = sorted(grouped[directory], key=lambda p: p.name)
        target_dir = output_root / directory.relative_to(source_root)

        conforming = [p for p in files if is_numbered_asset_file(p)]
        non_conforming = [p for p in files if not is_numbered_asset_file(p)]

        max_src = 0
        for p in conforming:
            m = OUTPUT_NAME_RE.match(p.name)
            if m:
                max_src = max(max_src, int(m.group(1)))

        max_t = max_index_in_directory(target_dir)
        next_i = max(max_src, max_t) + 1

        for path in conforming:
            jobs.append(
                Job(
                    source_label=path.relative_to(source_root).as_posix(),
                    target_dir=target_dir,
                    index=0,
                    loader=lambda p=path: p.read_bytes(),
                    source_file=path if delete_sources else None,
                    dest_name=path.name,
                )
            )

        for path in non_conforming:
            jobs.append(
                Job(
                    source_label=path.relative_to(source_root).as_posix(),
                    target_dir=target_dir,
                    index=next_i,
                    loader=lambda p=path: p.read_bytes(),
                    source_file=path if delete_sources else None,
                    dest_name=None,
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
                    source_file=None,
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
        _log(
            f"[warn] ok: {out} ({kind}) but could not delete {job.source_file}: {exc}",
            file=sys.stderr,
        )
        return kind


# --- 最长边缩放（多帧仅 GIF/WebP）---


def _is_multi_frame(im: Image.Image) -> bool:
    return bool(
        getattr(im, "is_animated", False) or getattr(im, "n_frames", 1) > 1
    )


def _target_size(w: int, h: int, max_side: int) -> tuple[int, int] | None:
    if max(w, h) <= max_side:
        return None
    if w >= h:
        nw = max_side
        nh = max(round(h * max_side / w), 1)
    else:
        nh = max_side
        nw = max(round(w * max_side / h), 1)
    return nw, nh


def _resize_rgba(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    return im.convert("RGBA").resize(size, Image.Resampling.LANCZOS)


def _static_save_format(path: Path, im: Image.Image) -> tuple[str, dict]:
    ext = path.suffix.lower()
    fmt = (im.format or "").upper()
    if ext in (".jpg", ".jpeg", ".jpe") or fmt in ("JPEG", "MPO"):
        return "JPEG", {"quality": 90, "optimize": True}
    if ext == ".png" or fmt == "PNG":
        return "PNG", {"optimize": True}
    if ext == ".webp" or fmt == "WEBP":
        return "WEBP", {"quality": 85, "method": 6}
    if ext == ".gif" or fmt == "GIF":
        return "GIF", {}
    if ext in (".bmp",) or fmt == "BMP":
        return "BMP", {}
    if ext in (".tif", ".tiff") or fmt == "TIFF":
        return "TIFF", {"compression": "tiff_lzw"}
    if ext == ".avif" or fmt == "AVIF":
        return "AVIF", {"quality": 80}
    if ext == ".webp":
        return "WEBP", {"quality": 85, "method": 6}
    return "PNG", {"optimize": True}


def _atomic_save(path: Path, saver) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=path.suffix, delete=False, dir=path.parent
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        saver(tmp_path)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _resize_static(im: Image.Image, path: Path, max_side: int) -> bool:
    w, h = im.size
    th = _target_size(w, h, max_side)
    if th is None:
        return False
    out = im.resize(th, Image.Resampling.LANCZOS)
    fmt, kwargs = _static_save_format(path, im)
    if fmt == "JPEG" and out.mode in ("RGBA", "P"):
        out = out.convert("RGB")
    elif fmt == "JPEG" and out.mode not in ("RGB", "L"):
        out = out.convert("RGB")
    _atomic_save(path, lambda p: out.save(p, format=fmt, **kwargs))
    return True


def _resize_animated(im: Image.Image, path: Path, max_side: int) -> bool:
    w, h = im.size
    th = _target_size(w, h, max_side)
    if th is None:
        return False

    loop = int(im.info.get("loop", 0) or 0)
    frames: list[Image.Image] = []
    durations: list[int] = []
    src_format = (im.format or "").upper()

    for frame in ImageSequence.Iterator(im):
        rgba = _resize_rgba(frame, th)
        frames.append(rgba)
        d = frame.info.get("duration", im.info.get("duration", 100))
        try:
            durations.append(int(d) if d is not None else 100)
        except (TypeError, ValueError):
            durations.append(100)

    if len(frames) == 0:
        return False
    if len(durations) < len(frames):
        durations.extend([durations[-1]] * (len(frames) - len(durations)))

    def save_gif(p: Path) -> None:
        if len(frames) == 1:
            frames[0].save(p, format="GIF", duration=durations[0], loop=loop)
        else:
            frames[0].save(
                p,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=loop,
                disposal=2,
            )

    def save_webp(p: Path) -> None:
        frames[0].save(
            p,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=loop,
            quality=85,
            method=6,
        )

    if src_format == "GIF" or path.suffix.lower() == ".gif":
        _atomic_save(path, save_gif)
    else:
        _atomic_save(path, save_webp)

    return True


def resize_output_if_needed(path: Path, max_side: int) -> None:
    if max_side < 1:
        return
    try:
        with Image.open(path) as im:
            im.load()
            if _is_multi_frame(im):
                fmt = (im.format or "").upper()
                ext = path.suffix.lower()
                if fmt not in ("GIF", "WEBP") and ext not in (".gif", ".webp"):
                    _log(
                        f"skip resize animated (only GIF/WebP): {path}",
                        file=sys.stderr,
                    )
                    return
                changed = _resize_animated(im, path, max_side)
            else:
                changed = _resize_static(im, path, max_side)
            if changed:
                _log(f"resized {path} (max side {max_side})")
    except OSError as e:
        _log(f"skip resize {path}: {e}", file=sys.stderr)


def run_job(job: Job, max_side: int) -> tuple[bool, str, Path, str | None, str | None]:
    try:
        data = job.loader()
        job.target_dir.mkdir(parents=True, exist_ok=True)

        if job.dest_name is not None:
            out = job.target_dir / job.dest_name
            out.write_bytes(data)
            kind = _remove_source_if_any(job, out, "copy")
            resize_output_if_needed(out, max_side)
            return True, job.source_label, out, kind, None

        if is_animated_gif(data):
            out = job.target_dir / f"{job.index}.gif"
            out.write_bytes(data)
            kind = _remove_source_if_any(job, out, "gif-animated")
            resize_output_if_needed(out, max_side)
            return True, job.source_label, out, kind, None

        if is_animated_webp_bytes(data):
            out = job.target_dir / f"{job.index}.gif"
            webp_bytes_to_gif(data, out)
            kind = _remove_source_if_any(job, out, "animated-webp->gif")
            resize_output_if_needed(out, max_side)
            return True, job.source_label, out, kind, None

        webp_data, animated = encode_to_webp_bytes(data)
        out = job.target_dir / f"{job.index}.webp"
        out.write_bytes(webp_data)
        base = "animated-webp" if animated else "static-webp"
        kind = _remove_source_if_any(job, out, base)
        resize_output_if_needed(out, max_side)
        return True, job.source_label, out, kind, None
    except Exception as exc:
        return False, job.source_label, job.target_dir / f"{job.index}.?", None, str(exc)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "原图/ 下：未编号素材转为编号 .webp/.gif 并限最长边；"
            "已符合 N.webp/N.gif 的复制到 原图-已处理/ 后同样限最长边。"
            "默认读取 原图/、保留源文件。"
        )
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        type=Path,
        help=f"源：目录、单图或 .zip（默认: {DEFAULT_SOURCE_DIR.as_posix()}/）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        dest="output_root",
        type=Path,
        help=f"输出根目录（默认: 目录模式为 {DEFAULT_OUTPUT_DIR.as_posix()}/；"
        "zip 为 zip 同目录下以压缩包名为文件夹；单图为该目录）",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=DEFAULT_MAX_SIDE,
        metavar="PX",
        help=f"最长边像素上限，超过则缩小（默认 {DEFAULT_MAX_SIDE}；0 表示不缩放）",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help=f"线程数（默认 {DEFAULT_JOBS}）",
    )
    parser.add_argument(
        "--delete-sources",
        action="store_true",
        help="成功后删除 原图 中已处理的源文件（含已编号复制项；默认保留）",
    )
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    source = (
        args.source.expanduser().resolve()
        if args.source is not None
        else (cwd / DEFAULT_SOURCE_DIR).resolve()
    )
    jobs: list[Job] = []
    max_side: int = args.max

    if source.is_dir():
        out_root = (
            args.output_root.expanduser().resolve()
            if args.output_root is not None
            else (cwd / DEFAULT_OUTPUT_DIR).resolve()
        )
        out_root.mkdir(parents=True, exist_ok=True)
        jobs = collect_directory_jobs(
            source, out_root, delete_sources=args.delete_sources
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
        target_dir = (
            args.output_root.expanduser().resolve()
            if args.output_root is not None
            else (cwd / DEFAULT_OUTPUT_DIR).resolve()
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        if is_numbered_asset_file(source):
            jobs = [
                Job(
                    source_label=source.name,
                    target_dir=target_dir,
                    index=0,
                    loader=lambda p=source: p.read_bytes(),
                    source_file=source if args.delete_sources else None,
                    dest_name=source.name,
                )
            ]
        else:
            idx = max_index_in_directory(target_dir) + 1
            jobs = [
                Job(
                    source_label=source.name,
                    target_dir=target_dir,
                    index=idx,
                    loader=lambda p=source: p.read_bytes(),
                    source_file=source if args.delete_sources else None,
                )
            ]
    else:
        print(f"不是目录、图片或 zip: {source}", file=sys.stderr)
        return 1

    jobs.sort(
        key=lambda job: (
            str(job.target_dir),
            (job.dest_name or "").lower(),
            f"{job.index:08d}",
        )
    )

    if not jobs:
        print(f"没有待处理文件: {source}")
        return 0

    converted = 0
    copied = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for ok, label, target, kind, error in pool.map(
            lambda j: run_job(j, max_side), jobs
        ):
            if ok:
                print(f"{label} -> {target} ({kind})")
                base_kind = (kind or "").split(";")[0].strip()
                if base_kind == "copy":
                    copied += 1
                else:
                    converted += 1
            else:
                print(f"[skip] {label}: {error}", file=sys.stderr)
                skipped += 1

    print(f"完成：转换={converted}, 复制={copied}, 失败={skipped}")
    return 0 if (converted + copied) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
