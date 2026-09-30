"""Pure crop-editor geometry in source pixels; no Tkinter or project state."""
import math
from core.image_geometry import MIN_CROP_FRACTION

ASPECT_MODES = ("Free", "Original", "1:1", "9:16", "16:9")


def get_aspect_ratio(mode, source_size):
    width, height = source_size
    if mode == "Free":
        return None
    if mode == "Original":
        return width / height
    return {"1:1": 1.0, "9:16": 9 / 16, "16:9": 16 / 9}[mode]


def minimum_crop_size(source_size):
    return tuple(max(1, math.ceil(size * MIN_CROP_FRACTION)) for size in source_size)


def _height_limits(source_size, ratio):
    width, height = source_size
    min_w, min_h = minimum_crop_size(source_size)
    minimum = max(min_h, min_w / ratio)
    maximum = min(height, width / ratio)
    if minimum > maximum + 1e-9:
        raise ValueError("This aspect ratio cannot fit the image while keeping the minimum crop size.")
    return minimum, maximum


def fit_crop_to_ratio(box, source_size, ratio):
    """Largest matching box inside the selection, expanded only for minimum size.

    Retain the center unless the image boundary requires shifting it inward.
    Floating pixel coordinates keep the ratio exact until Apply's pixel snapping.
    """
    if ratio is None:
        return list(box)
    left, top, right, bottom = box
    width, height = source_size
    minimum, maximum = _height_limits(source_size, ratio)
    crop_h = min(maximum, max(minimum, min(bottom-top, (right-left)/ratio)))
    crop_w = crop_h * ratio
    left = max(0.0, min(width-crop_w, (left+right-crop_w)/2))
    top = max(0.0, min(height-crop_h, (top+bottom-crop_h)/2))
    return [left, top, left+crop_w, top+crop_h]


def resize_crop_with_ratio(box, source_size, handle, dx, dy, ratio):
    """Keep the opposite corner/edge anchored; clamp before crossing or escaping.

    Corners project pointer movement onto the ratio diagonal. Edges keep the
    opposite edge midpoint anchored and resize symmetrically on the other axis.
    """
    left, top, right, bottom = box
    width, height = source_size
    minimum, _ = _height_limits(source_size, ratio)
    sx = -1 if "w" in handle else 1
    sy = -1 if "n" in handle else 1
    cx, cy = (left+right)/2, (top+bottom)/2
    if len(handle) == 2:
        anchor_x = right if sx < 0 else left
        anchor_y = bottom if sy < 0 else top
        available_w = anchor_x if sx < 0 else width-anchor_x
        available_h = anchor_y if sy < 0 else height-anchor_y
        maximum = min(available_h, available_w/ratio)
        wanted = (bottom-top) + (ratio*sx*dx + sy*dy)/(ratio*ratio+1)
    elif handle in ("e", "w"):
        anchor_x = right if sx < 0 else left
        maximum = min((anchor_x if sx < 0 else width-anchor_x)/ratio,
                      2*min(cy, height-cy))
        wanted = (right-left+sx*dx)/ratio
    elif handle in ("n", "s"):
        anchor_y = bottom if sy < 0 else top
        maximum = min(anchor_y if sy < 0 else height-anchor_y,
                      2*min(cx, width-cx)/ratio)
        wanted = bottom-top+sy*dy
    else:
        raise ValueError(f"Unknown crop handle: {handle}")
    crop_h = min(maximum, max(minimum, wanted))
    crop_w = crop_h * ratio
    if len(handle) == 2:
        x, y = anchor_x+sx*crop_w, anchor_y+sy*crop_h
        return [min(anchor_x,x), min(anchor_y,y), max(anchor_x,x), max(anchor_y,y)]
    if handle in ("e", "w"):
        x = anchor_x+sx*crop_w
        return [min(anchor_x,x), cy-crop_h/2, max(anchor_x,x), cy+crop_h/2]
    y = anchor_y+sy*crop_h
    return [cx-crop_w/2, min(anchor_y,y), cx+crop_w/2, max(anchor_y,y)]


def snap_crop_to_pixels(box, source_size):
    """Round dimensions rather than both edges, preserving minimum pixel extents."""
    left, top, right, bottom = box
    width, height = source_size
    min_w, min_h = minimum_crop_size(source_size)
    crop_w = min(width, max(min_w, round(right-left)))
    crop_h = min(height, max(min_h, round(bottom-top)))
    left = max(0, min(width-crop_w, round((left+right-crop_w)/2)))
    top = max(0, min(height-crop_h, round((top+bottom-crop_h)/2)))
    return [left, top, left+crop_w, top+crop_h]
