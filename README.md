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

1. **Install Python 3** from <https://www.python.org/downloads/macos/>. The
   official installer ships with Tk, which the GUI needs. (If you already
   have Python from Homebrew and you get a "no module named tkinter" error,
   run `brew install python-tk`.)

2. **Get the code.** Either click the green "Code" button on GitHub →
   *Download ZIP* and unzip into a folder you can find (e.g. your Desktop),
   or `git clone` it.

3. **Open Terminal and navigate to the folder.** This is the part that's
   easy to miss if you've never used a terminal before. Open the Terminal
   app (Cmd+Space → "Terminal" → Enter), then type:

   ```bash
   cd ~/Desktop
   cd visual-search-image-gen
   ```

   (Replace `visual-search-image-gen` with the actual folder name if it
   differs, and replace `~/Desktop` with wherever you put it — e.g.
   `~/Downloads` if it's still in your Downloads folder.) After each
   command press Enter. You can confirm you're in the right place by
   typing `ls` — you should see `gui.py`, `script.py`, `README.md`, etc.

4. **Install the dependencies (first time only):**

   ```bash
   python3 -m pip install "Pillow>=10.1" numpy
   ```

5. **Launch the GUI:**

   ```bash
   python3 gui.py
   ```

> **Second run and onwards:** skip step 4. The dependencies are already
> installed. Just open Terminal, do step 3 (`cd`), then step 5
> (`python3 gui.py`).

Set parameters on the left, click **Generate** to preview, click
**Save Image…** to write a PNG.

### Optional: a double-clickable launcher

If you'd rather not open Terminal each time, save a file called
`imggen.command` next to `gui.py` containing:

```bash
#!/bin/bash
cd "$(dirname "$0")"
python3 gui.py
```

Then in Terminal, run `chmod +x imggen.command` once. After that you can
double-click `imggen.command` from Finder to start the app.

## Quick start (Linux / Windows)

Same as above — install Python 3, `pip install "Pillow>=10.1" numpy`, run
`python3 gui.py`. Tk is bundled with the standard Python distributions.

## GUI fields

| Field | Meaning |
| --- | --- |
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
| **Target cover** | Stricter cover cap for the target number itself. Default `0.3` keeps the target at least 70% visible while still letting other numbers partially overlap it. |
| **Weight** | Slider from regular (0.0) to heavy (1.0). Faked via stroke thickening on the regular font; cannot go lighter than regular. Default `0.5` ≈ bold. |
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
  "width": 1920,
  "height": 1080,
  "color_spectrum": "rgb",
  "font_size_range": [56, 160],
  "count": 300,
  "value_range": [0, 99],
  "target": 42,
  "rotation_range": [-90, 90],
  "background": [255, 255, 255],
  "min_contrast": 3.0,
  "max_cover_rate": 0.8,
  "target_max_cover_rate": 0.3,
  "weight": 0.5,
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
- **"Pillow >= 10.1 required"** — your installed Pillow is too old.
  Run `python3 -m pip install --upgrade Pillow`.
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
