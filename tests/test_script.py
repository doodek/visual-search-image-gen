# SPDX-License-Identifier: BSD-3-Clause
"""Unit + integration tests for script.render and helpers."""

from __future__ import annotations

import io
import random

import numpy as np
import pytest
from PIL import Image

from script import (
    RenderResult,
    _contrast_ratio,
    _pick_color,
    _relative_luminance,
    _render_glyph,
    _sample_color,
    render,
)

# -------- color helpers --------

def test_relative_luminance_extremes() -> None:
    assert _relative_luminance((0, 0, 0)) == pytest.approx(0.0)
    assert _relative_luminance((255, 255, 255)) == pytest.approx(1.0)


def test_contrast_ratio_white_vs_black_is_21() -> None:
    # Per WCAG, white on black has the maximum 21:1 ratio.
    assert _contrast_ratio((255, 255, 255), (0, 0, 0)) == pytest.approx(21.0, rel=1e-3)


def test_contrast_ratio_same_color_is_one() -> None:
    assert _contrast_ratio((128, 128, 128), (128, 128, 128)) == pytest.approx(1.0)


def test_contrast_ratio_is_symmetric() -> None:
    assert _contrast_ratio((10, 20, 30), (200, 210, 220)) == pytest.approx(
        _contrast_ratio((200, 210, 220), (10, 20, 30))
    )


# -------- spectrum sampling --------

def test_sample_color_grayscale_returns_grey_triple() -> None:
    rng = random.Random(0)
    for _ in range(50):
        r, g, b = _sample_color("grayscale", rng)
        assert r == g == b
        assert 0 <= r <= 255


def test_sample_color_rgb_returns_byte_triple() -> None:
    rng = random.Random(0)
    for _ in range(50):
        r, g, b = _sample_color("rgb", rng)
        assert all(0 <= c <= 255 for c in (r, g, b))


def test_sample_color_rejects_unknown_spectrum() -> None:
    with pytest.raises(ValueError, match="unknown color_spectrum"):
        _sample_color("hsl", random.Random(0))


def test_pick_color_honors_min_contrast() -> None:
    rng = random.Random(0)
    bg = (255, 255, 255)
    for _ in range(20):
        c = _pick_color("rgb", bg, min_contrast=4.5, rng=rng)
        assert _contrast_ratio(c, bg) >= 4.5


def test_pick_color_raises_when_unsatisfiable() -> None:
    # WCAG max contrast is 21:1. Asking for >21 against any background is impossible.
    with pytest.raises(RuntimeError, match="could not sample color"):
        _pick_color("grayscale", (255, 255, 255), min_contrast=25.0, rng=random.Random(0))


# -------- glyph rendering --------

def test_render_glyph_produces_nonempty_mask() -> None:
    img, mask = _render_glyph(value=7, font_size=40, color=(0, 0, 0), rotation=0.0, weight=0.0)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGBA"
    assert mask.dtype == np.bool_
    assert mask.any(), "regular-weight glyph mask should not be empty"


def test_render_glyph_weight_increases_pixel_count() -> None:
    _, mask_regular = _render_glyph(7, 40, (0, 0, 0), 0.0, weight=0.0)
    _, mask_heavy = _render_glyph(7, 40, (0, 0, 0), 0.0, weight=1.0)
    assert int(mask_heavy.sum()) > int(mask_regular.sum())


# -------- render() integration --------

_BASE_CONFIG: dict = {
    "width": 320,
    "height": 240,
    "color_spectrum": "rgb",
    "font_size_range": (16, 28),
    "count": 12,
    "value_range": (0, 50),
    "target": 7,
    "min_contrast": 3.0,
    "max_cover_rate": 0.8,
    "target_max_cover_rate": 0.3,
    "weight": 0.0,
    "seed": 123,
}


def test_render_returns_correct_image_dimensions() -> None:
    r = render(**_BASE_CONFIG)
    assert isinstance(r, RenderResult)
    assert r.image.size == (_BASE_CONFIG["width"], _BASE_CONFIG["height"])


def test_render_places_count_numbers_on_easy_config() -> None:
    r = render(**_BASE_CONFIG)
    assert r.placed == _BASE_CONFIG["count"]
    assert r.skipped == 0


def test_render_target_bbox_is_inside_canvas() -> None:
    r = render(**_BASE_CONFIG)
    assert r.target_bbox is not None
    x0, y0, x1, y1 = r.target_bbox
    assert 0 <= x0 < x1 <= _BASE_CONFIG["width"]
    assert 0 <= y0 < y1 <= _BASE_CONFIG["height"]


def test_render_is_deterministic_for_same_seed() -> None:
    r1 = render(**_BASE_CONFIG)
    r2 = render(**_BASE_CONFIG)
    buf1, buf2 = io.BytesIO(), io.BytesIO()
    r1.image.save(buf1, "PNG")
    r2.image.save(buf2, "PNG")
    assert buf1.getvalue() == buf2.getvalue()
    assert r1.target_bbox == r2.target_bbox


def test_render_differs_across_seeds() -> None:
    r1 = render(**(_BASE_CONFIG | {"seed": 1}))
    r2 = render(**(_BASE_CONFIG | {"seed": 2}))
    assert r1.target_bbox != r2.target_bbox


# -------- validation errors --------

@pytest.mark.parametrize("kwargs, match", [
    ({"count": 0}, r"count must be >= 1"),
    ({"max_cover_rate": 1.5}, r"max_cover_rate must be in"),
    ({"target_max_cover_rate": -0.1}, r"target_max_cover_rate must be in"),
    ({"weight": 2.0}, r"weight must be in"),
    ({"font_size_range": (40, 16)}, r"font_size_range\[0\] must be <="),
    ({"value_range": (50, 0)}, r"value_range\[0\] must be <="),
])
def test_render_rejects_invalid_inputs(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        render(**(_BASE_CONFIG | kwargs))


def test_render_rejects_empty_pool_when_count_gt_1() -> None:
    cfg = _BASE_CONFIG | {"value_range": (7, 7), "target": 7, "count": 5}
    with pytest.raises(ValueError, match="value_range excluding target is empty"):
        render(**cfg)


def test_render_with_only_target_works_when_pool_is_empty() -> None:
    cfg = _BASE_CONFIG | {"value_range": (7, 7), "target": 7, "count": 1}
    r = render(**cfg)
    assert r.placed == 1
    assert r.target_bbox is not None
