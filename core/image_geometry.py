"""Pixel-aligned, non-destructive image crop geometry (no UI dependencies)."""
import math

from core.models import ImageLayer


MIN_CROP_FRACTION = 0.01


def _crop_axis(start, end, size):
    def bounded(value, default):
        try:
            value = float(value)
            return min(1.0, max(0.0, value)) if math.isfinite(value) else default
        except (TypeError, ValueError, OverflowError):
            return default

    start, end = sorted((bounded(start, 0.0), bounded(end, 1.0)))
    minimum = max(1, math.ceil(size * MIN_CROP_FRACTION))
    left, right = round(start * size), round(end * size)
    if right - left < minimum:
        left = min(left, size - minimum)
        right = left + minimum
    return left, right


def get_image_layer_crop_box(layer: ImageLayer, source_size):
    """Return Pillow's exclusive-right/bottom box, bounded to the source.

    Reversed edges are sorted. Tiny selections expand toward right/bottom,
    shifting inward at the image edge. Each axis retains at least 1% / 1px.
    Invalid non-finite values fall back to the corresponding full-image edge.
    """
    width, height = source_size
    if width < 1 or height < 1:
        raise ValueError("Source dimensions must be positive")
    left, right = _crop_axis(layer.crop_left, layer.crop_right, width)
    top, bottom = _crop_axis(layer.crop_top, layer.crop_bottom, height)
    return left, top, right, bottom


def get_image_layer_source_dimensions(layer: ImageLayer, source_size):
    left, top, right, bottom = get_image_layer_crop_box(layer, source_size)
    return right - left, bottom - top


def get_image_layer_render_dimensions(layer: ImageLayer, source_size, canvas_width):
    width, height = get_image_layer_source_dimensions(layer, source_size)
    target_width = max(1, int(canvas_width * 0.8 * max(0.05, layer.scale)))
    return target_width, max(1, int(target_width * height / width))
