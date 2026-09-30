"""Small per-page workspace controls shared by the canvas panels."""
import tkinter as tk
from tkinter import ttk
from ui.theme import BG_SECONDARY, TEXT_SECONDARY, FONT_SMALL


class WorkspaceControls(tk.Frame):
    def __init__(self, parent, get_page, on_change):
        super().__init__(parent, bg=BG_SECONDARY)
        self.get_page, self.on_change = get_page, on_change
        self.mode = tk.StringVar()
        self.screens = tk.StringVar()
        tk.Label(self, text="Workspace:", bg=BG_SECONDARY, fg=TEXT_SECONDARY,
                 font=FONT_SMALL).pack(anchor=tk.W)
        row = tk.Frame(self, bg=BG_SECONDARY)
        row.pack(fill=tk.X)
        self.mode_combo = ttk.Combobox(row, textvariable=self.mode, values=["Single", "Panorama"],
                                      state="readonly", width=10)
        self.mode_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(row, text="Screens:", bg=BG_SECONDARY, fg=TEXT_SECONDARY,
                 font=FONT_SMALL).pack(side=tk.LEFT, padx=3)
        self.screens_combo = ttk.Combobox(row, textvariable=self.screens, values=["2", "3", "4"],
                                         state="readonly", width=2)
        self.screens_combo.pack(side=tk.LEFT)
        self.mode_combo.bind("<<ComboboxSelected>>", self._changed)
        self.screens_combo.bind("<<ComboboxSelected>>", self._changed)
        self.refresh()

    def refresh(self):
        config = self.get_page().panorama
        self.mode.set("Panorama" if config.enabled else "Single")
        self.screens.set(str(max(2, config.screen_count)))
        self.screens_combo.configure(state="readonly" if config.enabled else "disabled")

    def _changed(self, event=None):
        config = self.get_page().panorama
        config.enabled = self.mode.get() == "Panorama"
        config.screen_count = int(self.screens.get())
        self.refresh()
        self.on_change()
