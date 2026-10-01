"""Shared image effect controls for the current and legacy inspectors."""
import tkinter as tk
from tkinter import colorchooser
from core.models import ImageEffectsConfig
from ui.theme import (BG_SECONDARY, BG_TERTIARY, TEXT_PRIMARY, TEXT_SECONDARY,
                      FONT_BOLD, FONT_SMALL, BTN_BG_DEFAULT, BTN_FG)
from ui.widgets import DarkButton
from ui.collapsible_section import inspector_section


def build_image_effects(self, layer):
    box = inspector_section(self, "image", "Image Effects")
    config = layer.effects
    config.normalize()
    sliders = {}

    def update(prop, value):
        setattr(config, prop, value)
        before = (config.fade_start, config.fade_end)
        if prop in ("fade_start", "fade_end"):
            config.fade_start = min(.95, config.fade_start)
            config.fade_end = max(.05, config.fade_start + .01, config.fade_end)
        config.normalize()
        for name in ("fade_start", "fade_end"):
            slider = sliders.get(name)
            prior = before[0 if name == "fade_start" else 1]
            if slider is not None and prior != getattr(config, name):
                slider.set(getattr(config, name))
        self.on_change()

    for prop, label in [("fade_enabled", "Bottom Fade"), ("shadow_enabled", "Drop Shadow")]:
        var = tk.BooleanVar(value=getattr(config, prop))
        tk.Checkbutton(box, text=label, variable=var, bg=BG_SECONDARY,
                       fg=TEXT_PRIMARY, selectcolor=BG_TERTIARY, font=FONT_SMALL,
                       command=lambda p=prop, v=var: update(p, v.get())).pack(anchor=tk.W)
        fields = ([("fade_start", "Start", 0, .95, .01),
                   ("fade_end", "End", .05, 1, .01)] if prop == "fade_enabled" else
                  [("shadow_opacity", "Opacity", 0, 1, .01),
                   ("shadow_blur", "Blur", 0, 100, 1),
                   ("shadow_offset_x", "Offset X", -100, 100, 1),
                   ("shadow_offset_y", "Offset Y", -100, 100, 1)])
        for name, title, low, high, step in fields:
            row = tk.Frame(box, bg=BG_SECONDARY)
            row.pack(fill=tk.X)
            tk.Label(row, text=title + ":", width=8, anchor=tk.W,
                     bg=BG_SECONDARY, fg=TEXT_SECONDARY, font=FONT_SMALL).pack(side=tk.LEFT)
            slider = tk.Scale(row, from_=low, to=high, resolution=step,
                              orient=tk.HORIZONTAL, bg=BG_SECONDARY,
                              fg=TEXT_PRIMARY, highlightthickness=0)
            slider.set(getattr(config, name))
            slider.configure(command=lambda v, p=name: update(p, float(v)))
            slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
            sliders[name] = slider

    def pick_color():
        color = colorchooser.askcolor(color=config.shadow_color, title="Image Shadow Color")
        if color and color[1]:
            update("shadow_color", color[1])
            color_button.configure(text="Color: " + config.shadow_color)

    color_button = DarkButton(box, text="Color: " + config.shadow_color,
                              command=pick_color, bg=BTN_BG_DEFAULT, fg=BTN_FG, font=FONT_SMALL)
    color_button.pack(fill=tk.X, pady=3)

    def reset():
        layer.effects = ImageEffectsConfig()
        self._build_inspector_fields()
        self.on_change()

    DarkButton(box, text="Reset Effects", command=reset, bg=BTN_BG_DEFAULT,
               fg=BTN_FG, font=FONT_SMALL).pack(fill=tk.X)

