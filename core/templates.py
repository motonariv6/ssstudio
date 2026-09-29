from __future__ import annotations
from typing import List
from core.models import (
    Page, ImageLayer, TextLayer, FrameConfig, GradientConfig,
    THEME_LEMEMO_LUXURY, GRADIENT_PRESETS
)


def apply_theme_to_page(page: Page, theme: dict = THEME_LEMEMO_LUXURY):
    """Applies a theme preset to a page."""
    bg_preset = theme.get("background_preset", "luxury_black")
    page.background.apply_preset(bg_preset)

    for layer in page.layers:
        if isinstance(layer, ImageLayer):
            layer.frame.corner_radius = theme.get("frame_corner_radius", 52)
            layer.frame.border_width = theme.get("frame_border_width", 6)
            layer.frame.border_color = theme.get("frame_border_color", "#28282E")
            layer.frame.shadow_opacity = theme.get("shadow_opacity", 0.5)
            layer.frame.shadow_blur = theme.get("shadow_blur", 48)
            layer.frame.shadow_offset_y = theme.get("shadow_offset_y", 32)
        elif isinstance(layer, TextLayer):
            if layer.style_preset in ["hero", "headline"]:
                layer.color = theme.get("primary_text", "#FFFFFF")
            elif layer.style_preset in ["subheadline", "caption"]:
                layer.color = theme.get("secondary_text", "#D8D8D8")


def create_template_headline_top(canvas_width: int, canvas_height: int, existing_image_path: str = "") -> Page:
    """Template A: Headline Top (Headline at top 20-25%, screenshot centered below)"""
    page = Page(name="Headline Top")
    page.background.apply_preset("luxury_black")

    # Headline
    headline = TextLayer(
        name="Main Headline",
        text="あの人のこと、もう忘れない。",
        font_size=88,
        font_weight="bold",
        color="#FFFFFF",
        align="center",
        x=canvas_width / 2,
        y=canvas_height * 0.08,
        max_width=int(canvas_width * 0.88),
        style_preset="headline"
    )

    # Subheadline
    subheadline = TextLayer(
        name="Subheadline",
        text="大切な会話や好みをスマートに記録",
        font_size=46,
        font_weight="regular",
        color="#D8D8D8",
        align="center",
        x=canvas_width / 2,
        y=canvas_height * 0.15,
        max_width=int(canvas_width * 0.85),
        style_preset="subheadline"
    )

    # Screenshot Layer
    screenshot = ImageLayer(
        name="Device Screenshot",
        file_path=existing_image_path,
        x=canvas_width / 2,
        y=canvas_height * 0.62,
        scale=0.92,
        frame=FrameConfig(
            enabled=True,
            corner_radius=54,
            border_width=6,
            border_color="#2A2A30",
            shadow_enabled=True,
            shadow_opacity=0.55,
            shadow_blur=50,
            shadow_offset_y=35
        )
    )

    page.layers = [screenshot, headline, subheadline]
    return page


def create_template_split(canvas_width: int, canvas_height: int, existing_image_path: str = "") -> Page:
    """Template B: Split (Text on top/left, device on bottom/right)"""
    page = Page(name="Split Layout")
    page.background.apply_preset("luxury_black")

    headline = TextLayer(
        name="Headline",
        text="記録して、思い出して、\n次につなげる。",
        font_size=80,
        font_weight="bold",
        color="#FFFFFF",
        align="center",
        x=canvas_width / 2,
        y=canvas_height * 0.09,
        max_width=int(canvas_width * 0.86),
        line_spacing=1.3,
        style_preset="headline"
    )

    screenshot = ImageLayer(
        name="Device Screenshot",
        file_path=existing_image_path,
        x=canvas_width / 2,
        y=canvas_height * 0.64,
        scale=0.95,
        frame=FrameConfig(
            enabled=True,
            corner_radius=54,
            border_width=6,
            border_color="#28282E",
            shadow_enabled=True,
            shadow_opacity=0.55,
            shadow_blur=48,
            shadow_offset_y=30
        )
    )

    page.layers = [screenshot, headline]
    return page


def create_template_center_device(canvas_width: int, canvas_height: int, existing_image_path: str = "") -> Page:
    """Template C: Center Device (Top headline, Large center device, Bottom caption)"""
    page = Page(name="Center Device")
    page.background.apply_preset("luxury_black")

    headline = TextLayer(
        name="Top Headline",
        text="次の予定も、ちゃんと見える。",
        font_size=82,
        font_weight="bold",
        color="#FFFFFF",
        align="center",
        x=canvas_width / 2,
        y=canvas_height * 0.08,
        max_width=int(canvas_width * 0.88),
        style_preset="headline"
    )

    screenshot = ImageLayer(
        name="Main Device",
        file_path=existing_image_path,
        x=canvas_width / 2,
        y=canvas_height * 0.52,
        scale=0.88,
        frame=FrameConfig(
            enabled=True,
            corner_radius=52,
            border_width=6,
            border_color="#2A2A32",
            shadow_enabled=True,
            shadow_opacity=0.55,
            shadow_blur=52,
            shadow_offset_y=36
        )
    )

    bottom_caption = TextLayer(
        name="Bottom Caption",
        text="タップ1回でカレンダーと連携",
        font_size=44,
        font_weight="regular",
        color="#B34254",  # Le'memo accent
        align="center",
        x=canvas_width / 2,
        y=canvas_height * 0.90,
        max_width=int(canvas_width * 0.85),
        style_preset="caption"
    )

    page.layers = [screenshot, headline, bottom_caption]
    return page


def create_template_double_device(canvas_width: int, canvas_height: int, img1_path: str = "", img2_path: str = "") -> Page:
    """Template D: Double Device (Two overlapping screenshots)"""
    page = Page(name="Double Device")
    page.background.apply_preset("luxury_black")

    headline = TextLayer(
        name="Headline",
        text="充実の機能、シンプルな操作。",
        font_size=82,
        font_weight="bold",
        color="#FFFFFF",
        align="center",
        x=canvas_width / 2,
        y=canvas_height * 0.08,
        max_width=int(canvas_width * 0.88),
        style_preset="headline"
    )

    # Back device (left/upper)
    dev1 = ImageLayer(
        name="Back Screenshot",
        file_path=img1_path,
        x=canvas_width * 0.36,
        y=canvas_height * 0.58,
        scale=0.76,
        rotation=-3.0,
        frame=FrameConfig(
            enabled=True,
            corner_radius=48,
            border_width=5,
            border_color="#222228",
            shadow_enabled=True,
            shadow_opacity=0.45,
            shadow_blur=44,
            shadow_offset_y=28
        )
    )

    # Front device (right/lower)
    dev2 = ImageLayer(
        name="Front Screenshot",
        file_path=img2_path,
        x=canvas_width * 0.64,
        y=canvas_height * 0.63,
        scale=0.78,
        rotation=3.0,
        frame=FrameConfig(
            enabled=True,
            corner_radius=48,
            border_width=6,
            border_color="#2D2D35",
            shadow_enabled=True,
            shadow_opacity=0.6,
            shadow_blur=54,
            shadow_offset_y=38
        )
    )

    page.layers = [dev1, dev2, headline]
    return page


def create_template_free_layout(canvas_width: int, canvas_height: int) -> Page:
    """Template E: Free Layout (Empty starter)"""
    page = Page(name="Free Layout")
    page.background.apply_preset("luxury_black")
    return page


TEMPLATE_FACTORIES = {
    "Headline Top": create_template_headline_top,
    "Split": create_template_split,
    "Center Device": create_template_center_device,
    "Double Device": create_template_double_device,
    "Free Layout": create_template_free_layout,
}
