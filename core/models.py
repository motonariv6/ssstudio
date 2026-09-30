from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union, Dict, Any

from core.panorama import PanoramaConfig
from core.store_profiles import CANVAS_PRESETS, DEFAULT_STORE_PRESETS, get_orientation

GRADIENT_PRESETS: Dict[str, Dict[str, Any]] = {
    "luxury_black": {
        "name": "Luxury Black",
        "color_start": "#070709",
        "color_end": "#15161A",
        "direction": "vertical",
        "intensity": 0.8,
        "spotlight_enabled": True,
        "spotlight_x": 0.5,
        "spotlight_y": 0.38,
        "spotlight_strength": 0.18,
        "spotlight_radius": 0.65
    },
    "pure_black": {
        "name": "Pure Black",
        "color_start": "#000000",
        "color_end": "#000000",
        "direction": "vertical",
        "intensity": 0.0,
        "spotlight_enabled": False,
        "spotlight_x": 0.5,
        "spotlight_y": 0.5,
        "spotlight_strength": 0.0,
        "spotlight_radius": 0.5
    },
    "charcoal_black": {
        "name": "Charcoal Black",
        "color_start": "#16171A",
        "color_end": "#222428",
        "direction": "diagonal",
        "intensity": 0.7,
        "spotlight_enabled": True,
        "spotlight_x": 0.5,
        "spotlight_y": 0.35,
        "spotlight_strength": 0.14,
        "spotlight_radius": 0.6
    },
    "soft_spotlight_black": {
        "name": "Soft Spotlight Black",
        "color_start": "#0A0A0C",
        "color_end": "#101014",
        "direction": "vertical",
        "intensity": 0.5,
        "spotlight_enabled": True,
        "spotlight_x": 0.5,
        "spotlight_y": 0.45,
        "spotlight_strength": 0.28,
        "spotlight_radius": 0.75
    },
    "pure_white": {
        "name": "Pure White",
        "color_start": "#FFFFFF",
        "color_end": "#FFFFFF",
        "direction": "vertical",
        "intensity": 0.0,
        "spotlight_enabled": False,
        "spotlight_x": 0.5,
        "spotlight_y": 0.5,
        "spotlight_strength": 0.0,
        "spotlight_radius": 0.5
    },
    "soft_gray": {
        "name": "Soft Studio Gray",
        "color_start": "#F5F5F7",
        "color_end": "#E5E5EA",
        "direction": "vertical",
        "intensity": 0.6,
        "spotlight_enabled": True,
        "spotlight_x": 0.5,
        "spotlight_y": 0.4,
        "spotlight_strength": 0.15,
        "spotlight_radius": 0.7
    }
}

TEXT_STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "hero": {
        "font_size": 108,
        "font_weight": "bold",
        "color": "#FFFFFF",
        "align": "center",
        "line_spacing": 1.25,
        "letter_spacing": 1
    },
    "headline": {
        "font_size": 84,
        "font_weight": "bold",
        "color": "#FFFFFF",
        "align": "center",
        "line_spacing": 1.25,
        "letter_spacing": 0
    },
    "subheadline": {
        "font_size": 52,
        "font_weight": "regular",
        "color": "#D8D8D8",
        "align": "center",
        "line_spacing": 1.35,
        "letter_spacing": 0
    },
    "caption": {
        "font_size": 38,
        "font_weight": "regular",
        "color": "#A0A0A0",
        "align": "center",
        "line_spacing": 1.35,
        "letter_spacing": 0
    }
}

THEME_LEMEMO_LUXURY = {
    "name": "Lememo Luxury",
    "background_preset": "luxury_black",
    "primary_text": "#FFFFFF",
    "secondary_text": "#D8D8D8",
    "accent": "#B34254",
    "frame_corner_radius": 52,
    "frame_border_width": 6,
    "frame_border_color": "#28282E",
    "shadow_opacity": 0.5,
    "shadow_blur": 48,
    "shadow_offset_y": 32
}


@dataclass
class FrameConfig:
    enabled: bool = True
    corner_radius: int = 52
    border_width: int = 6
    border_color: str = "#28282E"
    shadow_enabled: bool = True
    shadow_opacity: float = 0.5
    shadow_blur: int = 48
    shadow_offset_x: int = 0
    shadow_offset_y: int = 32
    shadow_color: str = "#000000"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FrameConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GradientConfig:
    preset: str = "luxury_black"
    color_start: str = "#070709"
    color_end: str = "#15161A"
    direction: str = "vertical"  # 'vertical', 'horizontal', 'diagonal'
    intensity: float = 0.8
    spotlight_enabled: bool = True
    spotlight_x: float = 0.5
    spotlight_y: float = 0.38
    spotlight_strength: float = 0.18
    spotlight_radius: float = 0.65

    def apply_preset(self, preset_key: str):
        if preset_key in GRADIENT_PRESETS:
            cfg = GRADIENT_PRESETS[preset_key]
            self.preset = preset_key
            self.color_start = cfg["color_start"]
            self.color_end = cfg["color_end"]
            self.direction = cfg["direction"]
            self.intensity = cfg["intensity"]
            self.spotlight_enabled = cfg["spotlight_enabled"]
            self.spotlight_x = cfg["spotlight_x"]
            self.spotlight_y = cfg["spotlight_y"]
            self.spotlight_strength = cfg["spotlight_strength"]
            self.spotlight_radius = cfg["spotlight_radius"]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GradientConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ImageLayer:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Screenshot"
    file_path: str = ""
    x: float = 0.0  # Center X on canvas (pixels)
    y: float = 0.0  # Center Y on canvas (pixels)
    scale: float = 1.0
    rotation: float = 0.0  # degrees
    opacity: float = 1.0
    frame: FrameConfig = field(default_factory=FrameConfig)
    original_width: int = 0
    original_height: int = 0
    visible: bool = True
    locked: bool = False
    layer_type: str = "image"

    crop_left: float = 0.0
    crop_top: float = 0.0
    crop_right: float = 1.0
    crop_bottom: float = 1.0

    def reset_crop(self):
        self.crop_left = self.crop_top = 0.0
        self.crop_right = self.crop_bottom = 1.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["frame"] = self.frame.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ImageLayer:
        data_copy = dict(data)
        if "frame" in data_copy and isinstance(data_copy["frame"], dict):
            data_copy["frame"] = FrameConfig.from_dict(data_copy["frame"])
        return cls(**{k: v for k, v in data_copy.items() if k in cls.__dataclass_fields__})


@dataclass
class TextLayer:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Text"
    text: str = "キャッチコピーを入力"
    font_family: str = "Hiragino Sans"
    font_size: int = 84
    font_weight: str = "bold"  # 'regular' or 'bold'
    color: str = "#FFFFFF"
    align: str = "center"  # 'left', 'center', 'right'
    x: float = 0.0  # Top-left or Center X on canvas (pixels)
    y: float = 0.0  # Top-left or Center Y on canvas (pixels)
    max_width: int = 1000  # 0 for auto
    line_spacing: float = 1.25
    letter_spacing: int = 0
    style_preset: str = "headline"  # 'hero', 'headline', 'subheadline', 'caption', 'custom'
    visible: bool = True
    locked: bool = False
    layer_type: str = "text"

    def apply_style_preset(self, preset_key: str):
        if preset_key in TEXT_STYLE_PRESETS:
            cfg = TEXT_STYLE_PRESETS[preset_key]
            self.style_preset = preset_key
            self.font_size = cfg["font_size"]
            self.font_weight = cfg["font_weight"]
            self.color = cfg["color"]
            self.align = cfg["align"]
            self.line_spacing = cfg["line_spacing"]
            self.letter_spacing = cfg["letter_spacing"]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TextLayer:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


LayerType = Union[ImageLayer, TextLayer]


@dataclass
class Page:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Page 1"
    background: GradientConfig = field(default_factory=GradientConfig)
    layers: List[LayerType] = field(default_factory=list)
    panorama: PanoramaConfig = field(default_factory=PanoramaConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "background": self.background.to_dict(),
            "panorama": self.panorama.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Page:
        bg = GradientConfig.from_dict(data.get("background", {}))
        layers: List[LayerType] = []
        for l_data in data.get("layers", []):
            if l_data.get("layer_type") == "image":
                layers.append(ImageLayer.from_dict(l_data))
            elif l_data.get("layer_type") == "text":
                layers.append(TextLayer.from_dict(l_data))
        return cls(id=data.get("id", str(uuid.uuid4())), name=data.get("name", "Page"), background=bg, layers=layers,
                   panorama=PanoramaConfig.from_dict(data.get("panorama", {})))


@dataclass
class Project:
    name: str = "AppStoreScreenshots"
    preset_name: str = "iPhone 6.9-inch"
    canvas_width: int = 1290
    canvas_height: int = 2796
    pages: List[Page] = field(default_factory=lambda: [Page(name="01_people")])
    active_page_index: int = 0

    store: Optional[str] = None
    device_type: Optional[str] = None

    def __post_init__(self):
        profile = CANVAS_PRESETS.get(self.preset_name)
        if profile and self.preset_name != "Custom":
            # A named profile owns its store/device identity. Keep saved dimensions.
            self.store = profile["store"]
            self.device_type = profile["device_type"]
        else:
            self.store = self.store or "apple_app_store"
            self.device_type = self.device_type or "custom"

    @property
    def orientation(self) -> str:
        # Derive from actual dimensions, including legacy/custom canvas sizes.
        return get_orientation(self.canvas_width, self.canvas_height)

    def set_store(self, store: str):
        if store not in DEFAULT_STORE_PRESETS:
            raise ValueError(f"Unknown store: {store}")
        if self.preset_name == "Custom":
            self.store = store
        else:
            self.set_preset(DEFAULT_STORE_PRESETS[store])

    def set_custom_size(self, width: int, height: int):
        if width <= 0 or height <= 0:
            raise ValueError("Canvas dimensions must be positive")
        self.preset_name = "Custom"
        self.canvas_width, self.canvas_height = width, height
        # Preserve store/device so editing Google Play dimensions keeps validation.

    @property
    def active_page(self) -> Page:
        if 0 <= self.active_page_index < len(self.pages):
            return self.pages[self.active_page_index]
        if self.pages:
            self.active_page_index = 0
            return self.pages[0]
        new_p = Page(name="Page 1")
        self.pages.append(new_p)
        self.active_page_index = 0
        return new_p

    def set_preset(self, preset_name: str):
        if preset_name in CANVAS_PRESETS:
            self.preset_name = preset_name
            self.canvas_width = CANVAS_PRESETS[preset_name]["width"]
            self.canvas_height = CANVAS_PRESETS[preset_name]["height"]
            if preset_name != "Custom":
                self.store = CANVAS_PRESETS[preset_name]["store"]
                self.device_type = CANVAS_PRESETS[preset_name]["device_type"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "preset_name": self.preset_name,
            "store": self.store,
            "device_type": self.device_type,
            "orientation": self.orientation,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "active_page_index": self.active_page_index,
            "pages": [p.to_dict() for p in self.pages]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Project:
        pages = [Page.from_dict(p) for p in data.get("pages", [])]
        if not pages:
            pages = [Page(name="01_people")]
        return cls(
            name=data.get("name", "AppStoreScreenshots"),
            preset_name=data.get("preset_name", "iPhone 6.9-inch"),
            canvas_width=data.get("canvas_width", 1290),
            canvas_height=data.get("canvas_height", 2796),
            pages=pages,
            active_page_index=data.get("active_page_index", 0),
            store=data.get("store"),
            device_type=data.get("device_type")
        )
