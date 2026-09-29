from __future__ import annotations
import os
import re
from typing import List, Tuple, Optional
from PIL import Image

from core.models import Project, Page
from core.renderer import render_page


def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be a safe filename."""
    s = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    s = re.sub(r"\s+", "_", s)
    return s or "page"


def get_default_export_filename(page_index: int, page_name: str) -> str:
    """Generates standard numbered filenames e.g. '01_people.png'."""
    clean_name = sanitize_filename(page_name)
    return f"{page_index + 1:02d}_{clean_name}.png"


def export_single_page(
    project: Project,
    page: Page,
    output_path: str
) -> Tuple[bool, str, Tuple[int, int]]:
    """
    Renders and exports a single page as RGB PNG at canvas resolution.
    Returns (success, message, (width, height)).
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img = render_page(project, page, show_guides=False, scale_factor=1.0)
        
        # Convert RGBA to high-quality RGB for App Store
        rgb_img = Image.new("RGB", img.size, (0, 0, 0))
        rgb_img.paste(img, mask=img.split()[3])

        rgb_img.save(output_path, format="PNG", optimize=False)
        return True, f"Saved successfully: {output_path}", img.size
    except Exception as e:
        return False, str(e), (0, 0)


def export_all_pages(
    project: Project,
    output_dir: str
) -> List[Tuple[str, bool, str, Tuple[int, int]]]:
    """
    Exports all pages in the project as numbered PNGs.
    Returns list of (filename, success, message, (width, height)).
    """
    results = []
    os.makedirs(output_dir, exist_ok=True)

    for i, page in enumerate(project.pages):
        filename = get_default_export_filename(i, page.name)
        out_path = os.path.join(output_dir, filename)
        success, msg, dims = export_single_page(project, page, out_path)
        results.append((filename, success, msg, dims))

    return results
