from __future__ import annotations
import tkinter as tk
from typing import Optional, Callable, Tuple, List
from PIL import ImageTk, Image

from core.models import Project, Page, ImageLayer, TextLayer, LayerType
from core.renderer import (
    render_page, get_cached_image, get_text_layer_metrics
)
from ui.theme import BG_DARK, ACCENT_COLOR, HIGHLIGHT_COLOR


class CanvasView(tk.Frame):
    """Interactive preview canvas supporting drag-and-drop layer movement and scaling."""

    def __init__(
        self,
        parent,
        get_project: Callable[[], Project],
        get_active_page: Callable[[], Page],
        on_layer_selected: Callable[[Optional[LayerType]], None],
        on_content_changed: Callable[[], None],
        **kwargs
    ):
        super().__init__(parent, bg=BG_DARK, **kwargs)
        self.get_project = get_project
        self.get_active_page = get_active_page
        self.on_layer_selected = on_layer_selected
        self.on_content_changed = on_content_changed

        self.selected_layer: Optional[LayerType] = None
        self.show_guides = True

        # Scale & offset tracking
        self.display_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Drag tracking
        self._drag_start_canvas_x = 0.0
        self._drag_start_canvas_y = 0.0
        self._layer_start_x = 0.0
        self._layer_start_y = 0.0
        self._layer_start_scale = 1.0
        self._is_dragging = False
        self._is_resizing = False
        self._active_handle = None

        # Canvas widget
        self.canvas = tk.Canvas(self, bg=BG_DARK, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._photo_image = None
        self._image_canvas_id = None

        # Bind events
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

    def set_show_guides(self, show: bool):
        self.show_guides = show
        self.refresh()

    def set_selected_layer(self, layer: Optional[LayerType]):
        self.selected_layer = layer
        self.draw_overlay_selection()

    def _on_resize(self, event=None):
        self.refresh()

    def refresh(self):
        """Re-renders the current page preview onto the canvas."""
        self.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            return

        project = self.get_project()
        page = self.get_active_page()
        if not project or not page:
            return

        proj_w = project.canvas_width
        proj_h = project.canvas_height

        # Calculate best fit scale with margin
        margin = 30
        avail_w = max(50, cw - margin * 2)
        avail_h = max(50, ch - margin * 2)
        self.display_scale = min(avail_w / proj_w, avail_h / proj_h)

        disp_w = int(proj_w * self.display_scale)
        disp_h = int(proj_h * self.display_scale)

        self.offset_x = (cw - disp_w) // 2
        self.offset_y = (ch - disp_h) // 2

        # Render page
        pil_img = render_page(
            project,
            page,
            show_guides=self.show_guides,
            scale_factor=self.display_scale
        )

        self._photo_image = ImageTk.PhotoImage(pil_img)
        self.canvas.delete("all")
        self._image_canvas_id = self.canvas.create_image(
            self.offset_x, self.offset_y,
            anchor=tk.NW,
            image=self._photo_image
        )

        # Draw selection rectangle and handles if a layer is selected
        self.draw_overlay_selection()

    def canvas_to_screen_coords(self, cx: float, cy: float) -> Tuple[float, float]:
        """Converts canvas project coordinates to screen pixel coordinates."""
        sx = self.offset_x + cx * self.display_scale
        sy = self.offset_y + cy * self.display_scale
        return sx, sy

    def screen_to_canvas_coords(self, sx: float, sy: float) -> Tuple[float, float]:
        """Converts screen pixel coordinates to canvas project coordinates."""
        cx = (sx - self.offset_x) / max(0.0001, self.display_scale)
        cy = (sy - self.offset_y) / max(0.0001, self.display_scale)
        return cx, cy

    def get_layer_bbox_canvas(self, layer: LayerType) -> Tuple[float, float, float, float]:
        """Returns (left, top, right, bottom) in canvas project coordinates."""
        project = self.get_project()
        cw = project.canvas_width

        if isinstance(layer, ImageLayer):
            src_img = get_cached_image(layer.file_path)
            if src_img:
                base_w = cw * 0.8
                s = max(0.05, layer.scale)
                tw = base_w * s
                th = tw * (src_img.height / max(1, src_img.width))
            else:
                tw, th = 300 * layer.scale, 500 * layer.scale
            return (layer.x - tw / 2, layer.y - th / 2, layer.x + tw / 2, layer.y + th / 2)

        elif isinstance(layer, TextLayer):
            tw, th, lines, _ = get_text_layer_metrics(layer, cw)
            pad = 20
            w = tw + pad * 2
            h = th + pad * 2
            left = layer.x - w / 2
            top = layer.y - pad
            return (left, top, left + w, top + h)

        return (0, 0, 0, 0)

    def draw_overlay_selection(self):
        """Draws visual selection box and handles for currently selected layer."""
        self.canvas.delete("selection_box")
        if not self.selected_layer or not self.selected_layer.visible:
            return

        l, t, r, b = self.get_layer_bbox_canvas(self.selected_layer)
        sx1, sy1 = self.canvas_to_screen_coords(l, t)
        sx2, sy2 = self.canvas_to_screen_coords(r, b)

        # Selection rectangle
        self.canvas.create_rectangle(
            sx1, sy1, sx2, sy2,
            outline=ACCENT_COLOR,
            width=2,
            dash=(4, 4),
            tags="selection_box"
        )

        # Draw 4 corner handles
        handle_size = 5
        corners = [
            ("nw", sx1, sy1),
            ("ne", sx2, sy1),
            ("sw", sx1, sy2),
            ("se", sx2, sy2),
        ]
        for name, hx, hy in corners:
            self.canvas.create_rectangle(
                hx - handle_size, hy - handle_size,
                hx + handle_size, hy + handle_size,
                fill=ACCENT_COLOR,
                outline="#FFFFFF",
                width=1,
                tags=("selection_box", f"handle_{name}")
            )

    def _hit_test_handle(self, sx: float, sy: float) -> Optional[str]:
        """Checks if a corner handle was clicked."""
        if not self.selected_layer:
            return None
        l, t, r, b = self.get_layer_bbox_canvas(self.selected_layer)
        sx1, sy1 = self.canvas_to_screen_coords(l, t)
        sx2, sy2 = self.canvas_to_screen_coords(r, b)
        
        tol = 10
        if abs(sx1 - sx) <= tol and abs(sy1 - sy) <= tol:
            return "nw"
        if abs(sx2 - sx) <= tol and abs(sy1 - sy) <= tol:
            return "ne"
        if abs(sx1 - sx) <= tol and abs(sy2 - sy) <= tol:
            return "sw"
        if abs(sx2 - sx) <= tol and abs(sy2 - sy) <= tol:
            return "se"
        return None

    def _on_mouse_down(self, event):
        sx, sy = event.x, event.y
        cx, cy = self.screen_to_canvas_coords(sx, sy)

        # 1. Check if clicking on a resize handle of current selection
        handle = self._hit_test_handle(sx, sy)
        if handle and isinstance(self.selected_layer, ImageLayer):
            self._is_resizing = True
            self._active_handle = handle
            self._drag_start_canvas_x = cx
            self._drag_start_canvas_y = cy
            self._layer_start_scale = self.selected_layer.scale
            return

        # 2. Check if clicked inside any layer (topmost first)
        page = self.get_active_page()
        hit_layer = None
        for layer in reversed(page.layers):
            if not layer.visible or layer.locked:
                continue
            l, t, r, b = self.get_layer_bbox_canvas(layer)
            if l <= cx <= r and t <= cy <= b:
                hit_layer = layer
                break

        self.selected_layer = hit_layer
        self.on_layer_selected(hit_layer)
        self.draw_overlay_selection()

        if hit_layer is not None:
            self._is_dragging = True
            self._drag_start_canvas_x = cx
            self._drag_start_canvas_y = cy
            self._layer_start_x = hit_layer.x
            self._layer_start_y = hit_layer.y

    def _on_mouse_drag(self, event):
        if not self.selected_layer:
            return

        cx, cy = self.screen_to_canvas_coords(event.x, event.y)
        dx = cx - self._drag_start_canvas_x
        dy = cy - self._drag_start_canvas_y

        if self._is_resizing and isinstance(self.selected_layer, ImageLayer):
            # Scale based on drag distance
            dist_delta = (dx + dy) / 400.0
            new_scale = max(0.1, min(3.0, self._layer_start_scale + dist_delta))
            self.selected_layer.scale = round(new_scale, 3)
            self.refresh()
            self.on_content_changed()

        elif self._is_dragging:
            self.selected_layer.x = round(self._layer_start_x + dx)
            self.selected_layer.y = round(self._layer_start_y + dy)
            self.refresh()
            self.on_content_changed()

    def _on_mouse_up(self, event):
        self._is_dragging = False
        self._is_resizing = False
        self._active_handle = None
        self.draw_overlay_selection()
