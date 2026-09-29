from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from typing import Callable, Optional
import uuid

from core.models import (
    Project, Page, ImageLayer, TextLayer, LayerType,
    CANVAS_PRESETS, GRADIENT_PRESETS, TEXT_STYLE_PRESETS,
    FrameConfig
)
from core.fonts import get_available_font_names
from ui.theme import (
    BG_DARK, BG_SECONDARY, BG_TERTIARY, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_COLOR, ACCENT_LEMEMO, BORDER_COLOR, FONT_BOLD, FONT_SMALL, FONT_SYSTEM
)


class PropertyPanel(tk.Frame):
    """Right sidebar containing Canvas/Background settings, Layer list, and Inspector."""

    def __init__(
        self,
        parent,
        get_project: Callable[[], Project],
        get_active_page: Callable[[], Page],
        get_selected_layer: Callable[[], Optional[LayerType]],
        on_select_layer: Callable[[Optional[LayerType]], None],
        on_change: Callable[[], None],
        **kwargs
    ):
        super().__init__(parent, bg=BG_DARK, width=380, **kwargs)
        self.get_project = get_project
        self.get_active_page = get_active_page
        self.get_selected_layer = get_selected_layer
        self.on_select_layer = on_select_layer
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

        # Build Sub-Sections
        self._build_canvas_section()
        self._build_background_section()
        self._build_layers_section()
        self._build_inspector_section()

        self.refresh()

    def _on_panel_resize(self, event):
        self.canvas_scroll.itemconfig(self._scroll_window, width=event.width - 20)

    # -------------------------------------------------------------
    # Helper UI Builders
    # -------------------------------------------------------------
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
        tk.Label(row1, text="Preset:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=8, anchor=tk.W).pack(side=tk.LEFT)
        
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
        tk.Label(row2, text="Size:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=8, anchor=tk.W).pack(side=tk.LEFT)

        self.canvas_w_var = tk.StringVar()
        self.canvas_h_var = tk.StringVar()

        tk.Entry(row2, textvariable=self.canvas_w_var, width=6, bg=BG_TERTIARY, fg=TEXT_PRIMARY, insertbackground="#FFF", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Label(row2, text="×", fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(side=tk.LEFT, padx=2)
        tk.Entry(row2, textvariable=self.canvas_h_var, width=6, bg=BG_TERTIARY, fg=TEXT_PRIMARY, insertbackground="#FFF", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        
        btn_apply_size = tk.Button(
            row2, text="Apply", bg=ACCENT_COLOR, fg="#FFF", font=FONT_SMALL, relief=tk.FLAT,
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
        tk.Label(row1, text="Preset:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=8, anchor=tk.W).pack(side=tk.LEFT)
        
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
        tk.Label(row2, text="Colors:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=8, anchor=tk.W).pack(side=tk.LEFT)

        self.btn_bg_start = tk.Button(
            row2, text="Start", width=6, relief=tk.FLAT, font=FONT_SMALL,
            command=lambda: self._pick_bg_color("start")
        )
        self.btn_bg_start.pack(side=tk.LEFT, padx=2)

        self.btn_bg_end = tk.Button(
            row2, text="End", width=6, relief=tk.FLAT, font=FONT_SMALL,
            command=lambda: self._pick_bg_color("end")
        )
        self.btn_bg_end.pack(side=tk.LEFT, padx=2)

        # Direction
        self.bg_dir_var = tk.StringVar(value="vertical")
        dir_menu = ttk.Combobox(
            row2,
            textvariable=self.bg_dir_var,
            values=["vertical", "horizontal", "diagonal"],
            width=9,
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
        tk.Label(row4, text="Spotlight:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=8, anchor=tk.W).pack(side=tk.LEFT)
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
        page = self.get_active_page()
        page.background.spotlight_strength = float(val)
        self.on_change()

    # -------------------------------------------------------------
    # 3. Layer Manager
    # -------------------------------------------------------------
    def _build_layers_section(self):
        card = self._create_section_card("📚 Layers")

        # Layer actions row
        btn_row = tk.Frame(card, bg=BG_SECONDARY)
        btn_row.pack(fill=tk.X, pady=2)

        btn_add_img = tk.Button(
            btn_row, text="+ Screenshot", bg=BG_TERTIARY, fg=TEXT_PRIMARY,
            font=FONT_SMALL, relief=tk.FLAT, command=self._add_image_layer
        )
        btn_add_img.pack(side=tk.LEFT, padx=2)

        btn_add_txt = tk.Button(
            btn_row, text="+ Text", bg=BG_TERTIARY, fg=TEXT_PRIMARY,
            font=FONT_SMALL, relief=tk.FLAT, command=self._add_text_layer
        )
        btn_add_txt.pack(side=tk.LEFT, padx=2)

        btn_dup = tk.Button(
            btn_row, text="⧉ Dup", bg=BG_TERTIARY, fg=TEXT_PRIMARY,
            font=FONT_SMALL, relief=tk.FLAT, command=self._duplicate_layer
        )
        btn_dup.pack(side=tk.LEFT, padx=2)

        btn_up = tk.Button(
            btn_row, text="▲", bg=BG_TERTIARY, fg=TEXT_PRIMARY,
            font=FONT_SMALL, relief=tk.FLAT, command=self._move_layer_up
        )
        btn_up.pack(side=tk.LEFT, padx=2)

        btn_down = tk.Button(
            btn_row, text="▼", bg=BG_TERTIARY, fg=TEXT_PRIMARY,
            font=FONT_SMALL, relief=tk.FLAT, command=self._move_layer_down
        )
        btn_down.pack(side=tk.LEFT, padx=2)

        btn_del = tk.Button(
            btn_row, text="✕", bg=BG_TERTIARY, fg="#FF6961",
            font=FONT_SMALL, relief=tk.FLAT, command=self._delete_layer
        )
        btn_del.pack(side=tk.LEFT, padx=2)

        # Layer Listbox
        self.layer_listbox = tk.Listbox(
            card,
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            selectbackground=ACCENT_COLOR,
            selectforeground="#FFFFFF",
            font=FONT_SMALL,
            height=4,
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.layer_listbox.pack(fill=tk.X, pady=6)
        self.layer_listbox.bind("<<ListboxSelect>>", self._on_layer_listbox_select)

    def _refresh_layer_list(self):
        self.layer_listbox.delete(0, tk.END)
        page = self.get_active_page()
        selected = self.get_selected_layer()

        selected_idx = -1
        # Display in top-to-bottom visual order (last layer rendered on top)
        for i, layer in enumerate(reversed(page.layers)):
            icon = "🖼️" if isinstance(layer, ImageLayer) else "🔤"
            name = layer.name or ("Screenshot" if isinstance(layer, ImageLayer) else "Text")
            vis = "" if layer.visible else " (Hidden)"
            self.layer_listbox.insert(tk.END, f"{icon} {name}{vis}")
            if selected and layer.id == selected.id:
                selected_idx = i

        if selected_idx >= 0:
            self.layer_listbox.selection_set(selected_idx)

    def _on_layer_listbox_select(self, event=None):
        sel = self.layer_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        page = self.get_active_page()
        # Convert reversed list index
        real_idx = len(page.layers) - 1 - idx
        if 0 <= real_idx < len(page.layers):
            layer = page.layers[real_idx]
            self.on_select_layer(layer)
            self._build_inspector_fields()

    def _add_image_layer(self):
        file_path = filedialog.askopenfilename(
            title="Select Screenshot Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")]
        )
        if not file_path:
            return

        proj = self.get_project()
        page = self.get_active_page()
        new_layer = ImageLayer(
            name=f"Screenshot {len(page.layers)+1}",
            file_path=file_path,
            x=proj.canvas_width / 2,
            y=proj.canvas_height * 0.60,
            scale=0.9
        )
        page.layers.append(new_layer)
        self.on_select_layer(new_layer)
        self.refresh()
        self.on_change()

    def _add_text_layer(self):
        proj = self.get_project()
        page = self.get_active_page()
        new_layer = TextLayer(
            name=f"Text {len(page.layers)+1}",
            text="新しい見出し",
            x=proj.canvas_width / 2,
            y=proj.canvas_height * 0.12,
            font_size=84,
            font_weight="bold",
            color="#FFFFFF"
        )
        page.layers.append(new_layer)
        self.on_select_layer(new_layer)
        self.refresh()
        self.on_change()

    def _duplicate_layer(self):
        selected = self.get_selected_layer()
        if not selected:
            return
        page = self.get_active_page()
        new_layer = copy.deepcopy(selected)
        new_layer.id = str(uuid.uuid4())
        new_layer.name = f"{selected.name} (Copy)"
        new_layer.x += 40
        new_layer.y += 40
        page.layers.append(new_layer)
        self.on_select_layer(new_layer)
        self.refresh()
        self.on_change()

    def _move_layer_up(self):
        selected = self.get_selected_layer()
        if not selected:
            return
        page = self.get_active_page()
        idx = page.layers.index(selected)
        if idx < len(page.layers) - 1:
            page.layers[idx], page.layers[idx + 1] = page.layers[idx + 1], page.layers[idx]
            self.refresh()
            self.on_change()

    def _move_layer_down(self):
        selected = self.get_selected_layer()
        if not selected:
            return
        page = self.get_active_page()
        idx = page.layers.index(selected)
        if idx > 0:
            page.layers[idx], page.layers[idx - 1] = page.layers[idx - 1], page.layers[idx]
            self.refresh()
            self.on_change()

    def _delete_layer(self):
        selected = self.get_selected_layer()
        if not selected:
            return
        page = self.get_active_page()
        if selected in page.layers:
            page.layers.remove(selected)
            self.on_select_layer(None)
            self.refresh()
            self.on_change()

    # -------------------------------------------------------------
    # 4. Inspector / Selected Layer Properties
    # -------------------------------------------------------------
    def _build_inspector_section(self):
        self.inspector_card = self._create_section_card("⚙️ Layer Properties")
        self.inspector_container = tk.Frame(self.inspector_card, bg=BG_SECONDARY)
        self.inspector_container.pack(fill=tk.BOTH, expand=True)

    def _build_inspector_fields(self):
        for widget in self.inspector_container.winfo_children():
            widget.destroy()

        layer = self.get_selected_layer()
        if not layer:
            lbl = tk.Label(
                self.inspector_container,
                text="No layer selected.\nClick a layer on canvas or list above.",
                font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_SECONDARY, justify=tk.CENTER, pady=16
            )
            lbl.pack()
            return

        # Common: Name & Visibility
        row_name = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        row_name.pack(fill=tk.X, pady=2)
        tk.Label(row_name, text="Name:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        
        name_var = tk.StringVar(value=layer.name)
        def _on_name_change(*args):
            layer.name = name_var.get()
            self._refresh_layer_list()
        name_var.trace_add("write", _on_name_change)
        tk.Entry(row_name, textvariable=name_var, bg=BG_TERTIARY, fg=TEXT_PRIMARY, insertbackground="#FFF", relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Position X / Y
        row_pos = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        row_pos.pack(fill=tk.X, pady=4)
        tk.Label(row_pos, text="Position:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)

        tk.Label(row_pos, text="X", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(side=tk.LEFT)
        x_var = tk.StringVar(value=str(int(layer.x)))
        def _on_x_change(*args):
            try:
                layer.x = float(x_var.get())
                self.on_change()
            except ValueError:
                pass
        x_var.trace_add("write", _on_x_change)
        tk.Entry(row_pos, textvariable=x_var, width=5, bg=BG_TERTIARY, fg=TEXT_PRIMARY, insertbackground="#FFF", relief=tk.FLAT).pack(side=tk.LEFT, padx=3)

        tk.Label(row_pos, text="Y", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(side=tk.LEFT)
        y_var = tk.StringVar(value=str(int(layer.y)))
        def _on_y_change(*args):
            try:
                layer.y = float(y_var.get())
                self.on_change()
            except ValueError:
                pass
        y_var.trace_add("write", _on_y_change)
        tk.Entry(row_pos, textvariable=y_var, width=5, bg=BG_TERTIARY, fg=TEXT_PRIMARY, insertbackground="#FFF", relief=tk.FLAT).pack(side=tk.LEFT, padx=3)

        # Image Layer Fields
        if isinstance(layer, ImageLayer):
            self._build_image_layer_inspector(layer)
        # Text Layer Fields
        elif isinstance(layer, TextLayer):
            self._build_text_layer_inspector(layer)

    def _build_image_layer_inspector(self, layer: ImageLayer):
        # Image Source Row
        row_img = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        row_img.pack(fill=tk.X, pady=4)
        tk.Label(row_img, text="Image:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        
        btn_change = tk.Button(
            row_img, text="Replace Image...", bg=BG_TERTIARY, fg=TEXT_PRIMARY,
            font=FONT_SMALL, relief=tk.FLAT,
            command=lambda: self._replace_image_layer_file(layer)
        )
        btn_change.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Scale slider
        row_scale = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        row_scale.pack(fill=tk.X, pady=2)
        tk.Label(row_scale, text="Scale:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        scale_slider = tk.Scale(
            row_scale, from_=0.2, to=1.8, resolution=0.01, orient=tk.HORIZONTAL,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, highlightthickness=0,
            command=lambda v: self._update_layer_prop(layer, "scale", float(v))
        )
        scale_slider.set(layer.scale)
        scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Rotation slider
        row_rot = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        row_rot.pack(fill=tk.X, pady=2)
        tk.Label(row_rot, text="Rotate:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        rot_slider = tk.Scale(
            row_rot, from_=-30, to=30, resolution=1, orient=tk.HORIZONTAL,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, highlightthickness=0,
            command=lambda v: self._update_layer_prop(layer, "rotation", float(v))
        )
        rot_slider.set(int(layer.rotation))
        rot_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Device Frame Sub-section
        frame_box = tk.LabelFrame(self.inspector_container, text="📱 Device Frame & Shadow", bg=BG_SECONDARY, fg=TEXT_PRIMARY, font=FONT_BOLD, padx=8, pady=6)
        frame_box.pack(fill=tk.X, pady=8)

        # Frame Enable
        frame_en_var = tk.BooleanVar(value=layer.frame.enabled)
        def _on_frame_en():
            layer.frame.enabled = frame_en_var.get()
            self.on_change()
        tk.Checkbutton(
            frame_box, text="Enable Frame", variable=frame_en_var,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, selectcolor=BG_TERTIARY,
            activebackground=BG_SECONDARY, activeforeground=TEXT_PRIMARY,
            command=_on_frame_en, font=FONT_SMALL
        ).pack(anchor=tk.W)

        # Corner Radius
        r_row = tk.Frame(frame_box, bg=BG_SECONDARY)
        r_row.pack(fill=tk.X, pady=2)
        tk.Label(r_row, text="Radius:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        r_slider = tk.Scale(
            r_row, from_=0, to=120, resolution=2, orient=tk.HORIZONTAL,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, highlightthickness=0,
            command=lambda v: self._update_frame_prop(layer, "corner_radius", int(v))
        )
        r_slider.set(layer.frame.corner_radius)
        r_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Border Width & Color
        b_row = tk.Frame(frame_box, bg=BG_SECONDARY)
        b_row.pack(fill=tk.X, pady=2)
        tk.Label(b_row, text="Border:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        b_slider = tk.Scale(
            b_row, from_=0, to=24, resolution=1, orient=tk.HORIZONTAL,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, highlightthickness=0,
            command=lambda v: self._update_frame_prop(layer, "border_width", int(v))
        )
        b_slider.set(layer.frame.border_width)
        b_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        b_color_btn = tk.Button(
            b_row, text="Color", bg=layer.frame.border_color, fg="#FFF", font=FONT_SMALL, relief=tk.FLAT,
            command=lambda: self._pick_frame_border_color(layer)
        )
        b_color_btn.pack(side=tk.RIGHT, padx=2)

        # Shadow Enable & Opacity
        sh_row = tk.Frame(frame_box, bg=BG_SECONDARY)
        sh_row.pack(fill=tk.X, pady=2)
        tk.Label(sh_row, text="Shadow:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        sh_slider = tk.Scale(
            sh_row, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, highlightthickness=0,
            command=lambda v: self._update_frame_prop(layer, "shadow_opacity", float(v))
        )
        sh_slider.set(layer.frame.shadow_opacity)
        sh_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Shadow Blur & Offset
        sh_blur_row = tk.Frame(frame_box, bg=BG_SECONDARY)
        sh_blur_row.pack(fill=tk.X, pady=2)
        tk.Label(sh_blur_row, text="Blur / Y:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        
        sh_blur_slider = tk.Scale(
            sh_blur_row, from_=0, to=100, resolution=2, orient=tk.HORIZONTAL,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, highlightthickness=0,
            command=lambda v: self._update_frame_prop(layer, "shadow_blur", int(v))
        )
        sh_blur_slider.set(layer.frame.shadow_blur)
        sh_blur_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _replace_image_layer_file(self, layer: ImageLayer):
        path = filedialog.askopenfilename(
            title="Replace Screenshot Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")]
        )
        if path:
            layer.file_path = path
            self.refresh()
            self.on_change()

    def _update_layer_prop(self, layer, prop, val):
        setattr(layer, prop, val)
        self.on_change()

    def _update_frame_prop(self, layer: ImageLayer, prop, val):
        setattr(layer.frame, prop, val)
        self.on_change()

    def _pick_frame_border_color(self, layer: ImageLayer):
        color = colorchooser.askcolor(color=layer.frame.border_color, title="Choose Frame Border Color")
        if color and color[1]:
            layer.frame.border_color = color[1]
            self._build_inspector_fields()
            self.on_change()

    def _build_text_layer_inspector(self, layer: TextLayer):
        # Text Editor Area
        tk.Label(self.inspector_container, text="Text Content:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(anchor=tk.W, pady=(4, 1))
        
        txt_box = tk.Text(
            self.inspector_container,
            height=3,
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            insertbackground="#FFF",
            font=("Hiragino Sans", 13),
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        txt_box.insert("1.0", layer.text)
        txt_box.pack(fill=tk.X, pady=2)

        def _on_text_box_key(event=None):
            content = txt_box.get("1.0", "end-1c")
            layer.text = content
            self.on_change()

        txt_box.bind("<KeyRelease>", _on_text_box_key)

        # Style Presets Row
        style_row = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        style_row.pack(fill=tk.X, pady=4)
        tk.Label(style_row, text="Preset:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)

        style_var = tk.StringVar(value=layer.style_preset.title())
        style_combo = ttk.Combobox(
            style_row,
            textvariable=style_var,
            values=["Hero", "Headline", "Subheadline", "Caption"],
            state="readonly"
        )
        style_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def _on_style_selected(event=None):
            key = style_var.get().lower()
            layer.apply_style_preset(key)
            self._build_inspector_fields()
            self.on_change()

        style_combo.bind("<<ComboboxSelected>>", _on_style_selected)

        # Font Family & Size
        font_row = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        font_row.pack(fill=tk.X, pady=4)
        tk.Label(font_row, text="Font:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)

        font_var = tk.StringVar(value=layer.font_family)
        font_combo = ttk.Combobox(
            font_row,
            textvariable=font_var,
            values=get_available_font_names(),
            state="readonly",
            width=14
        )
        font_combo.pack(side=tk.LEFT, padx=2)
        def _on_font_selected(event=None):
            layer.font_family = font_var.get()
            self.on_change()
        font_combo.bind("<<ComboboxSelected>>", _on_font_selected)

        # Font Size
        tk.Label(font_row, text="Pt:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(side=tk.LEFT, padx=2)
        size_var = tk.StringVar(value=str(layer.font_size))
        def _on_size_change(*args):
            try:
                s = int(size_var.get())
                if s > 5:
                    layer.font_size = s
                    self.on_change()
            except ValueError:
                pass
        size_var.trace_add("write", _on_size_change)
        tk.Entry(font_row, textvariable=size_var, width=4, bg=BG_TERTIARY, fg=TEXT_PRIMARY, insertbackground="#FFF", relief=tk.FLAT).pack(side=tk.LEFT)

        # Weight & Align
        opt_row = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        opt_row.pack(fill=tk.X, pady=4)

        bold_var = tk.BooleanVar(value=(layer.font_weight == "bold"))
        def _on_bold_toggle():
            layer.font_weight = "bold" if bold_var.get() else "regular"
            self.on_change()
        tk.Checkbutton(
            opt_row, text="Bold", variable=bold_var,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, selectcolor=BG_TERTIARY,
            activebackground=BG_SECONDARY, activeforeground=TEXT_PRIMARY,
            command=_on_bold_toggle, font=FONT_SMALL
        ).pack(side=tk.LEFT, padx=2)

        # Align buttons
        align_frame = tk.Frame(opt_row, bg=BG_SECONDARY)
        align_frame.pack(side=tk.RIGHT)
        for a_mode, a_icon in [("left", "⬅"), ("center", "⬌"), ("right", "➡")]:
            btn = tk.Button(
                align_frame, text=a_icon, bg=ACCENT_COLOR if layer.align == a_mode else BG_TERTIARY,
                fg="#FFF", font=FONT_SMALL, relief=tk.FLAT, padx=6,
                command=lambda m=a_mode: self._set_text_align(layer, m)
            )
            btn.pack(side=tk.LEFT, padx=1)

        # Color Palette & Custom Color Picker
        color_row = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        color_row.pack(fill=tk.X, pady=4)
        tk.Label(color_row, text="Color:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)

        preset_colors = [
            ("#FFFFFF", "White"),
            ("#F2F2F2", "Soft White"),
            ("#D8D8D8", "Secondary"),
            ("#B34254", "Le'memo Accent"),
            ("#D4AF37", "Gold")
        ]
        for c_hex, c_name in preset_colors:
            c_btn = tk.Button(
                color_row, bg=c_hex, width=2, relief=tk.FLAT,
                command=lambda c=c_hex: self._set_text_color(layer, c)
            )
            c_btn.pack(side=tk.LEFT, padx=2)

        custom_col_btn = tk.Button(
            color_row, text="🎨", bg=BG_TERTIARY, fg=TEXT_PRIMARY, font=FONT_SMALL, relief=tk.FLAT,
            command=lambda: self._pick_text_custom_color(layer)
        )
        custom_col_btn.pack(side=tk.LEFT, padx=4)

        # Max Width (Auto-wrap) & Line Spacing
        wrap_row = tk.Frame(self.inspector_container, bg=BG_SECONDARY)
        wrap_row.pack(fill=tk.X, pady=2)
        tk.Label(wrap_row, text="Max W:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, width=7, anchor=tk.W).pack(side=tk.LEFT)
        wrap_slider = tk.Scale(
            wrap_row, from_=300, to=1500, resolution=20, orient=tk.HORIZONTAL,
            bg=BG_SECONDARY, fg=TEXT_PRIMARY, highlightthickness=0,
            command=lambda v: self._update_layer_prop(layer, "max_width", int(v))
        )
        wrap_slider.set(layer.max_width)
        wrap_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _set_text_align(self, layer: TextLayer, align: str):
        layer.align = align
        self._build_inspector_fields()
        self.on_change()

    def _set_text_color(self, layer: TextLayer, color_hex: str):
        layer.color = color_hex
        self.on_change()

    def _pick_text_custom_color(self, layer: TextLayer):
        color = colorchooser.askcolor(color=layer.color, title="Choose Text Color")
        if color and color[1]:
            layer.color = color[1]
            self.on_change()

    # -------------------------------------------------------------
    # Refresh All Fields
    # -------------------------------------------------------------
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
        self.btn_bg_start.configure(bg=page.background.color_start)
        self.btn_bg_end.configure(bg=page.background.color_end)
        self.bg_dir_var.set(page.background.direction)
        self.bg_spotlight_var.set(page.background.spotlight_enabled)
        self.bg_spotlight_scale.set(page.background.spotlight_strength)

        self._refresh_layer_list()
        self._build_inspector_fields()
