#!/usr/bin/env python3
"""
将「最长边」超过指定值的图片等比缩小，使最长边等于该值；不超过的不改动。

默认扫描 原图/、默认目标边长 300 像素、默认 10 线程并行。依赖 Pillow。

处理完成后若只改了 原图/，可再运行 npm run build 同步 public/meme。
"""
from __future__ import annotations

import argparse
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

DEFAULT_ROOT = Path("原图")
DEFAULT_JOBS = 10

_log_lock = threading.Lock()


def _log(*args, file=sys.stdout, **kwargs) -> None:
    with _log_lock:
        print(*args, file=file, **kwargs)


def is_image_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def is_multi_frame(im: Image.Image) -> bool:
    return bool(
        getattr(im, "is_animated", False) or getattr(im, "n_frames", 1) > 1
    )


def target_size(w: int, h: int, max_side: int) -> tuple[int, int] | None:
    if max(w, h) <= max_side:
        return None
    if w >= h:
        nw = max_side
        nh = max(round(h * max_side / w), 1)
    else:
        nh = max_side
        nw = max(round(w * max_side / h), 1)
    return nw, nh


def resize_rgba(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    return im.convert("RGBA").resize(size, Image.Resampling.LANCZOS)


def static_save_format(path: Path, im: Image.Image) -> tuple[str, dict]:
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
    # fallback: keep extension hint
    if ext == ".webp":
        return "WEBP", {"quality": 85, "method": 6}
    return "PNG", {"optimize": True}


def process_static(im: Image.Image, path: Path, max_side: int, dry_run: bool) -> bool:
    w, h = im.size
    th = target_size(w, h, max_side)
    if th is None:
        return False
    if dry_run:
        _log(f"[dry-run] would resize {path} {w}x{h} -> {th[0]}x{th[1]}")
        return True
    out = im.resize(th, Image.Resampling.LANCZOS)
    fmt, kwargs = static_save_format(path, im)
    if fmt == "JPEG" and out.mode in ("RGBA", "P"):
        out = out.convert("RGB")
    elif fmt == "JPEG" and out.mode not in ("RGB", "L"):
        out = out.convert("RGB")
    _atomic_save(path, lambda p: out.save(p, format=fmt, **kwargs))
    _log(f"resized {path} {w}x{h} -> {th[0]}x{th[1]}")
    return True


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


def process_animated(im: Image.Image, path: Path, max_side: int, dry_run: bool) -> bool:
    w, h = im.size
    th = target_size(w, h, max_side)
    if th is None:
        return False

    loop = int(im.info.get("loop", 0) or 0)
    frames: list[Image.Image] = []
    durations: list[int] = []
    src_format = (im.format or "").upper()

    for frame in ImageSequence.Iterator(im):
        rgba = resize_rgba(frame, th)
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

    if dry_run:
        _log(f"[dry-run] would resize animated {path} {w}x{h} -> {th[0]}x{th[1]}")
        return True

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

    _log(f"resized animated {path} {w}x{h} -> {th[0]}x{th[1]}")
    return True


def process_file(path: Path, max_side: int, dry_run: bool) -> bool:
    try:
        with Image.open(path) as im:
            im.load()
            if is_multi_frame(im):
                fmt = (im.format or "").upper()
                ext = path.suffix.lower()
                if fmt not in ("GIF", "WEBP") and ext not in (".gif", ".webp"):
                    _log(
                        f"skip animated (only GIF/WebP): {path}",
                        file=sys.stderr,
                    )
                    return False
                return process_animated(im, path, max_side, dry_run)
            return process_static(im, path, max_side, dry_run)
    except OSError as e:
        _log(f"skip (read error) {path}: {e}", file=sys.stderr)
        return False


def iter_image_files(root: Path) -> list[Path]:
    out: list[Path] = []
    if not root.is_dir():
        return out
    for p in root.rglob("*"):
        if is_image_path(p):
            out.append(p)
    return sorted(out)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Downscale images whose longest side exceeds --max (default 300px); "
            "smaller images unchanged. In-place under the given root."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=DEFAULT_ROOT,
        type=Path,
        help=f"Root directory (default: {DEFAULT_ROOT})",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=300,
        metavar="PX",
        help="Target length for the longest side in pixels (default: 300)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be resized",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        metavar="N",
        help=f"Parallel worker threads (default: {DEFAULT_JOBS})",
    )
    args = parser.parse_args(argv)
    root: Path = args.root
    max_side: int = args.max
    if max_side < 1:
        print("--max must be >= 1", file=sys.stderr)
        return 2
    workers = max(1, args.jobs)

    files = iter_image_files(root)
    if not files:
        print(f"no images under {root}", file=sys.stderr)
        return 1

    n = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for touched in pool.map(
            lambda p: process_file(p, max_side, args.dry_run), files
        ):
            if touched:
                n += 1

    print(f"done. touched {n} file(s) under {root} ({workers} workers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
