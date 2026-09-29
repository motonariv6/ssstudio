from __future__ import annotations
import os
import functools
from typing import Dict, List, Optional
from PIL import ImageFont

# Well-known macOS fonts with their regular and bold variants
SYSTEM_FONT_MAP: Dict[str, Dict[str, str]] = {
    "Hiragino Sans": {
        "regular": "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "bold": "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "heavy": "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
    },
    "Hiragino Maru Gothic": {
        "regular": "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
        "bold": "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
    },
    "Hiragino Mincho": {
        "regular": "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
        "bold": "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
    },
    "Helvetica Neue": {
        "regular": "/System/Library/Fonts/HelveticaNeue.ttc",
        "bold": "/System/Library/Fonts/HelveticaNeue.ttc",
    },
    "Helvetica": {
        "regular": "/System/Library/Fonts/Helvetica.ttc",
        "bold": "/System/Library/Fonts/Helvetica.ttc",
    },
    "Avenir Next": {
        "regular": "/System/Library/Fonts/Avenir Next.ttc",
        "bold": "/System/Library/Fonts/Avenir Next.ttc",
    },
    "Apple SD Gothic Neo": {
        "regular": "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "bold": "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    },
    "Arial": {
        "regular": "/System/Library/Fonts/Supplemental/Arial.ttf",
        "bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    },
}

DEFAULT_FONT_NAME = "Hiragino Sans"


def get_available_font_names() -> List[str]:
    """Returns a list of font family names available on this machine."""
    available = []
    for name, variants in SYSTEM_FONT_MAP.items():
        if any(os.path.exists(p) for p in variants.values()):
            available.append(name)
    if not available:
        available = ["Default"]
    return available


@functools.lru_cache(maxsize=128)
def load_font(font_family: str, size: int, weight: str = "regular") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads a font at specified size and weight, with automatic fallbacks."""
    size = max(8, int(size))
    variants = SYSTEM_FONT_MAP.get(font_family)
    if not variants:
        variants = SYSTEM_FONT_MAP.get(DEFAULT_FONT_NAME, {})

    target_path = variants.get(weight) or variants.get("bold" if weight == "bold" else "regular")
    
    if target_path and os.path.exists(target_path):
        try:
            return ImageFont.truetype(target_path, size=size)
        except Exception:
            pass

    # Try any existing font in the map
    for fam, f_variants in SYSTEM_FONT_MAP.items():
        for w, path in f_variants.items():
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    pass

    # Final fallback
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()
