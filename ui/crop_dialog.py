"""Non-destructive crop editor. All edits stay local until Apply."""
import math
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

from core.image_geometry import MIN_CROP_FRACTION, get_image_layer_crop_box
from core.renderer import get_cached_image
from ui.theme import BG_DARK, TEXT_PRIMARY, ACCENT_COLOR
from ui.widgets import DarkButton
from ui.crop_geometry import (
    ASPECT_MODES, get_aspect_ratio, fit_crop_to_ratio,
    resize_crop_with_ratio, snap_crop_to_pixels,
)


def open_crop_dialog(parent, layer, on_apply):
    source = get_cached_image(layer.file_path)
    if source is None:
        messagebox.showerror("Crop Image", "The image could not be opened.", parent=parent)
        return None
    return CropDialog(parent, layer, source, on_apply)


class CropDialog(tk.Toplevel):
    def __init__(self, parent, layer, source, on_apply):
        super().__init__(parent)
        self.title("Crop Image")
        self.configure(bg=BG_DARK)
        self.transient(parent.winfo_toplevel())
        self.layer, self.source, self.on_apply = layer, source, on_apply
        self.box = list(get_image_layer_crop_box(layer, source.size))
        self._drag = None
        self._aspect_ratio = None
        self._aspect_mode = "Free"
        self.resizable(False, False)
        tk.Label(self, text="Drag inside to move; drag an edge or corner to resize.",
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(padx=16, pady=10)
        aspect_row = tk.Frame(self, bg=BG_DARK)
        aspect_row.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Label(aspect_row, text="Aspect:", bg=BG_DARK, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        self.aspect_var = tk.StringVar(value="Free")
        self.aspect_combo = ttk.Combobox(aspect_row, textvariable=self.aspect_var,
                                         values=ASPECT_MODES, state="readonly", width=12)
        self.aspect_combo.pack(side=tk.LEFT, padx=8)
        self.aspect_combo.bind("<<ComboboxSelected>>", self._aspect_changed)
        max_w = min(860, self.winfo_screenwidth() - 100)
        max_h = min(650, self.winfo_screenheight() - 260)
        ratio = min(max_w / source.width, max_h / source.height, 1.0)
        self.preview = source.resize((max(1, round(source.width * ratio)),
                                      max(1, round(source.height * ratio))), Image.Resampling.LANCZOS)
        self.sx = self.preview.width / source.width
        self.sy = self.preview.height / source.height
        self.margin = 14
        self.canvas = tk.Canvas(self, width=self.preview.width + 28,
                                height=self.preview.height + 28, bg=BG_DARK,
                                highlightthickness=0)
        self.canvas.pack(padx=12)
        buttons = tk.Frame(self, bg=BG_DARK)
        buttons.pack(fill=tk.X, padx=16, pady=12)
        for title, action in [("Reset", self.reset), ("Cancel", self.destroy), ("Apply", self.apply)]:
            DarkButton(buttons, text=title, command=action, padx=16, pady=6).pack(side=tk.LEFT, padx=4)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Motion>", self._hover)
        self.bind("<Escape>", lambda event: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._draw()
        self.grab_set()

    def _aspect_changed(self, event=None):
        mode = self.aspect_var.get()
        ratio = get_aspect_ratio(mode, self.source.size)
        try:
            box = fit_crop_to_ratio(self.box, self.source.size, ratio)
            if ratio is None:
                box = snap_crop_to_pixels(box, self.source.size)
        except ValueError as error:
            self.aspect_var.set(self._aspect_mode)
            messagebox.showwarning("Aspect Ratio", str(error), parent=self)
            return
        self._aspect_mode, self._aspect_ratio = mode, ratio
        self._drag = None
        self.box = box
        self._draw()

    def _screen_box(self):
        l, t, r, b = self.box
        m = self.margin
        return m + l * self.sx, m + t * self.sy, m + r * self.sx, m + b * self.sy

    def _draw(self):
        l, t, r, b = self._screen_box()
        m = self.margin
        image = self.preview.copy()
        shade = Image.new("RGBA", image.size, (0, 0, 0, 150))
        shade.paste((0, 0, 0, 0), (round(l-m), round(t-m), round(r-m), round(b-m)))
        image = Image.alpha_composite(image.convert("RGBA"), shade)
        self._photo = ImageTk.PhotoImage(image, master=self)
        self.canvas.delete("all")
        self.canvas.create_image(m, m, anchor=tk.NW, image=self._photo)
        self.canvas.create_rectangle(l, t, r, b, outline=ACCENT_COLOR, width=2)
        for x, y in [(l,t), ((l+r)/2,t), (r,t), (l,(t+b)/2),
                     (r,(t+b)/2), (l,b), ((l+r)/2,b), (r,b)]:
            self.canvas.create_rectangle(x-4, y-4, x+4, y+4, fill=ACCENT_COLOR, outline="white")

    def _hit(self, x, y):
        l, t, r, b = self._screen_box()
        if not (l-8 <= x <= r+8 and t-8 <= y <= b+8):
            return None
        horizontal = "w" if abs(x-l) <= 8 else "e" if abs(x-r) <= 8 else ""
        vertical = "n" if abs(y-t) <= 8 else "s" if abs(y-b) <= 8 else ""
        return vertical + horizontal or "move"

    def _hover(self, event):
        self.canvas.configure(cursor="fleur" if self._hit(event.x, event.y) == "move" else "crosshair")

    def _press(self, event):
        mode = self._hit(event.x, event.y)
        self._drag = (mode, event.x, event.y, self.box[:]) if mode else None

    def _motion(self, event):
        if self._drag is None:
            return
        mode, x, y, original = self._drag
        l, t, r, b = original
        dx, dy = (event.x-x)/self.sx, (event.y-y)/self.sy
        width, height = self.source.size
        min_w, min_h = max(1, math.ceil(width*MIN_CROP_FRACTION)), max(1, math.ceil(height*MIN_CROP_FRACTION))
        if mode == "move":
            dx, dy = max(-l, min(width-r, dx)), max(-t, min(height-b, dy))
            l, t, r, b = l+dx, t+dy, r+dx, b+dy
        elif getattr(self, "_aspect_ratio", None) is not None:
            self.box = resize_crop_with_ratio(original, self.source.size, mode, dx, dy, self._aspect_ratio)
            self._draw()
            return
        else:
            if "w" in mode:
                l = max(0, min(r-min_w, l+dx))
            if "e" in mode:
                r = min(width, max(l+min_w, r+dx))
            if "n" in mode:
                t = max(0, min(b-min_h, t+dy))
            if "s" in mode:
                b = min(height, max(t+min_h, b+dy))
        self.box = ([l, t, r, b] if getattr(self, "_aspect_ratio", None) is not None
                    else [round(l), round(t), round(r), round(b)])
        self._draw()

    def _release(self, event):
        self._drag = None

    def reset(self):
        self._aspect_mode, self._aspect_ratio = "Free", None
        if hasattr(self, "aspect_var"):
            self.aspect_var.set("Free")
        self._drag = None
        self.box = [0, 0, self.source.width, self.source.height]
        self._draw()

    def apply(self):
        l, t, r, b = snap_crop_to_pixels(self.box, self.source.size)
        self.layer.crop_left, self.layer.crop_right = l/self.source.width, r/self.source.width
        self.layer.crop_top, self.layer.crop_bottom = t/self.source.height, b/self.source.height
        self.destroy()
        self.on_apply()
