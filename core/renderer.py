from __future__ import annotations
import math
import os
import functools
from typing import Tuple, List, Optional, Dict
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageColor, ImageChops

from core.models import (
    Project, Page, ImageLayer, TextLayer, LayerType,
    GradientConfig, FrameConfig, CANVAS_PRESETS
)
from core.image_effects import apply_bottom_fade, create_alpha_shadow
from core.fonts import load_font
from core.panorama import get_workspace_geometry
from dataclasses import replace
from core.image_geometry import get_image_layer_crop_box, get_image_layer_render_dimensions


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Converts a hex color string to an (R, G, B) tuple."""
    try:
        c = ImageColor.getrgb(hex_str)
        return c[:3]
    except Exception:
        return (0, 0, 0)


@functools.lru_cache(maxsize=32)
def load_and_cache_image(file_path: str, mtime: float) -> Optional[Image.Image]:
    """Loads an image and caches it in memory."""
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        im = Image.open(file_path).convert("RGBA")
        return im
    except Exception:
        return None


def get_cached_image(file_path: str) -> Optional[Image.Image]:
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        mtime = os.path.getmtime(file_path)
        return load_and_cache_image(file_path, mtime)
    except Exception:
        return None


def create_gradient_background(width: int, height: int, config: GradientConfig) -> Image.Image:
    """Creates a high-fidelity dithered gradient background with optional radial spotlight."""
    c_start = np.array(hex_to_rgb(config.color_start), dtype=np.float32)
    c_end = np.array(hex_to_rgb(config.color_end), dtype=np.float32)

    # Base grid
    y_coords, x_coords = np.mgrid[0:height, 0:width].astype(np.float32)
    norm_x = x_coords / max(1, width - 1)
    norm_y = y_coords / max(1, height - 1)

    # Linear gradient direction
    if config.direction == "horizontal":
        t = norm_x
    elif config.direction == "diagonal":
        t = (norm_x + norm_y) / 2.0
    else:  # vertical
        t = norm_y

    intensity = max(0.0, min(1.0, config.intensity))
    t = t * intensity + (1.0 - intensity) * 0.5
    t = np.clip(t, 0.0, 1.0)[:, :, None]

    # Interpolate colors
    bg_arr = c_start * (1.0 - t) + c_end * t

    # Radial spotlight
    if config.spotlight_enabled and config.spotlight_strength > 0:
        cx = config.spotlight_x * width
        cy = config.spotlight_y * height
        radius = max(10.0, config.spotlight_radius * max(width, height))
        
        # Distance map normalized
        dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2) / radius
        # Smooth cosine/gaussian decay
        spot_factor = np.clip(1.0 - dist, 0.0, 1.0)
        spot_factor = (np.sin((spot_factor - 0.5) * np.pi) + 1.0) / 2.0  # smoothstep
        spot_factor = spot_factor[:, :, None] * config.spotlight_strength

        # Add subtle soft light / spotlight (boost brightness by spotlight_strength * 255)
        bg_arr = bg_arr + (255.0 - bg_arr) * spot_factor

    # Add very subtle triangular dither to prevent 8-bit banding in dark gradients
    noise = (np.random.rand(height, width, 1).astype(np.float32) - 0.5) * 1.5
    bg_arr = np.clip(bg_arr + noise, 0.0, 255.0).astype(np.uint8)

    return Image.fromarray(bg_arr, mode="RGB").convert("RGBA")


def create_rounded_mask(width: int, height: int, radius: int) -> Image.Image:
    """Creates a high quality antialiased rounded rectangle mask using 2x supersampling."""
    if radius <= 0:
        return Image.new("L", (width, height), 255)
    
    scale = 2
    sw, sh = width * scale, height * scale
    sr = min(radius * scale, min(sw, sh) // 2)

    mask = Image.new("L", (sw, sh), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sr, fill=255)
    
    return mask.resize((width, height), resample=Image.Resampling.LANCZOS)


def create_shadow_image(width: int, height: int, frame: FrameConfig) -> Tuple[Image.Image, int, int]:
    """
    Renders an elegant soft drop shadow image.
    Returns (shadow_image, offset_left, offset_top) relative to target layer (x, y).
    """
    if not frame.shadow_enabled or frame.shadow_opacity <= 0 or frame.shadow_blur <= 0:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), 0, 0

    blur = int(frame.shadow_blur)
    pad = blur * 3
    sw = width + pad * 2
    sh = height + pad * 2

    # Draw solid rounded rectangle in temporary image
    shadow_base = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow_base)

    s_rgb = hex_to_rgb(frame.shadow_color)
    alpha = int(max(0.0, min(1.0, frame.shadow_opacity)) * 255)
    fill_color = (*s_rgb, alpha)

    r = min(frame.corner_radius, min(width, height) // 2)
    draw.rounded_rectangle(
        [pad, pad, pad + width - 1, pad + height - 1],
        radius=r,
        fill=fill_color
    )

    # Apply Gaussian blur
    shadow_blurred = shadow_base.filter(ImageFilter.GaussianBlur(radius=blur))
    
    offset_x = frame.shadow_offset_x - pad
    offset_y = frame.shadow_offset_y - pad
    return shadow_blurred, offset_x, offset_y


def render_image_layer(layer: ImageLayer, canvas_width: int, canvas_height: int, render_scale: float = 1.0) -> Optional[Tuple[Image.Image, int, int]]:
    """
    Renders an ImageLayer including device frame (corner radius, border, shadow).
    Returns (rendered_rgba_layer, top_left_x, top_left_y) or None if no image.
    """
    src_img = get_cached_image(layer.file_path)
    if src_img is None:
        return None

    full_w, full_h = get_image_layer_render_dimensions(layer, src_img.size, canvas_width)
    target_w = max(1, int(full_w * render_scale))
    target_h = max(1, int(full_h * render_scale))
    src_img = src_img.crop(get_image_layer_crop_box(layer, src_img.size))
    scale = max(0.05, layer.scale)

    # Resize source image with high-quality LANCZOS
    resized = src_img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

    effects = layer.effects.from_dict(layer.effects.to_dict())
    resized = apply_bottom_fade(resized, effects)
    effect_shadow = create_alpha_shadow(resized, effects, scale * render_scale)

    frame = layer.frame
    if frame.enabled:
        # Apply corner radius
        r = min(int(frame.corner_radius * scale * render_scale), min(target_w, target_h) // 2)
        if r > 0:
            mask = create_rounded_mask(target_w, target_h, r)
            if effects.fade_enabled or effects.shadow_enabled:
                resized.putalpha(ImageChops.multiply(resized.getchannel("A"), mask))
            else:
                resized.putalpha(ImageOps.invert(ImageOps.invert(mask)))

        # Draw border if specified
        if frame.border_width > 0:
            bw = max(1, int(frame.border_width * scale * render_scale))
            b_rgb = hex_to_rgb(frame.border_color)
            border_draw = ImageDraw.Draw(resized)
            border_draw.rounded_rectangle(
                [bw // 2, bw // 2, target_w - 1 - bw // 2, target_h - 1 - bw // 2],
                radius=max(0, r - bw // 2),
                outline=b_rgb,
                width=bw
            )

    # Symmetric padding keeps the source center fixed when the whole group rotates.
    pad_x = pad_y = 0
    if effect_shadow is not None:
        shadow, sx, sy = effect_shadow
        pad_x = max(0, -sx, sx + shadow.width - target_w)
        pad_y = max(0, -sy, sy + shadow.height - target_h)
        group = Image.new("RGBA", (target_w + 2 * pad_x, target_h + 2 * pad_y))
        group.alpha_composite(shadow, (pad_x + sx, pad_y + sy))
        group.alpha_composite(resized, (pad_x, pad_y))
        resized = group

    # Opacity
    if layer.opacity < 1.0:
        alpha = resized.split()[3]
        alpha = alpha.point(lambda p: int(p * layer.opacity))
        resized.putalpha(alpha)

    # Top-left position on canvas (layer.x, layer.y is center of image)
    top_left_x = int(int(layer.x - full_w / 2) * render_scale)
    top_left_y = int(int(layer.y - full_h / 2) * render_scale)

    top_left_x -= pad_x
    top_left_y -= pad_y

    # Rotation
    if abs(layer.rotation) > 0.01:
        resized = resized.rotate(-layer.rotation, resample=Image.Resampling.BICUBIC, expand=True)
        # Re-center rotated image
        top_left_x = int(layer.x * render_scale - resized.width / 2)
        top_left_y = int(layer.y * render_scale - resized.height / 2)

    return resized, top_left_x, top_left_y


def wrap_text_lines(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wraps text lines according to max_width (supports Japanese character wrapping)."""
    if not text:
        return []
    
    raw_lines = text.split("\n")
    if max_width <= 0:
        return raw_lines

    wrapped_lines = []
    for line in raw_lines:
        if not line:
            wrapped_lines.append("")
            continue

        current_line = ""
        for char in line:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            if w > max_width and current_line:
                wrapped_lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        if current_line:
            wrapped_lines.append(current_line)

    return wrapped_lines


def get_text_layer_metrics(layer: TextLayer, canvas_width: int) -> Tuple[int, int, List[str], any]:
    """Calculates text layer bounding dimensions and wrapped lines."""
    font = load_font(layer.font_family, layer.font_size, layer.font_weight)
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    max_w = layer.max_width if layer.max_width > 0 else int(canvas_width * 0.9)
    lines = wrap_text_lines(layer.text, font, max_w, draw)

    if not lines:
        return 0, 0, [], font

    line_height = int(layer.font_size * layer.line_spacing)
    total_w = 0
    
    for l in lines:
        bbox = draw.textbbox((0, 0), l, font=font)
        lw = bbox[2] - bbox[0]
        total_w = max(total_w, lw)

    total_h = max(line_height, len(lines) * line_height)
    return total_w, total_h, lines, font


def render_text_layer(layer: TextLayer, canvas_width: int, canvas_height: int, render_scale: float = 1.0) -> Optional[Tuple[Image.Image, int, int]]:
    """
    Renders a TextLayer to an RGBA image.
    Returns (text_image, top_left_x, top_left_y).
    """
    if not layer.text.strip():
        return None

    total_w, total_h, lines, font = get_text_layer_metrics(layer, canvas_width)
    if not lines:
        return None

    pad = 20
    text_img = Image.new("RGBA", (max(1, int((total_w + pad * 2) * render_scale)),
                                  max(1, int((total_h + pad * 2) * render_scale))), (0, 0, 0, 0))
    render_font = font if render_scale == 1 else load_font(
        layer.font_family, max(1, round(layer.font_size * render_scale)), layer.font_weight)
    draw = ImageDraw.Draw(text_img)

    color_rgb = hex_to_rgb(layer.color)
    line_height = int(layer.font_size * layer.line_spacing)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        
        if layer.align == "center":
            lx = pad + (total_w - lw) // 2
        elif layer.align == "right":
            lx = pad + (total_w - lw)
        else:
            lx = pad

        ly = pad + i * line_height
        draw.text((lx * render_scale, ly * render_scale), line, font=render_font, fill=(*color_rgb, 255))

    # Top-left calculation based on layer.x, layer.y (center X, top Y)
    top_left_x = int(layer.x - (total_w + pad * 2) / 2)
    top_left_y = int(layer.y - pad)

    return text_img, int(top_left_x * render_scale), int(top_left_y * render_scale)


def draw_preview_guides(canvas_img: Image.Image, canvas_width: int, canvas_height: int) -> Image.Image:
    """Draws overlay guides for center, 5%/10% safe margins, and headline area."""
    overlay = Image.new("RGBA", canvas_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 10% Safe Area
    m10_x = int(canvas_width * 0.10)
    m10_y = int(canvas_height * 0.10)
    draw.rectangle(
        [m10_x, m10_y, canvas_width - m10_x, canvas_height - m10_y],
        outline=(80, 200, 255, 120),
        width=2
    )
    draw.text((m10_x + 10, m10_y + 10), "10% Safe Margin", fill=(80, 200, 255, 180))

    # 5% Margin
    m5_x = int(canvas_width * 0.05)
    m5_y = int(canvas_height * 0.05)
    draw.rectangle(
        [m5_x, m5_y, canvas_width - m5_x, canvas_height - m5_y],
        outline=(255, 160, 60, 90),
        width=2
    )

    # Headline Area (Top 22%)
    h_bottom = int(canvas_height * 0.22)
    draw.rectangle(
        [m5_x, m5_y, canvas_width - m5_x, h_bottom],
        outline=(160, 100, 255, 140),
        width=2
    )
    draw.text((m5_x + 10, h_bottom - 40), "Headline Area (Top 22%)", fill=(160, 100, 255, 180))

    # Center lines (Crosshair)
    cx = canvas_width // 2
    cy = canvas_height // 2
    draw.line([(cx, 0), (cx, canvas_height)], fill=(255, 255, 255, 70), width=1)
    draw.line([(0, cy), (canvas_width, cy)], fill=(255, 255, 255, 70), width=1)

    return Image.alpha_composite(canvas_img, overlay)


def render_page(
    project: Project,
    page: Page,
    show_guides: bool = False,
    scale_factor: float = 1.0
) -> Image.Image:
    """
    Renders the entire page at full resolution (or scaled for fast preview).
    Returns an RGBA PIL Image.
    """
    cw = project.canvas_width
    ch = project.canvas_height

    geometry = get_workspace_geometry(project, page)
    # Keep Single's existing render path. Panorama allocates only preview-sized
    # buffers; layer layout still uses logical per-screen pixels.
    render_scale = min(1.0, scale_factor) if page.panorama.enabled and scale_factor > 0 else 1.0
    rw, rh = max(1, int(geometry.width * render_scale)), max(1, int(geometry.height * render_scale))
    canvas = create_gradient_background(rw, rh, page.background)

    # 2. Render Layers in order
    for layer in page.layers:
        if not layer.visible:
            continue

        if isinstance(layer, ImageLayer):
            # Render shadow if enabled
            if layer.frame.enabled and layer.frame.shadow_enabled:
                src_img = get_cached_image(layer.file_path)
                if src_img:
                    tw, th = get_image_layer_render_dimensions(layer, src_img.size, cw)
                    if tw > 0 and th > 0:
                        frame = layer.frame
                        if render_scale != 1:
                            frame = replace(frame, **{name: getattr(frame, name) * render_scale for name in
                                ("corner_radius", "shadow_blur", "shadow_offset_x", "shadow_offset_y")})
                        shadow_img, sx_off, sy_off = create_shadow_image(
                            max(1, int(tw * render_scale)), max(1, int(th * render_scale)), frame)
                        layer_tl_x = int(int(layer.x - tw / 2) * render_scale)
                        layer_tl_y = int(int(layer.y - th / 2) * render_scale)
                        shadow_x = int(layer_tl_x + sx_off)
                        shadow_y = int(layer_tl_y + sy_off)
                        canvas.alpha_composite(shadow_img, (shadow_x, shadow_y))

            # Render image layer
            res = render_image_layer(layer, cw, ch, render_scale=render_scale)
            if res is not None:
                img_layer, lx, ly = res
                canvas.alpha_composite(img_layer, (lx, ly))

        elif isinstance(layer, TextLayer):
            res = render_text_layer(layer, cw, ch, render_scale=render_scale)
            if res is not None:
                txt_layer, lx, ly = res
                canvas.alpha_composite(txt_layer, (lx, ly))

    # 3. Overlay guides if requested (preview only)
    if show_guides:
        if page.panorama.enabled:
            draw = ImageDraw.Draw(canvas)
            for boundary in geometry.boundaries:
                x = round(boundary * render_scale)
                draw.line((x, 0, x, rh), fill=(100, 200, 255, 220), width=2)
            for number, (left, _, right, _) in enumerate(geometry.screen_rectangles, 1):
                draw.text((round((left + right) / 2 * render_scale), 8), str(number),
                          anchor="mt", fill="white")
        else:
            canvas = draw_preview_guides(canvas, cw, ch)

    # 4. Optional scaling
    if scale_factor != render_scale and scale_factor > 0:
        pw = max(1, int(geometry.width * scale_factor))
        ph = max(1, int(geometry.height * scale_factor))
        return canvas.resize((pw, ph), resample=Image.Resampling.LANCZOS)

    return canvas
