"""Store export requirements, independent of Tkinter and rendering."""
from typing import List
from core.models import Project
from core.store_profiles import CANVAS_PRESETS


def validate_store_canvas(store: str, width: int, height: int) -> List[str]:
    """Return actionable export errors; Apple validation is not part of M2."""
    if store != "google_play":
        return []
    if any(not isinstance(value, int) or isinstance(value, bool) for value in (width, height)):
        return ["Google Play: width and height must be integer pixel dimensions."]
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
    store = "google_play" if profile.get("store") == "google_play" else project.store
    return validate_store_canvas(store, project.canvas_width, project.canvas_height)
