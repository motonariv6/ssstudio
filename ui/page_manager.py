from __future__ import annotations
import copy
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Callable, Optional
import uuid

from core.models import Project, Page, ImageLayer, TextLayer
from ui.theme import (
    BG_DARK, BG_SECONDARY, BG_TERTIARY, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_COLOR, FONT_BOLD, FONT_SMALL, FONT_SYSTEM,
    BTN_BG_DEFAULT, BTN_BG_HOVER, BTN_FG, BTN_ACCENT_BG, BTN_ACCENT_HOVER,
    BTN_DANGER_BG, BTN_DANGER_HOVER
)
from ui.widgets import DarkButton


class PageManagerBar(tk.Frame):
    """Horizontal page thumbnail/tab management bar."""

    def __init__(
        self,
        parent,
        get_project: Callable[[], Project],
        on_page_changed: Callable[[], None],
        **kwargs
    ):
        super().__init__(parent, bg=BG_SECONDARY, height=44, **kwargs)
        self.get_project = get_project
        self.on_page_changed = on_page_changed

        self.pack_propagate(False)

        # Left action buttons
        self.btn_frame = tk.Frame(self, bg=BG_SECONDARY)
        self.btn_frame.pack(side=tk.LEFT, padx=8, pady=4)

        self.btn_add = DarkButton(
            self.btn_frame,
            text="+ Add Page",
            bg=BTN_BG_DEFAULT,
            fg=BTN_FG,
            font=FONT_SMALL,
            padx=8,
            pady=4,
            command=self.add_new_page
        )
        self.btn_add.pack(side=tk.LEFT, padx=2)

        self.btn_dup = DarkButton(
            self.btn_frame,
            text="⧉ Duplicate Page",
            bg=BTN_BG_DEFAULT,
            fg=BTN_FG,
            font=FONT_SMALL,
            padx=8,
            pady=4,
            command=self.duplicate_current_page
        )
        self.btn_dup.pack(side=tk.LEFT, padx=2)

        # Scrollable pages container
        self.pages_scroll_frame = tk.Frame(self, bg=BG_SECONDARY)
        self.pages_scroll_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.page_buttons_container = tk.Frame(self.pages_scroll_frame, bg=BG_SECONDARY)
        self.page_buttons_container.pack(side=tk.LEFT, fill=tk.BOTH)

        # Right action buttons
        self.right_frame = tk.Frame(self, bg=BG_SECONDARY)
        self.right_frame.pack(side=tk.RIGHT, padx=8, pady=4)

        self.btn_rename = DarkButton(
            self.right_frame,
            text="✏ Rename",
            bg=BTN_BG_DEFAULT,
            fg=BTN_FG,
            font=FONT_SMALL,
            padx=8,
            pady=4,
            command=self.rename_current_page
        )
        self.btn_rename.pack(side=tk.LEFT, padx=2)

        self.btn_del = DarkButton(
            self.right_frame,
            text="✕ Delete",
            bg=BTN_DANGER_BG,
            hover_bg=BTN_DANGER_HOVER,
            fg="#FFFFFF",
            font=FONT_SMALL,
            padx=8,
            pady=4,
            command=self.delete_current_page
        )
        self.btn_del.pack(side=tk.LEFT, padx=2)

        self.refresh()

    def refresh(self):
        """Re-draws all page tab buttons."""
        for widget in self.page_buttons_container.winfo_children():
            widget.destroy()

        project = self.get_project()
        if not project:
            return

        for i, page in enumerate(project.pages):
            is_active = (i == project.active_page_index)
            bg = BTN_ACCENT_BG if is_active else BTN_BG_DEFAULT
            hover_bg = BTN_ACCENT_HOVER if is_active else BTN_BG_HOVER
            fg = "#FFFFFF" if is_active else "#D0D0D5"
            font = FONT_BOLD if is_active else FONT_SMALL

            btn = DarkButton(
                self.page_buttons_container,
                text=f"{i+1}. {page.name}",
                bg=bg,
                hover_bg=hover_bg,
                fg=fg,
                font=font,
                padx=10,
                pady=4,
                command=lambda idx=i: self.select_page(idx)
            )
            btn.pack(side=tk.LEFT, padx=2)

    def select_page(self, index: int):
        project = self.get_project()
        if 0 <= index < len(project.pages):
            project.active_page_index = index
            self.refresh()
            self.on_page_changed()

    def add_new_page(self):
        project = self.get_project()
        new_idx = len(project.pages) + 1
        page = Page(name=f"Page {new_idx}")
        # Copy background from active page for convenience
        page.background = copy.deepcopy(project.active_page.background)
        project.pages.append(page)
        project.active_page_index = len(project.pages) - 1
        self.refresh()
        self.on_page_changed()

    def duplicate_current_page(self):
        project = self.get_project()
        curr = project.active_page
        new_page = copy.deepcopy(curr)
        new_page.id = str(uuid.uuid4())
        new_page.name = f"{curr.name} (Copy)"
        
        # Give fresh IDs to duplicated layers
        for layer in new_page.layers:
            layer.id = str(uuid.uuid4())

        insert_pos = project.active_page_index + 1
        project.pages.insert(insert_pos, new_page)
        project.active_page_index = insert_pos
        self.refresh()
        self.on_page_changed()

    def rename_current_page(self):
        project = self.get_project()
        curr = project.active_page
        new_name = simpledialog.askstring(
            "Rename Page",
            "Enter new page name:",
            initialvalue=curr.name,
            parent=self
        )
        if new_name and new_name.strip():
            curr.name = new_name.strip()
            self.refresh()
            self.on_page_changed()

    def delete_current_page(self):
        project = self.get_project()
        if len(project.pages) <= 1:
            messagebox.showwarning("Cannot Delete", "Project must have at least one page.", parent=self)
            return

        curr = project.active_page
        if messagebox.askyesno("Confirm Delete", f"Delete page '{curr.name}'?", parent=self):
            project.pages.pop(project.active_page_index)
            if project.active_page_index >= len(project.pages):
                project.active_page_index = len(project.pages) - 1
            self.refresh()
            self.on_page_changed()
