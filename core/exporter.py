from __future__ import annotations
import os
import re
from typing import List, Tuple
from PIL import Image

from core.models import Project, Page
from core.renderer import render_page
from core.store_validation import validate_project_export
from core.panorama import get_workspace_geometry


def sanitize_filename(name: str) -> str:
    s = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    s = re.sub(r"\s+", "_", s)
    return s or "page"


def get_default_export_filename(page_index: int, page_name: str) -> str:
    return f"{page_index + 1:02d}_{sanitize_filename(page_name)}.png"


def get_page_output_paths(project: Project, page: Page, output_path: str) -> List[str]:
    """A panorama filename is a base: foo.png produces foo_01.png, etc."""
    geometry = get_workspace_geometry(project, page)
    if geometry.screen_count == 1:
        return [output_path]
    stem = os.path.splitext(output_path)[0]
    return [f"{stem}_{i + 1:02d}.png" for i in range(geometry.screen_count)]


def get_all_output_paths(project: Project, output_dir: str) -> List[str]:
    return [path for i, page in enumerate(project.pages)
            for path in get_page_output_paths(project, page, os.path.join(
                output_dir, get_default_export_filename(i, page.name)))]


def _export_page_outputs(project, page, output_path, overwrite=False):
    paths = get_page_output_paths(project, page, output_path)
    errors = validate_project_export(project)  # canvas dimensions are each slice's dimensions
    if page.panorama.enabled and not overwrite:
        existing = [os.path.basename(path) for path in paths if os.path.exists(path)]
        if existing:
            errors.append("Files already exist; export stopped: " + ", ".join(existing))
    if errors:
        return [(path, False, "\n".join(errors), (0, 0)) for path in paths]
    results = []
    try:
        geometry = get_workspace_geometry(project, page)
        image = render_page(project, page, show_guides=False, scale_factor=1.0)
        # Render exactly once, then cut adjacent integer boxes. No independent
        # per-screen rendering (including gradient/spotlight/dither).
        for path, box in zip(paths, geometry.slice_boxes):
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                piece = image.crop(box)
                rgb = Image.new("RGB", piece.size, (0, 0, 0))
                rgb.paste(piece, mask=piece.getchannel("A"))
                mode = "xb" if page.panorama.enabled and not overwrite else "wb"
                with open(path, mode) as output:
                    rgb.save(output, format="PNG", optimize=False)
                results.append((path, True, f"Saved successfully: {path}", piece.size))
            except Exception as exc:
                results.append((path, False, str(exc), (0, 0)))
    except Exception as exc:
        return [(path, False, str(exc), (0, 0)) for path in paths]
    return results


def export_single_page(project: Project, page: Page, output_path: str,
                       overwrite: bool = False) -> Tuple[bool, str, Tuple[int, int]]:
    """Export current page. Panorama uses output_path as a numbered PNG base.

    Single mode retains its original exact filename/overwrite behavior. Panorama
    requires explicit overwrite=True if any numbered destination already exists.
    Returned dimensions are those of one screenshot, never the full workspace.
    """
    results = _export_page_outputs(project, page, output_path, overwrite)
    success = all(ok for _, ok, _, _ in results)
    return success, "\n".join(message for _, _, message, _ in results), (
        (project.canvas_width, project.canvas_height) if success else (0, 0))


def export_all_pages(project: Project, output_dir: str,
                     overwrite: bool = False) -> List[Tuple[str, bool, str, Tuple[int, int]]]:
    """One result per PNG, in page/screen order. Preflight the whole panorama batch."""
    paths = get_all_output_paths(project, output_dir)
    errors = validate_project_export(project)
    if any(page.panorama.enabled for page in project.pages) and not overwrite:
        existing = [os.path.basename(path) for path in paths if os.path.exists(path)]
        if existing:
            errors.append("Files already exist; export stopped: " + ", ".join(existing))
    if errors:
        return [(os.path.basename(path), False, "\n".join(errors), (0, 0)) for path in paths]
    results = []
    for i, page in enumerate(project.pages):
        base = os.path.join(output_dir, get_default_export_filename(i, page.name))
        results.extend((os.path.basename(path), ok, message, dims)
                       for path, ok, message, dims in _export_page_outputs(project, page, base, overwrite))
    return results
