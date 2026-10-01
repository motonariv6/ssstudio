"""Non-destructive image effects, shared by preview and export (no UI dependencies)."""
import math

import numpy as np
from PIL import Image, ImageChops, ImageColor, ImageFilter

from core.models import ImageEffectsConfig


def build_bottom_fade_mask(size, start=.70, end=1.0):
    config = ImageEffectsConfig(fade_start=start, fade_end=end)
    config.normalize()
    width, height = size
    y = np.linspace(0, 1, height) if height > 1 else np.ones(1)
    alpha = np.rint(np.clip((config.fade_end - y) /
                           (config.fade_end - config.fade_start), 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(alpha[:, None]).resize((width, height))


def apply_bottom_fade(image, config):
    if not config.fade_enabled:
        return image
    result = image.copy()
    result.putalpha(ImageChops.multiply(image.getchannel("A"),
                    build_bottom_fade_mask(image.size, config.fade_start, config.fade_end)))
    return result


def create_alpha_shadow(image, config, render_scale=1.0):
    """Return shadow and its origin relative to the source, or None when disabled."""
    config = ImageEffectsConfig.from_dict(config.to_dict())
    if not config.shadow_enabled or config.shadow_opacity <= 0:
        return None
    blur = config.shadow_blur * render_scale
    pad = math.ceil(blur * 3)
    alpha = Image.new("L", (image.width + 2 * pad, image.height + 2 * pad))
    alpha.paste(image.getchannel("A"), (pad, pad))
    if blur > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(blur))
    alpha = alpha.point(lambda value: int(value * config.shadow_opacity))
    try:
        color = ImageColor.getrgb(config.shadow_color)[:3]
    except (ValueError, TypeError, AttributeError):
        color = (0, 0, 0)
    shadow = Image.new("RGBA", alpha.size, (*color, 0))
    shadow.putalpha(alpha)
    return shadow, round(config.shadow_offset_x * render_scale) - pad, round(config.shadow_offset_y * render_scale) - pad
