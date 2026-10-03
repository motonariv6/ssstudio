"""Store-aware canvas profiles; legacy preset keys remain stable."""
from typing import Any, Dict

STORE_LABELS = {"apple_app_store": "Apple App Store", "google_play": "Google Play"}
DEFAULT_STORE_PRESETS = {
    "apple_app_store": "iPhone 6.9-inch",
    "google_play": "Google Play Phone Portrait",
}


def get_orientation(width: int, height: int) -> str:
    if width == height:
        return "square"
    return "portrait" if height > width else "landscape"


def _profile(name, store, device_type, width, height, description, asset_type="screenshot"):
    return {
        "name": name, "store": store, "device_type": device_type,
        "asset_type": asset_type,
        "orientation": get_orientation(width, height),
        "width": width, "height": height, "description": description,
        "desc": description,  # Compatibility with existing preset consumers.
    }


CANVAS_PRESETS: Dict[str, Dict[str, Any]] = {
    "iPhone 6.9-inch": _profile("iPhone 6.9-inch", "apple_app_store", "phone", 1290, 2796, "16 Pro Max / 15 Pro Max"),
    "iPhone 6.5-inch": _profile("iPhone 6.5-inch", "apple_app_store", "phone", 1242, 2688, "XS Max / 11 Pro Max"),
    "iPhone 6.3-inch": _profile("iPhone 6.3-inch", "apple_app_store", "phone", 1206, 2622, "16 Pro / 15 Pro"),
    "iPad 13-inch": _profile("iPad 13-inch", "apple_app_store", "tablet", 2064, 2752, "iPad Pro 13-inch (M4)"),
    "Google Play Phone Portrait": _profile("Google Play Phone Portrait", "google_play", "phone", 1080, 1920, "Google Play phone screenshot"),
    "Google Play Phone Landscape": _profile("Google Play Phone Landscape", "google_play", "phone", 1920, 1080, "Google Play phone screenshot"),
    "Google Play Tablet Portrait": _profile("Google Play Tablet Portrait", "google_play", "tablet", 1080, 1920, "Google Play tablet screenshot"),
    "Google Play Tablet Landscape": _profile("Google Play Tablet Landscape", "google_play", "tablet", 1920, 1080, "Google Play tablet screenshot"),
    "Google Play Feature Graphic": _profile("Google Play Feature Graphic", "google_play", "feature_graphic", 1024, 500, "Google Play feature graphic", asset_type="feature_graphic"),
    "Google Play — Feature Graphic": _profile("Google Play — Feature Graphic", "google_play", "feature_graphic", 1024, 500, "Google Play feature graphic", asset_type="feature_graphic"),
    "Custom": _profile("Custom", "custom", "custom", 1290, 2796, "Custom Dimensions"),
}


def get_store_preset_labels(store: str) -> Dict[str, str]:
    """Map short UI labels to stable JSON profile keys under a Store selector."""
    labels = {}
    for key, profile in CANVAS_PRESETS.items():
        if profile["store"] == store or key == "Custom":
            if "—" in key:
                continue
            label = key.removeprefix("Google Play ")
            labels[label] = key
    return labels
