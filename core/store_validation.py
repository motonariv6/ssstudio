"""Store export requirements, independent of Tkinter and rendering."""
from typing import List
from core.models import Project
from core.store_profiles import CANVAS_PRESETS


def validate_store_canvas(store: str, width: int, height: int, asset_type: str = "screenshot") -> List[str]:
    """Return actionable export errors; Apple validation is not part of M2."""
    if store != "google_play":
        return []
    if any(not isinstance(value, int) or isinstance(value, bool) for value in (width, height)):
        return ["Google Play: width and height must be integer pixel dimensions."]

    if asset_type == "feature_graphic":
        if width != 1024 or height != 500:
            return ["Google Play Feature Graphic: dimensions must be exactly 1024 × 500 px."]
        return []

    errors = []
    if min(width, height) < 320:
        errors.append("Google Play: width and height must each be at least 320 px.")
    if max(width, height) > 3840:
        errors.append("Google Play: width and height must each be at most 3840 px.")
    if max(width, height) > 2 * min(width, height):
        errors.append("Google Play: the long side must be no more than 2 times the short side (2:1).")
    return errors


def validate_project_export(project: Project) -> List[str]:
    # Also guard named Google profiles if a caller directly changes legacy fields.
    profile = CANVAS_PRESETS.get(project.preset_name, {})
    if project.preset_name != "Custom" and profile:
        store = profile.get("store", project.store)
        asset_type = profile.get("asset_type", project.asset_type or "screenshot")
    else:
        store = project.store
        asset_type = project.asset_type or "screenshot"
    return validate_store_canvas(store, project.canvas_width, project.canvas_height, asset_type=asset_type)
