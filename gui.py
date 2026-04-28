# SPDX-License-Identifier: BSD-3-Clause
"""Tkinter front-end for the visual-search image generator.

Run:  python3 gui.py

Requirements: Pillow, numpy. Tkinter ships with Python on macOS / Windows.
On macOS, install Python from python.org if Tk is missing from your install.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

from script import RenderResult, render

PREVIEW_MAX_W = 720
PREVIEW_MAX_H = 480
TARGET_MARKER_PADDING = 10
TARGET_MARKER_COLOR = "#e11d48"  # rose-600


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("imggen — Visual-Search Image Generator")
        self.minsize(960, 640)
        self._last_image: Image.Image | None = None
        self._target_bbox: tuple[int, int, int, int] | None = None
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._preview_layout: tuple[float, int, int] = (1.0, 0, 0)  # (scale, off_x, off_y)
        self._bg_rgb: tuple[int, int, int] = (255, 255, 255)
        self._setup_style()
        self._build_ui()

    # ---------- styling ----------

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        for theme in ("aqua", "clam"):
            if theme in style.theme_names():
                try:
                    style.theme_use(theme)
                    break
                except tk.TclError:
                    continue
        # Brand-ish palette
        self.configure(background="#f7f7f8")
        style.configure(".", background="#f7f7f8")
        style.configure("TLabelframe", background="#f7f7f8", padding=10)
        style.configure("TLabelframe.Label", background="#f7f7f8", font=("", 10, "bold"))
        style.configure("TFrame", background="#f7f7f8")
        style.configure("TLabel", background="#f7f7f8")
        style.configure("TCheckbutton", background="#f7f7f8")
        style.configure("TRadiobutton", background="#f7f7f8")
        style.configure("Title.TLabel", font=("", 16, "bold"), background="#f7f7f8")
        style.configure("Subtitle.TLabel", foreground="#666", background="#f7f7f8")
        style.configure("Status.TLabel", foreground="#444", background="#f7f7f8")
        style.configure("Primary.TButton", font=("", 10, "bold"), padding=6)
        style.configure("Secondary.TButton", padding=6)

    # ---------- layout ----------

    def _build_ui(self) -> None:
        # Header
        header = ttk.Frame(self, padding=(18, 14, 18, 6))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(header, text="Visual-Search Image Generator", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Configure stimulus images for a “find the target number” task.",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

        # Two-column body
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        form = ttk.Frame(self, padding=(18, 8, 8, 12))
        form.grid(row=1, column=0, sticky="nw")
        self._build_image_frame(form).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._build_numbers_frame(form).grid(row=1, column=0, sticky="ew", pady=8)
        self._build_style_frame(form).grid(row=2, column=0, sticky="ew", pady=8)
        self._build_output_frame(form).grid(row=3, column=0, sticky="ew", pady=8)
        self._build_action_row(form).grid(row=4, column=0, sticky="ew", pady=(8, 4))

        self.status_var = tk.StringVar(value="Set parameters and click Generate.")
        ttk.Label(form, textvariable=self.status_var, style="Status.TLabel", wraplength=320).grid(
            row=5, column=0, sticky="w", pady=(4, 0)
        )

        # Preview pane
        preview_outer = ttk.Frame(self, padding=(8, 8, 18, 12))
        preview_outer.grid(row=1, column=1, sticky="nsew")
        preview_outer.columnconfigure(0, weight=1)
        preview_outer.rowconfigure(0, weight=1)
        preview_card = tk.Frame(
            preview_outer, background="#ffffff",
            highlightbackground="#dcdce0", highlightthickness=1,
        )
        preview_card.grid(row=0, column=0, sticky="n")
        self.preview_canvas = tk.Canvas(
            preview_card, width=PREVIEW_MAX_W, height=PREVIEW_MAX_H,
            background="#ffffff", highlightthickness=0,
        )
        self.preview_canvas.pack(padx=8, pady=8)
        self._draw_placeholder()

        controls_below = ttk.Frame(preview_outer)
        controls_below.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.show_target_var = tk.BooleanVar(value=False)
        self.show_target_chk = ttk.Checkbutton(
            controls_below, text="Show target (preview only — saved image is unmarked)",
            variable=self.show_target_var, command=self._refresh_preview,
            state="disabled",
        )
        self.show_target_chk.pack(side="left")

    def _build_image_frame(self, parent: tk.Widget) -> ttk.Labelframe:
        f = ttk.Labelframe(parent, text="Image")
        self.width_var = tk.StringVar(value="800")
        self.height_var = tk.StringVar(value="600")
        self._row_label_pair(f, 0, "Width", self.width_var)
        self._row_label_pair(f, 1, "Height", self.height_var)
        ttk.Label(f, text="Background").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        self.bg_button = tk.Button(
            f, text="    ", bg="#FFFFFF", width=4, relief="solid", borderwidth=1,
            command=self._pick_bg, cursor="hand2",
        )
        self.bg_button.grid(row=2, column=1, sticky="w", padx=4, pady=4)
        return f

    def _build_numbers_frame(self, parent: tk.Widget) -> ttk.Labelframe:
        f = ttk.Labelframe(parent, text="Numbers")
        self.count_var = tk.StringVar(value="60")
        self._row_label_pair(f, 0, "Count", self.count_var)

        self.value_min_var = tk.StringVar(value="0")
        self.value_max_var = tk.StringVar(value="99")
        self._row_range(f, 1, "Value range", self.value_min_var, self.value_max_var)

        self.target_var = tk.StringVar(value="42")
        self._row_label_pair(f, 2, "Target", self.target_var)

        self.size_min_var = tk.StringVar(value="14")
        self.size_max_var = tk.StringVar(value="40")
        self._row_range(f, 3, "Font size", self.size_min_var, self.size_max_var)

        self.rot_min_var = tk.StringVar(value="-90")
        self.rot_max_var = tk.StringVar(value="90")
        self._row_range(f, 4, "Rotation°", self.rot_min_var, self.rot_max_var)
        return f

    def _build_style_frame(self, parent: tk.Widget) -> ttk.Labelframe:
        f = ttk.Labelframe(parent, text="Style")
        self.spectrum_var = tk.StringVar(value="rgb")
        ttk.Label(f, text="Color spectrum").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        radios = ttk.Frame(f)
        radios.grid(row=0, column=1, columnspan=3, sticky="w", padx=4, pady=4)
        ttk.Radiobutton(radios, text="RGB", variable=self.spectrum_var, value="rgb").pack(side="left", padx=(0, 12))
        ttk.Radiobutton(radios, text="Grayscale", variable=self.spectrum_var, value="grayscale").pack(side="left")

        self.contrast_var = tk.StringVar(value="3.0")
        self._row_label_pair(f, 1, "Min contrast", self.contrast_var)

        self.cover_var = tk.StringVar(value="0.8")
        self._row_label_pair(f, 2, "Max cover", self.cover_var)
        ttk.Label(f, text="(fraction of any number that may be hidden, 0–1)",
                  style="Subtitle.TLabel").grid(row=3, column=1, columnspan=3, sticky="w", padx=4)

        self.target_cover_var = tk.StringVar(value="0.2")
        self._row_label_pair(f, 4, "Target cover", self.target_cover_var)
        ttk.Label(f, text="(stricter cap for the target, 0–1)",
                  style="Subtitle.TLabel").grid(row=5, column=1, columnspan=3, sticky="w", padx=4)

        self.bold_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Bold", variable=self.bold_var).grid(
            row=6, column=1, sticky="w", padx=4, pady=(6, 4)
        )
        return f

    def _build_output_frame(self, parent: tk.Widget) -> ttk.Labelframe:
        f = ttk.Labelframe(parent, text="Output")
        self.seed_var = tk.StringVar(value="")
        ttk.Label(f, text="Seed").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(f, textvariable=self.seed_var, width=12).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(f, text="(blank = random)", style="Subtitle.TLabel").grid(
            row=0, column=2, sticky="w", padx=4
        )
        return f

    def _build_action_row(self, parent: tk.Widget) -> ttk.Frame:
        row = ttk.Frame(parent)
        ttk.Button(row, text="Generate", style="Primary.TButton", command=self._generate).pack(side="left", padx=(0, 8))
        self.save_button = ttk.Button(
            row, text="Save Image…", style="Secondary.TButton",
            command=self._save, state="disabled",
        )
        self.save_button.pack(side="left")
        return row

    def _row_label_pair(self, parent: tk.Widget, row: int, label: str, var: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(parent, textvariable=var, width=10).grid(row=row, column=1, sticky="w", padx=4, pady=4)

    def _row_range(
        self, parent: tk.Widget, row: int, label: str,
        var_min: tk.StringVar, var_max: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(parent, textvariable=var_min, width=10).grid(row=row, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(parent, text="to").grid(row=row, column=2, padx=2)
        ttk.Entry(parent, textvariable=var_max, width=10).grid(row=row, column=3, sticky="w", padx=4, pady=4)

    # ---------- actions ----------

    def _pick_bg(self) -> None:
        result = colorchooser.askcolor(initialcolor=self._bg_rgb, title="Background color")
        if result and result[0]:
            r, g, b = (int(c) for c in result[0])
            self._bg_rgb = (r, g, b)
            self.bg_button.configure(bg=f"#{r:02x}{g:02x}{b:02x}")

    def _collect_params(self) -> dict:
        seed_text = self.seed_var.get().strip()
        return dict(
            width=int(self.width_var.get()),
            height=int(self.height_var.get()),
            color_spectrum=self.spectrum_var.get(),
            font_size_range=(int(self.size_min_var.get()), int(self.size_max_var.get())),
            count=int(self.count_var.get()),
            value_range=(int(self.value_min_var.get()), int(self.value_max_var.get())),
            target=int(self.target_var.get()),
            rotation_range=(float(self.rot_min_var.get()), float(self.rot_max_var.get())),
            background=self._bg_rgb,
            min_contrast=float(self.contrast_var.get()),
            max_cover_rate=float(self.cover_var.get()),
            target_max_cover_rate=float(self.target_cover_var.get()),
            bold=self.bold_var.get(),
            seed=int(seed_text) if seed_text else None,
        )

    def _generate(self) -> None:
        try:
            params = self._collect_params()
        except ValueError as e:
            messagebox.showerror("Invalid input", f"Could not parse parameters: {e}")
            return
        self.status_var.set("Generating…")
        self.update_idletasks()
        try:
            result: RenderResult = render(**params)
        except Exception as e:
            self.status_var.set("Error.")
            messagebox.showerror("Generation failed", str(e))
            return
        self._last_image = result.image
        self._target_bbox = result.target_bbox
        self.show_target_chk.configure(
            state="normal" if result.target_bbox else "disabled"
        )
        self._refresh_preview()
        self.save_button.config(state="normal")
        msg = f"Placed {result.placed} of {params['count']} (target = {result.target})"
        if result.skipped:
            msg += f"  ·  {result.skipped} skipped (overlap budget exceeded)"
        if result.target_bbox is None:
            msg += "  ·  target could not be placed!"
        self.status_var.set(msg)

    def _refresh_preview(self) -> None:
        if self._last_image is None:
            self._draw_placeholder()
            return
        img = self._last_image
        w, h = img.size
        scale = min(PREVIEW_MAX_W / w, PREVIEW_MAX_H / h, 1.0)
        if scale < 1.0:
            preview = img.resize(
                (max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS
            )
        else:
            preview = img
        disp_w, disp_h = preview.size
        off_x = (PREVIEW_MAX_W - disp_w) // 2
        off_y = (PREVIEW_MAX_H - disp_h) // 2
        self._preview_layout = (scale, off_x, off_y)
        self._preview_photo = ImageTk.PhotoImage(preview)

        c = self.preview_canvas
        c.delete("all")
        c.create_image(off_x, off_y, image=self._preview_photo, anchor="nw")
        if self.show_target_var.get() and self._target_bbox is not None:
            self._draw_target_marker()

    def _draw_target_marker(self) -> None:
        if self._target_bbox is None:
            return
        scale, off_x, off_y = self._preview_layout
        x0, y0, x1, y1 = self._target_bbox
        pad = TARGET_MARKER_PADDING
        cx0 = off_x + int(x0 * scale) - pad
        cy0 = off_y + int(y0 * scale) - pad
        cx1 = off_x + int(x1 * scale) + pad
        cy1 = off_y + int(y1 * scale) + pad
        # Outer halo + inner ring for visibility on any background
        self.preview_canvas.create_oval(
            cx0 - 2, cy0 - 2, cx1 + 2, cy1 + 2,
            outline="#ffffff", width=4,
        )
        self.preview_canvas.create_oval(
            cx0, cy0, cx1, cy1,
            outline=TARGET_MARKER_COLOR, width=3,
        )

    def _draw_placeholder(self) -> None:
        c = self.preview_canvas
        c.delete("all")
        c.create_text(
            PREVIEW_MAX_W // 2, PREVIEW_MAX_H // 2,
            text="Click Generate to preview",
            fill="#999999", font=("", 12),
        )

    def _save(self) -> None:
        if self._last_image is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            initialfile="image.png",
        )
        if not path:
            return
        self._last_image.save(path, "PNG")
        self.status_var.set(f"Saved to {path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    App().mainloop()


if __name__ == "__main__":
    main()
