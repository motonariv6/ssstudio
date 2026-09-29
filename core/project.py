from __future__ import annotations
import json
import os
from typing import Optional, Tuple
from core.models import Project


def save_project_to_json(project: Project, file_path: str) -> Tuple[bool, str]:
    """Saves a project object to a JSON file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        data = project.to_dict()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True, "Project saved successfully."
    except Exception as e:
        return False, f"Failed to save project: {e}"


def load_project_from_json(file_path: str) -> Tuple[Optional[Project], str]:
    """Loads a project from a JSON file."""
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        project = Project.from_dict(data)
        return project, "Project loaded successfully."
    except Exception as e:
        return None, f"Failed to parse project JSON: {e}"
