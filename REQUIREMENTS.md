# Image Generator — Requirements

## Purpose

Generate images suitable for a visual search experiment in the spirit of *Where's Waldo?*
Participants are shown an image filled with numbers and must locate one specific
target number. The script in `script.py` produces these stimulus images.

## Functional Requirements

### Image
- **R1. Resolution.** The image's pixel dimensions (width × height) are
  configurable.
- **R2. Color spectrum.** The set of colors numbers may take is configurable.
  Example presets: *grayscale* and *full RGB*. Other restricted spectra must
  also be expressible.
- **R3. Per-number-instance color.** Each number on a single image is assigned a color
  drawn at random from the configured spectrum. Different numbers on the same
  image will generally have different colors.

### Numbers
- **R4. Size range.** A font-size range is configurable (e.g. 10–46).
  Each number's size is selected uniformly at random from that range.
- **R5. Count.** The total count of numbers placed on an image is configurable.
- **R6. Value range.** An integer range is configurable. Non-target numbers
  are drawn uniformly at random from this range.
- **R7. Font.** A single, consistent font is used for every number on every
  image.
- **R8. Orientation.** Each number is rotated by a random angle, but never
  close to upside-down. Working interpretation: rotation drawn from
  [-90°, +90°] (configurable bounds; never wraps past vertical).
- **R9. Overlap.** Numbers may visually overlap, but no number may be *fully*
  hidden by others. After placement every number must retain at least some
  visible pixels in the final image.
- **R13. Max cover rate.** A configurable fraction (`max_cover_rate`,
  default 0.8) sets the maximum fraction of any number's pixel mask that may
  be obscured by later placements. R9 is the special case where this limit
  is < 1.0; setting `max_cover_rate = 1.0` allows full occlusion.
- **R14. Target cover rate.** The target has its own (typically tighter)
  cap (`target_max_cover_rate`, default 0.3). The target's placement order is
  not constrained — it may sit at any layer and may itself cover other
  numbers — but any later placement that would push the target's coverage
  past this rate is rejected. Implementation: each placed glyph carries an
  `is_target` flag; the cover check uses the appropriate rate per glyph.

### Target
- **R10. Target uniqueness.** A configured target number appears in the image
  *exactly once*. The target is excluded from the random pool defined by R6,
  so it cannot appear a second time even if its value falls inside the
  configured range.

### Readability

- **R11. Background contrast.** Each sampled number color must maintain a
  minimum perceptual distance from the background — e.g. white-on-white must
  not occur. Implemented via the WCAG relative-luminance contrast ratio with
  a configurable minimum (default 3.0, the WCAG AA threshold for large text).
  Sampling rejects colors below the threshold and retries.
- **R12. Weight.** A continuous `weight` parameter (float, 0.0–1.0) controls
  glyph thickness: 0.0 = regular, 1.0 = heavy/black. Implemented via
  Pillow's `stroke_width` on the regular default font, so we cannot go
  lighter than regular. Same weight applies to every number on the image
  (R7); weight is not chosen per-number.

## Configuration Parameters

| Parameter               | Type         | Requirement | Description                                                                   |
| ----------------------- | ------------ | ----------- | ----------------------------------------------------------------------------- |
| `width`                 | int          | R1          | Image width in pixels.                                                        |
| `height`                | int          | R1          | Image height in pixels.                                                       |
| `color_spectrum`        | spec         | R2, R3      | Allowed color set. Built-in presets `"grayscale"` and `"rgb"`.                |
| `font_size_range`       | (int, int)   | R4          | Inclusive min/max font size, in points or pixels.                             |
| `count`                 | int          | R5          | Total number of numbers placed on the image (including the target).           |
| `value_range`           | (int, int)   | R6, R10     | Inclusive min/max integer value for non-target numbers.                       |
| `target`                | int          | R10         | The number that must appear exactly once.                                     |
| `rotation_range`        | (deg, deg)   | R8          | Inclusive min/max rotation in degrees. Default `(-90, 90)`.                   |
| `background`            | color        | —           | Background fill color. Default white.                                         |
| `min_contrast`          | float        | R11         | Min WCAG luminance contrast (number vs. bg). Default `3.0`.                   |
| `max_cover_rate`        | float        | R13         | Max fraction (0–1) of any number that may be obscured. Default `0.8`.         |
| `target_max_cover_rate` | float        | R14         | Stricter cover cap for the target. Default `0.3`.                             |
| `weight`                | float        | R12         | Glyph weight, 0.0–1.0 (0 = regular, 1 = heavy). Default `0.5` ≈ bold.         |
| `seed`                  | int / None   | —           | Optional RNG seed for reproducibility.                                        |
| `output_path`           | str / Path   | —           | Where the generated image is written.                                         |

## Generation Algorithm (sketch)

1. Build the value pool: integers in `value_range` excluding `target`.
2. Sample `count - 1` non-target values from the pool (with replacement,
   since the same non-target number may appear multiple times — to be confirmed).
3. Insert exactly one occurrence of `target` and shuffle the resulting list.
4. For each value, sample size, color, rotation, and a candidate position.
5. Render the rotated glyph onto the canvas; before committing, check R9
   (no previously placed number becomes fully covered). On failure, retry
   with a new position; after a configurable retry budget, give up and report.
6. Write the image to `output_path`.

## Assumptions

1. **Custom color spectrum API.** Just simple keywords like "grayscale", "rgb"
2. **Repeated non-target values.** Non-target values may repeat and may have different colours too
3. **Rotation bounds.** "Not upside down" interpreted as ±90°. Confirmed.
4. **"Fully covered" check.** Implemented as a pixel-level test on each
   number's rendered glyph mask after each new placement (any non-background
   pixel of an earlier number remains visible ⇒ OK). Bounding-box-only
   approximation is cheaper but less accurate. Default plan: pixel-mask check.
5. **Background.** Assumed solid white, configurable. Confirm.
6. **Output format.** Assumed PNG.
7. **Failure mode.** If placement cannot satisfy R9 within a retry budget,
   the script logs a warning and continues with whatever was placed.
8. **Interfaces.** Two front-ends:
   - `script.py` — CLI driven by a JSON config file (for scripted/batch use).
   - `gui.py` — Tkinter GUI for interactive use (set parameters → Generate
     → preview → Save Image…). No JSON authoring required.
   Both share the core `render()` function in `script.py`.
9. **Font source.** The script uses a hardcoded font: `DejaVuSans.ttf` when
   `bold` is false, `DejaVuSans-Bold.ttf` when true. Both are searched in
   common Linux/macOS locations.
10. **Contrast metric.** WCAG relative-luminance contrast ratio is used for
    R11. Default minimum 3.0 (WCAG AA for large text). If the spectrum +
    background combination cannot satisfy the threshold within a sampling
    budget (default 64 attempts), the script raises — that's a
    misconfiguration, not a placement failure.

