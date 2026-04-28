# imggen — Visual-Search Image Generator

Generate "Where's Waldo?"-style images filled with numbers for visual-search
psychology experiments. Each image hides one configured **target** number among
many distractors, with controllable size, color, rotation, overlap, and more.

![Example output](image.png)

Two ways to use it:

- **GUI** (`gui.py`) — point-and-click, live preview, Save Image button.
- **CLI** (`script.py`) — reads a JSON config, writes a PNG. Useful for batch
  generation.

## Quick start (macOS)

1. Install Python 3 from <https://www.python.org/downloads/macos/>. The
   official installer ships with Tk, which the GUI needs. (If you already
   have Python from Homebrew and you get a "no module named tkinter" error,
   run `brew install python-tk`.)
2. Open Terminal, `cd` to this folder, and install the two dependencies:

   ```bash
   python3 -m pip install Pillow numpy
   ```

3. Launch the GUI:

   ```bash
   python3 gui.py
   ```

That's it. Set parameters on the left, click **Generate** to preview, click
**Save Image…** to write a PNG.

If you'd like a clickable launcher, save a file called `imggen.command` next
to `gui.py` containing:

```bash
#!/bin/bash
cd "$(dirname "$0")"
python3 gui.py
```

then `chmod +x imggen.command`. Double-click it from Finder to start the app.

## Quick start (Linux / Windows)

Same as above — install Python 3, `pip install Pillow numpy`, run
`python3 gui.py`. Tk is bundled with the standard Python distributions.

## GUI fields

| Field | Meaning |
|---|---|
| **Width / Height** | Output image size in pixels. |
| **Background** | Click the swatch to pick the canvas color. |
| **Count** | How many numbers to draw on the image (target included). |
| **Value range** | Distractor numbers are drawn uniformly from this integer range, excluding the target. |
| **Target** | The number the participant searches for. Appears exactly once. Excluded from the value range even if it falls inside it. |
| **Font size** | Each number's size is sampled uniformly from this min/max range. |
| **Rotation°** | Each number is rotated by a random angle in this range. Default `-90 … 90` keeps numbers from going upside-down. |
| **Color spectrum** | `RGB` = any color; `Grayscale` = shades of gray only. |
| **Min contrast** | Minimum WCAG luminance contrast between number color and background. Default `3.0` (WCAG AA for large text) keeps every number readable. Lower = more low-contrast colors allowed. |
| **Max cover** | Largest fraction of any one number that may be hidden by later numbers. `0.8` means each number stays at least 20% visible. `1.0` allows full occlusion. |
| **Target cover** | Stricter cover cap for the target number itself. Default `0.2` keeps the target at least 80% visible while still letting other numbers partially overlap it. |
| **Bold** | Switches the font to its bold variant. |
| **Seed** | Optional integer for reproducible output. Leave blank for random each click. |

Below the preview there is a **Show target** toggle that highlights the
target's location with a red ring — useful when you want to verify placement
without playing the game yourself. The marker is preview-only; saved PNGs are
never marked.

## CLI usage

```bash
python3 script.py path/to/config.json
```

Example `config.json`:

```json
{
  "width": 800,
  "height": 600,
  "color_spectrum": "rgb",
  "font_size_range": [14, 40],
  "count": 80,
  "value_range": [0, 99],
  "target": 42,
  "rotation_range": [-90, 90],
  "background": [255, 255, 255],
  "min_contrast": 3.0,
  "max_cover_rate": 0.8,
  "target_max_cover_rate": 0.2,
  "bold": false,
  "seed": null,
  "output_path": "out.png"
}
```

All fields except `output_path` and the seven core parameters are optional and
fall back to the defaults shown.

## Troubleshooting

- **"No module named tkinter"** — Tk isn't bundled with your Python.
  On macOS, install Python from python.org, or `brew install python-tk`.
  On Debian/Ubuntu Linux, `sudo apt install python3-tk`.
- **"font not found"** — the script uses DejaVuSans (and DejaVuSans-Bold for
  bold mode). It's usually preinstalled. If not, install the DejaVu fonts via
  your OS package manager.
- **"could not sample color … with contrast"** — the requested
  `min_contrast` is too high for the spectrum + background combo. Either
  pick a darker/lighter background or lower `min_contrast`.
- **"could not place number …"** — for very crowded layouts (high `count`,
  small canvas, low `max_cover_rate`), some placements may be dropped. The
  generator logs a warning and continues; the resulting image will contain
  fewer numbers than `count`. Increase the canvas, lower the count, or raise
  `max_cover_rate` to fit more in.

## Files

- `gui.py` — Tkinter front-end.
- `script.py` — core renderer and CLI.
- `REQUIREMENTS.md` — formal requirement list driving the implementation.
- `LICENSE` — BSD 3-Clause license.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
