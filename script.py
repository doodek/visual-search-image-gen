# SPDX-License-Identifier: BSD-3-Clause
"""Image generator for a visual-search experiment.

Usage:
    python script.py path/to/config.json

The JSON config keys map directly to ``render()`` keyword arguments
(plus an ``output_path`` consumed by the CLI wrapper).
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger("imggen")

PLACEMENT_RETRIES = 200
ALPHA_THRESHOLD = 128
COLOR_SAMPLE_RETRIES = 64

try:
    _BICUBIC = Image.Resampling.BICUBIC
except AttributeError:
    _BICUBIC = Image.BICUBIC


def _resolve_font(size: int) -> ImageFont.ImageFont:
    """Return Pillow's built-in default TTF at the requested size.

    Requires Pillow >= 10.1 (where ``load_default`` accepts ``size``).
    """
    try:
        return ImageFont.load_default(size=size)
    except TypeError as e:
        raise RuntimeError(
            "Pillow >= 10.1 required (older versions don't support "
            "ImageFont.load_default(size=...)). Run: "
            "pip install --upgrade Pillow"
        ) from e


def _sample_color(spectrum: str, rng: random.Random) -> tuple[int, int, int]:
    if spectrum == "grayscale":
        v = rng.randint(0, 255)
        return (v, v, v)
    if spectrum == "rgb":
        return (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
    raise ValueError(f"unknown color_spectrum: {spectrum!r}")


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def lin(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast_ratio(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    l1, l2 = _relative_luminance(c1), _relative_luminance(c2)
    lo, hi = (l1, l2) if l1 < l2 else (l2, l1)
    return (hi + 0.05) / (lo + 0.05)


def _pick_color(
    spectrum: str,
    background: tuple[int, int, int],
    min_contrast: float,
    rng: random.Random,
) -> tuple[int, int, int]:
    for _ in range(COLOR_SAMPLE_RETRIES):
        c = _sample_color(spectrum, rng)
        if _contrast_ratio(c, background) >= min_contrast:
            return c
    raise RuntimeError(
        f"could not sample color from spectrum {spectrum!r} with contrast "
        f">= {min_contrast} against background {background} after "
        f"{COLOR_SAMPLE_RETRIES} attempts — relax min_contrast or change "
        f"background"
    )


def _render_glyph(
    value: int,
    font_size: int,
    color: tuple[int, int, int],
    rotation: float,
    weight: float,
) -> tuple[Image.Image, np.ndarray]:
    font = _resolve_font(font_size)
    text = str(value)
    left, top, right, bottom = font.getbbox(text)
    # Weight is emulated via Pillow's stroke_width: 0 = regular, ~1 = heavy/black.
    stroke_w = max(0, round(font_size * weight / 6))
    pad = max(4, font_size // 4) + stroke_w
    w = (right - left) + 2 * pad
    h = (bottom - top) + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fill = color + (255,)
    ImageDraw.Draw(img).text(
        (-left + pad, -top + pad), text, font=font, fill=fill,
        stroke_width=stroke_w, stroke_fill=fill,
    )
    if rotation:
        img = img.rotate(rotation, expand=True, resample=_BICUBIC)
    mask = np.asarray(img)[:, :, 3] >= ALPHA_THRESHOLD
    return img, mask


@dataclass
class _Placed:
    x: int
    y: int
    visible: np.ndarray  # bool, shape (h, w); True where this glyph is still visible
    total_pixels: int    # mask.sum() at placement time, used to bound coverage
    is_target: bool = False


def _try_place(
    mask: np.ndarray,
    canvas_size: tuple[int, int],
    placed: list[_Placed],
    rng: random.Random,
    retries: int,
    max_cover_rate: float,
    target_max_cover_rate: float,
) -> tuple[int, int, list[np.ndarray | None]] | None:
    """Find a position where every prior glyph stays under its own cover budget.

    Targets use ``target_max_cover_rate``; other glyphs use ``max_cover_rate``.
    """
    canvas_w, canvas_h = canvas_size
    gh, gw = mask.shape
    if gw > canvas_w or gh > canvas_h:
        return None
    for _ in range(retries):
        x = rng.randint(0, canvas_w - gw)
        y = rng.randint(0, canvas_h - gh)
        updates: list[np.ndarray | None] = []
        ok = True
        for p in placed:
            ph, pw = p.visible.shape
            ox0 = max(x, p.x)
            oy0 = max(y, p.y)
            ox1 = min(x + gw, p.x + pw)
            oy1 = min(y + gh, p.y + ph)
            if ox0 >= ox1 or oy0 >= oy1:
                updates.append(None)
                continue
            new_local = mask[oy0 - y : oy1 - y, ox0 - x : ox1 - x]
            tentative = p.visible.copy()
            tentative[oy0 - p.y : oy1 - p.y, ox0 - p.x : ox1 - p.x] &= ~new_local
            covered_fraction = 1.0 - int(tentative.sum()) / p.total_pixels
            limit = target_max_cover_rate if p.is_target else max_cover_rate
            if covered_fraction > limit:
                ok = False
                break
            updates.append(tentative)
        if ok:
            return x, y, updates
    return None


@dataclass
class RenderResult:
    image: Image.Image
    placed: int
    skipped: int
    target: int
    target_bbox: tuple[int, int, int, int] | None = None  # (x0, y0, x1, y1) on canvas


def render(
    *,
    width: int,
    height: int,
    color_spectrum: str,
    font_size_range: Sequence[int],
    count: int,
    value_range: Sequence[int],
    target: int,
    rotation_range: Sequence[float] = (-90, 90),
    background: Sequence[int] = (255, 255, 255),
    min_contrast: float = 3.0,
    max_cover_rate: float = 0.8,
    target_max_cover_rate: float = 0.3,
    weight: float = 0.5,
    seed: int | None = None,
) -> RenderResult:
    if count < 1:
        raise ValueError("count must be >= 1")
    if not 0.0 <= max_cover_rate <= 1.0:
        raise ValueError("max_cover_rate must be in [0, 1]")
    if not 0.0 <= target_max_cover_rate <= 1.0:
        raise ValueError("target_max_cover_rate must be in [0, 1]")
    if not 0.0 <= weight <= 1.0:
        raise ValueError("weight must be in [0, 1]")
    fmin, fmax = int(font_size_range[0]), int(font_size_range[1])
    vmin, vmax = int(value_range[0]), int(value_range[1])
    rmin, rmax = float(rotation_range[0]), float(rotation_range[1])
    if fmin > fmax:
        raise ValueError("font_size_range[0] must be <= font_size_range[1]")
    if vmin > vmax:
        raise ValueError("value_range[0] must be <= value_range[1]")

    rng = random.Random(seed)

    pool = [v for v in range(vmin, vmax + 1) if v != target]
    if count > 1 and not pool:
        raise ValueError("value_range excluding target is empty but count > 1")
    values = [rng.choice(pool) for _ in range(count - 1)] + [target]
    rng.shuffle(values)

    bg = tuple(int(c) for c in background)
    canvas = Image.new("RGB", (width, height), bg)
    placed: list[_Placed] = []
    skipped = 0
    target_bbox: tuple[int, int, int, int] | None = None

    for value in values:
        is_target = (value == target)
        size = rng.randint(fmin, fmax)
        color = _pick_color(color_spectrum, bg, min_contrast, rng)
        rotation = rng.uniform(rmin, rmax)
        rgba, mask = _render_glyph(value, size, color, rotation, weight)

        # Targets get a larger retry budget since over-covering them later is
        # bounded tighter, which can take more tries to satisfy.
        retries = PLACEMENT_RETRIES * 5 if is_target else PLACEMENT_RETRIES
        result = _try_place(
            mask, (width, height), placed, rng, retries,
            max_cover_rate, target_max_cover_rate,
        )
        if result is None:
            log.warning(
                "could not place number %s (size=%d) within cover budget "
                "after %d attempts; skipping",
                value, size, retries,
            )
            if is_target:
                log.error("TARGET %s could not be placed — image is unusable", target)
            skipped += 1
            continue

        x, y, updates = result
        for p, upd in zip(placed, updates, strict=True):
            if upd is not None:
                p.visible = upd
        canvas.paste(rgba, (x, y), rgba)
        placed.append(_Placed(
            x=x, y=y, visible=mask.copy(),
            total_pixels=int(mask.sum()), is_target=is_target,
        ))

        if is_target:
            ys, xs = np.nonzero(mask)
            if xs.size:
                target_bbox = (
                    x + int(xs.min()), y + int(ys.min()),
                    x + int(xs.max()) + 1, y + int(ys.max()) + 1,
                )

    return RenderResult(
        image=canvas, placed=len(placed), skipped=skipped,
        target=target, target_bbox=target_bbox,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="path to JSON config file")
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = json.load(f)
    output_path = cfg.pop("output_path", None)
    if not output_path:
        parser.error("config must include 'output_path'")
    result = render(**cfg)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.image.save(out, "PNG")
    log.info(
        "wrote %s — placed %d/%d numbers (target=%s, skipped=%d)",
        out, result.placed, cfg["count"], result.target, result.skipped,
    )


if __name__ == "__main__":
    main()
