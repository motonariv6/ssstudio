from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from core.models import Project, Page, LayerType, CANVAS_PRESETS, THEME_LEMEMO_LUXURY
from core.project import save_project_to_json, load_project_from_json
from core.templates import TEMPLATE_FACTORIES, apply_theme_to_page
from core.exporter import export_single_page, export_all_pages, get_default_export_filename
from ui.theme import (
    BG_DARK, BG_SECONDARY, BG_TERTIARY, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_COLOR, ACCENT_LEMEMO, FONT_BOLD, FONT_SMALL, FONT_TITLE, FONT_SYSTEM,
    BTN_BG_DEFAULT, BTN_BG_HOVER, BTN_FG, BTN_ACCENT_BG, BTN_ACCENT_HOVER,
    BTN_LEMEMO_BG, BTN_LEMEMO_HOVER
)
from ui.widgets import DarkButton
from ui.canvas_view import CanvasView
from ui.page_manager import PageManagerBar
from ui.property_panel import PropertyPanel


class MainWindow(tk.Tk):
    """Main Application Window for SSStudio."""

    def __init__(self):
        super().__init__()
        self.title("SSStudio — App Store Screenshot Composer")
        self.geometry("1380x880")
        self.minsize(1050, 680)
        self.configure(bg=BG_DARK)

        # State
        self.project = Project()
        self.current_project_path: Optional[str] = None
        self.selected_layer: Optional[LayerType] = None

        # Setup initial default template (Headline Top) for page 1
        self._init_default_project()

        # Build UI
        self._build_menu()
        self._build_toolbar()
        self._build_main_layout()

        # Refresh
        self.refresh_all()

    def _init_default_project(self):
        """Initializes default 6-page project for App Store screenshot production."""
        self.project = Project(preset_name="iPhone 6.9-inch", canvas_width=1290, canvas_height=2796)
        
        # Initialize page 1 with headline top template
        p1 = TEMPLATE_FACTORIES["Headline Top"](self.project.canvas_width, self.project.canvas_height)
        p1.name = "01_people"
        
        # Initialize page 2 with split template
        p2 = TEMPLATE_FACTORIES["Split"](self.project.canvas_width, self.project.canvas_height)
        p2.name = "02_memory"

        # Initialize page 3 with center device template
        p3 = TEMPLATE_FACTORIES["Center Device"](self.project.canvas_width, self.project.canvas_height)
        p3.name = "03_schedule"

        self.project.pages = [p1, p2, p3]
        self.project.active_page_index = 0

    # -------------------------------------------------------------
    # Menu & Toolbar
    # -------------------------------------------------------------
    def _build_menu(self):
        menubar = tk.Menu(self)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project", accelerator="Cmd+N", command=self.on_new_project)
        file_menu.add_command(label="Open Project...", accelerator="Cmd+O", command=self.on_open_project)
        file_menu.add_command(label="Save Project", accelerator="Cmd+S", command=self.on_save_project)
        file_menu.add_command(label="Save Project As...", command=self.on_save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export Current Page (PNG)...", accelerator="Cmd+E", command=self.on_export_current)
        file_menu.add_command(label="Export All Pages...", accelerator="Cmd+Shift+E", command=self.on_export_all)
        menubar.add_cascade(label="File", menu=file_menu)

        # Template Menu
        template_menu = tk.Menu(menubar, tearoff=0)
        for name in TEMPLATE_FACTORIES.keys():
            template_menu.add_command(
                label=f"Apply {name}",
                command=lambda t_name=name: self.on_apply_template(t_name)
            )
        menubar.add_cascade(label="Template", menu=template_menu)

        self.config(menu=menubar)

        # Shortcuts
        self.bind_all("<Command-n>", lambda e: self.on_new_project())
        self.bind_all("<Command-o>", lambda e: self.on_open_project())
        self.bind_all("<Command-s>", lambda e: self.on_save_project())
        self.bind_all("<Command-e>", lambda e: self.on_export_current())
        self.bind_all("<Command-Shift-E>", lambda e: self.on_export_all())

    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg=BG_SECONDARY, height=48)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)

        # Brand / Title
        tk.Label(
            toolbar, text="SSStudio", font=FONT_TITLE, fg=TEXT_PRIMARY, bg=BG_SECONDARY, padx=12
        ).pack(side=tk.LEFT)

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=8)

        # File actions
        self._create_tool_btn(toolbar, "📄 New", self.on_new_project)
        self._create_tool_btn(toolbar, "📂 Open", self.on_open_project)
        self._create_tool_btn(toolbar, "💾 Save", self.on_save_project)

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        # Template selector dropdown
        tk.Label(toolbar, text="Template:", font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(side=tk.LEFT, padx=(4, 2))
        self.toolbar_template_var = tk.StringVar(value="Headline Top")
        tpl_combo = ttk.Combobox(
            toolbar,
            textvariable=self.toolbar_template_var,
            values=list(TEMPLATE_FACTORIES.keys()),
            state="readonly",
            width=14
        )
        tpl_combo.pack(side=tk.LEFT, padx=2)
        
        btn_apply_tpl = DarkButton(
            toolbar, text="Apply", bg=BTN_BG_DEFAULT, fg=BTN_FG,
            font=FONT_SMALL, padx=8, pady=4, command=lambda: self.on_apply_template(self.toolbar_template_var.get())
        )
        btn_apply_tpl.pack(side=tk.LEFT, padx=2)

        # Theme preset button
        btn_theme = DarkButton(
            toolbar, text="✨ Lememo Luxury Theme", bg=BTN_LEMEMO_BG, hover_bg=BTN_LEMEMO_HOVER, fg=BTN_FG,
            font=FONT_BOLD, padx=10, pady=4, command=self.on_apply_luxury_theme
        )
        btn_theme.pack(side=tk.LEFT, padx=8)

        # Guides Toggle
        self.guides_btn = DarkButton(
            toolbar, text="📐 Guides: ON", bg=BTN_BG_DEFAULT, fg=BTN_FG,
            font=FONT_SMALL, padx=8, pady=4, command=self.on_toggle_guides
        )
        self.guides_btn.pack(side=tk.LEFT, padx=4)

        # Right side: Export buttons
        right_frame = tk.Frame(toolbar, bg=BG_SECONDARY)
        right_frame.pack(side=tk.RIGHT, padx=12)

        btn_export_single = DarkButton(
            right_frame, text="Export PNG", bg=BTN_BG_DEFAULT, fg=BTN_FG,
            font=FONT_BOLD, padx=10, pady=4, command=self.on_export_current
        )
        btn_export_single.pack(side=tk.LEFT, padx=4)

        btn_export_all = DarkButton(
            right_frame, text="⚡ Export All PNGs", bg=BTN_ACCENT_BG, hover_bg=BTN_ACCENT_HOVER, fg=BTN_FG,
            font=FONT_BOLD, padx=12, pady=4, command=self.on_export_all
        )
        btn_export_all.pack(side=tk.LEFT, padx=4)

    def _create_tool_btn(self, parent, text, command):
        btn = DarkButton(
            parent, text=text, bg=BTN_BG_DEFAULT, fg=BTN_FG,
            font=FONT_SMALL, padx=8, pady=4, command=command
        )
        btn.pack(side=tk.LEFT, padx=2)
        return btn

    # -------------------------------------------------------------
    # Main Layout
    # -------------------------------------------------------------
    def _build_main_layout(self):
        container = tk.Frame(self, bg=BG_DARK)
        container.pack(fill=tk.BOTH, expand=True)

        # Left area: Page Bar + Canvas
        left_pane = tk.Frame(container, bg=BG_DARK)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Top Page Manager Bar
        self.page_bar = PageManagerBar(
            left_pane,
            get_project=lambda: self.project,
            on_page_changed=self._on_page_switched
        )
        self.page_bar.pack(side=tk.TOP, fill=tk.X)

        # Interactive Canvas Preview
        self.canvas_view = CanvasView(
            left_pane,
            get_project=lambda: self.project,
            get_active_page=lambda: self.project.active_page,
            on_layer_selected=self._on_layer_selected,
            on_content_changed=self._on_content_changed
        )
        self.canvas_view.pack(fill=tk.BOTH, expand=True)

        # Right area: Property Panel
        self.property_panel = PropertyPanel(
            container,
            get_project=lambda: self.project,
            get_active_page=lambda: self.project.active_page,
            get_selected_layer=lambda: self.selected_layer,
            on_select_layer=self._on_layer_selected,
            on_change=self._on_content_changed
        )
        self.property_panel.pack(side=tk.RIGHT, fill=tk.Y)

    # -------------------------------------------------------------
    # Event Handlers & State Sync
    # -------------------------------------------------------------
    def _on_page_switched(self):
        self.selected_layer = None
        self.canvas_view.set_selected_layer(None)
        self.canvas_view.refresh()
        self.property_panel.refresh()

    def _on_layer_selected(self, layer: Optional[LayerType]):
        self.selected_layer = layer
        self.canvas_view.set_selected_layer(layer)
        self.property_panel.refresh()

    def _on_content_changed(self):
        self.canvas_view.refresh()
        self.property_panel._refresh_layer_list()

    def refresh_all(self):
        self.page_bar.refresh()
        self.canvas_view.refresh()
        self.property_panel.refresh()

    def on_toggle_guides(self):
        new_state = not self.canvas_view.show_guides
        self.canvas_view.set_show_guides(new_state)
        self.guides_btn.configure(text=f"📐 Guides: {'ON' if new_state else 'OFF'}")

    def on_apply_template(self, template_name: str):
        if template_name not in TEMPLATE_FACTORIES:
            return

        if messagebox.askyesno(
            "Apply Template",
            f"Apply template '{template_name}' to current page?\nThis will replace the current page layout.",
            parent=self
        ):
            active_p = self.project.active_page
            new_p = TEMPLATE_FACTORIES[template_name](self.project.canvas_width, self.project.canvas_height)
            active_p.background = new_p.background
            active_p.layers = new_p.layers
            self.selected_layer = None
            self.refresh_all()

    def on_apply_luxury_theme(self):
        active_p = self.project.active_page
        apply_theme_to_page(active_p, THEME_LEMEMO_LUXURY)
        self.refresh_all()

    # -------------------------------------------------------------
    # Project Save / Load / Export Actions
    # -------------------------------------------------------------
    def on_new_project(self):
        if messagebox.askyesno("New Project", "Create a new project? Any unsaved changes will be lost.", parent=self):
            self._init_default_project()
            self.current_project_path = None
            self.selected_layer = None
            self.refresh_all()

    def on_open_project(self):
        file_path = filedialog.askopenfilename(
            title="Open Project JSON",
            filetypes=[("SSStudio Project", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        proj, msg = load_project_from_json(file_path)
        if proj:
            self.project = proj
            self.current_project_path = file_path
            self.selected_layer = None
            self.refresh_all()
        else:
            messagebox.showerror("Open Error", msg, parent=self)

    def on_save_project(self):
        if self.current_project_path:
            ok, msg = save_project_to_json(self.project, self.current_project_path)
            if ok:
                messagebox.showinfo("Saved", f"Project saved to {os.path.basename(self.current_project_path)}", parent=self)
            else:
                messagebox.showerror("Save Error", msg, parent=self)
        else:
            self.on_save_project_as()

    def on_save_project_as(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Project As",
            defaultextension=".json",
            filetypes=[("SSStudio Project", "*.json")]
        )
        if not file_path:
            return

        ok, msg = save_project_to_json(self.project, file_path)
        if ok:
            self.current_project_path = file_path
            messagebox.showinfo("Saved", f"Project saved to {os.path.basename(file_path)}", parent=self)
        else:
            messagebox.showerror("Save Error", msg, parent=self)

    def on_export_current(self):
        curr_page = self.project.active_page
        page_idx = self.project.active_page_index
        default_name = get_default_export_filename(page_idx, curr_page.name)
        
        # Ask output file path
        output_path = filedialog.asksaveasfilename(
            title=f"Export Current Page ({self.project.canvas_width} × {self.project.canvas_height} px)",
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")]
        )
        if not output_path:
            return

        if os.path.exists(output_path):
            if not messagebox.askyesno("Overwrite Confirmation", f"File '{os.path.basename(output_path)}' already exists.\nDo you want to overwrite it?", parent=self):
                return

        ok, msg, dims = export_single_page(self.project, curr_page, output_path)
        if ok:
            messagebox.showinfo(
                "Export Complete",
                f"Successfully exported page:\n\nResolution: {dims[0]} × {dims[1]} px\nPath: {output_path}",
                parent=self
            )
        else:
            messagebox.showerror("Export Error", f"Export failed: {msg}", parent=self)

    def on_export_all(self):
        output_dir = filedialog.askdirectory(title="Select Output Directory for Batch Export")
        if not output_dir:
            return

        total_pages = len(self.project.pages)
        msg_confirm = (
            f"Export all {total_pages} pages to:\n{output_dir}\n\n"
            f"Resolution per page: {self.project.canvas_width} × {self.project.canvas_height} px\n"
            f"Mode: App Store RGB PNG\n\nProceed?"
        )
        if not messagebox.askyesno("Batch Export Confirmation", msg_confirm, parent=self):
            return

        results = export_all_pages(self.project, output_dir)
        success_count = sum(1 for _, ok, _, _ in results if ok)
        
        file_list_str = "\n".join([f"• {fname} ({dims[0]}×{dims[1]})" for fname, ok, _, dims in results if ok])

        messagebox.showinfo(
            "Batch Export Complete",
            f"Successfully exported {success_count} of {total_pages} pages:\n\n{file_list_str}",
            parent=self
        )
