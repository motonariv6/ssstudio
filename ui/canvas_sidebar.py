from __future__ import annotations
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from typing import Callable, Optional

from core.models import Project, Page, CANVAS_PRESETS, GRADIENT_PRESETS
from ui.theme import (
    BG_DARK, BG_SECONDARY, BG_TERTIARY, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_COLOR, FONT_BOLD, FONT_SMALL, FONT_SYSTEM,
    BTN_BG_DEFAULT, BTN_BG_HOVER, BTN_FG, BTN_ACCENT_BG, BTN_ACCENT_HOVER
)
from ui.widgets import DarkButton


class CanvasSidebar(tk.Frame):
    """Left sidebar for Canvas dimensions and Background/Gradient configuration."""

    def __init__(
        self,
        parent,
        get_project: Callable[[], Project],
        get_active_page: Callable[[], Page],
        on_change: Callable[[], None],
        **kwargs
    ):
        super().__init__(parent, bg=BG_DARK, width=300, **kwargs)
        self.get_project = get_project
        self.get_active_page = get_active_page
        self.on_change = on_change

        self.pack_propagate(False)

        # Scrollable container
        self.canvas_scroll = tk.Canvas(self, bg=BG_DARK, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas_scroll.yview)
        self.scroll_content = tk.Frame(self.canvas_scroll, bg=BG_DARK)

        self.scroll_content.bind(
            "<Configure>",
            lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all"))
        )
        self._scroll_window = self.canvas_scroll.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar.set)

        self.canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.bind("<Configure>", self._on_panel_resize)
        self.canvas_scroll.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        # Build Sections
        self._build_canvas_section()
        self._build_background_section()

        self._initialized = True
        self.refresh()

    def _on_panel_resize(self, event):
        self.canvas_scroll.itemconfig(self._scroll_window, width=event.width - 15)

    def _on_mousewheel(self, event):
        # Only scroll if mouse is over this sidebar
        x, y = self.winfo_pointerxy()
        widget_under_mouse = self.winfo_containing(x, y)
        if widget_under_mouse and str(widget_under_mouse).startswith(str(self)):
            self.canvas_scroll.yview_scroll(int(-1 * (event.delta / 1)), "units")

    def _create_section_card(self, title: str) -> tk.Frame:
        card = tk.Frame(self.scroll_content, bg=BG_SECONDARY, padx=12, pady=10)
        card.pack(fill=tk.X, padx=10, pady=6)
        
        lbl = tk.Label(card, text=title, font=FONT_BOLD, fg=TEXT_PRIMARY, bg=BG_SECONDARY)
        lbl.pack(anchor=tk.W, pady=(0, 6))
        return card

    # -------------------------------------------------------------
    # 1. Canvas Dimensions
    # -------------------------------------------------------------
    def _build_canvas_section(self):
        card = self._create_section_card("📐 Canvas Preset & Size")

        row1 = tk.Frame(card, bg=BG_SECONDARY)
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="Preset:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        
        self.canvas_preset_var = tk.StringVar()
        self.canvas_preset_combo = ttk.Combobox(
            row1,
            textvariable=self.canvas_preset_var,
            values=list(CANVAS_PRESETS.keys()),
            state="readonly"
        )
        self.canvas_preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.canvas_preset_combo.bind("<<ComboboxSelected>>", self._on_canvas_preset_changed)

        # Width & Height
        row2 = tk.Frame(card, bg=BG_SECONDARY)
        row2.pack(fill=tk.X, pady=4)
        tk.Label(row2, text="Size:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)

        self.canvas_w_var = tk.StringVar()
        self.canvas_h_var = tk.StringVar()

        tk.Entry(row2, textvariable=self.canvas_w_var, width=5, bg=BG_TERTIARY, fg=TEXT_PRIMARY, insertbackground="#FFF", relief=tk.FLAT).pack(side=tk.LEFT, padx=1)
        tk.Label(row2, text="×", fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(side=tk.LEFT, padx=1)
        tk.Entry(row2, textvariable=self.canvas_h_var, width=5, bg=BG_TERTIARY, fg=TEXT_PRIMARY, insertbackground="#FFF", relief=tk.FLAT).pack(side=tk.LEFT, padx=1)
        
        btn_apply_size = DarkButton(
            row2, text="Apply", bg=BTN_ACCENT_BG, hover_bg=BTN_ACCENT_HOVER, fg="#FFFFFF", font=FONT_SMALL, padx=8, pady=2,
            command=self._apply_custom_canvas_size
        )
        btn_apply_size.pack(side=tk.RIGHT, padx=2)

    def _on_canvas_preset_changed(self, event=None):
        preset_name = self.canvas_preset_var.get()
        proj = self.get_project()
        proj.set_preset(preset_name)
        self.canvas_w_var.set(str(proj.canvas_width))
        self.canvas_h_var.set(str(proj.canvas_height))
        self.on_change()

    def _apply_custom_canvas_size(self):
        try:
            w = int(self.canvas_w_var.get())
            h = int(self.canvas_h_var.get())
            if w > 0 and h > 0:
                proj = self.get_project()
                proj.preset_name = "Custom"
                proj.canvas_width = w
                proj.canvas_height = h
                self.canvas_preset_var.set("Custom")
                self.on_change()
        except ValueError:
            messagebox.showerror("Invalid Size", "Please enter positive integers for canvas width and height.")

    # -------------------------------------------------------------
    # 2. Background Settings
    # -------------------------------------------------------------
    def _build_background_section(self):
        card = self._create_section_card("🎨 Background & Gradient")

        # Preset
        row1 = tk.Frame(card, bg=BG_SECONDARY)
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="Preset:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        
        self.bg_preset_var = tk.StringVar()
        preset_names = [cfg["name"] for cfg in GRADIENT_PRESETS.values()] + ["Custom"]
        self.bg_preset_combo = ttk.Combobox(
            row1,
            textvariable=self.bg_preset_var,
            values=preset_names,
            state="readonly"
        )
        self.bg_preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.bg_preset_combo.bind("<<ComboboxSelected>>", self._on_bg_preset_changed)

        # Colors Start / End
        row2 = tk.Frame(card, bg=BG_SECONDARY)
        row2.pack(fill=tk.X, pady=4)
        tk.Label(row2, text="Colors:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)

        self.btn_bg_start = DarkButton(
            row2, text="Start", bg=BTN_BG_DEFAULT, fg=BTN_FG, font=FONT_SMALL, padx=6, pady=3,
            command=lambda: self._pick_bg_color("start")
        )
        self.btn_bg_start.pack(side=tk.LEFT, padx=1)

        self.btn_bg_end = DarkButton(
            row2, text="End", bg=BTN_BG_DEFAULT, fg=BTN_FG, font=FONT_SMALL, padx=6, pady=3,
            command=lambda: self._pick_bg_color("end")
        )
        self.btn_bg_end.pack(side=tk.LEFT, padx=1)

        # Direction
        self.bg_dir_var = tk.StringVar(value="vertical")
        dir_menu = ttk.Combobox(
            row2,
            textvariable=self.bg_dir_var,
            values=["vertical", "horizontal", "diagonal"],
            width=8,
            state="readonly"
        )
        dir_menu.pack(side=tk.RIGHT)
        dir_menu.bind("<<ComboboxSelected>>", self._on_bg_direction_changed)

        # Spotlight Controls
        row3 = tk.Frame(card, bg=BG_SECONDARY)
        row3.pack(fill=tk.X, pady=4)

        self.bg_spotlight_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(
            row3, text="Radial Spotlight", variable=self.bg_spotlight_var,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, selectcolor=BG_TERTIARY,
            activebackground=BG_SECONDARY, activeforeground=TEXT_PRIMARY,
            command=self._on_bg_spotlight_toggled, font=FONT_SMALL
        )
        chk.pack(side=tk.LEFT)

        # Spotlight Strength Slider
        row4 = tk.Frame(card, bg=BG_SECONDARY)
        row4.pack(fill=tk.X, pady=2)
        tk.Label(row4, text="Strength:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        self.bg_spotlight_scale = tk.Scale(
            row4, from_=0.0, to=0.8, resolution=0.02, orient=tk.HORIZONTAL,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, highlightthickness=0,
            command=self._on_spotlight_strength_changed
        )
        self.bg_spotlight_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _on_bg_preset_changed(self, event=None):
        name = self.bg_preset_var.get()
        page = self.get_active_page()
        for key, cfg in GRADIENT_PRESETS.items():
            if cfg["name"] == name:
                page.background.apply_preset(key)
                self.refresh()
                self.on_change()
                return

    def _pick_bg_color(self, which: str):
        page = self.get_active_page()
        curr = page.background.color_start if which == "start" else page.background.color_end
        color = colorchooser.askcolor(color=curr, title=f"Choose {which.title()} Background Color")
        if color and color[1]:
            if which == "start":
                page.background.color_start = color[1]
            else:
                page.background.color_end = color[1]
            page.background.preset = "custom"
            self.refresh()
            self.on_change()

    def _on_bg_direction_changed(self, event=None):
        page = self.get_active_page()
        page.background.direction = self.bg_dir_var.get()
        page.background.preset = "custom"
        self.on_change()

    def _on_bg_spotlight_toggled(self):
        page = self.get_active_page()
        page.background.spotlight_enabled = self.bg_spotlight_var.get()
        self.on_change()

    def _on_spotlight_strength_changed(self, val):
        if not getattr(self, "_initialized", False):
            return
        page = self.get_active_page()
        page.background.spotlight_strength = float(val)
        self.on_change()

    def refresh(self):
        proj = self.get_project()
        page = self.get_active_page()
        if not proj or not page:
            return

        self.canvas_preset_var.set(proj.preset_name)
        self.canvas_w_var.set(str(proj.canvas_width))
        self.canvas_h_var.set(str(proj.canvas_height))

        # Background
        bg_name = GRADIENT_PRESETS.get(page.background.preset, {}).get("name", "Custom")
        self.bg_preset_var.set(bg_name)
        self.btn_bg_start.configure(text=f"Start: {page.background.color_start}")
        self.btn_bg_end.configure(text=f"End: {page.background.color_end}")
        self.bg_dir_var.set(page.background.direction)
        self.bg_spotlight_var.set(page.background.spotlight_enabled)
        self.bg_spotlight_scale.set(page.background.spotlight_strength)
