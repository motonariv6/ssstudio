"""Inspector sections with session-only state, independent of project data."""
import tkinter as tk
from ui.theme import BG_SECONDARY, BG_TERTIARY, TEXT_PRIMARY, FONT_BOLD
from ui.widgets import DarkButton


class SectionState:
    def __init__(self):
        self._values = {}

    def is_open(self, key):
        return self._values.get(key, True)

    def toggle(self, key):
        self._values[key] = not self.is_open(key)
        return self._values[key]


class CollapsibleSection(tk.Frame):
    def __init__(self, master, title, state, key):
        super().__init__(master, bg=BG_SECONDARY)
        self.title, self.state, self.key = title, state, key
        self.header = DarkButton(self, font=FONT_BOLD, bg=BG_TERTIARY,
                                 fg=TEXT_PRIMARY, command=self.toggle, anchor='w', padx=8, pady=6)
        self.header.pack(fill=tk.X)
        self.content = tk.Frame(self, bg=BG_SECONDARY, padx=4, pady=4)
        self._display()

    def toggle(self):
        self.state.toggle(self.key)
        self._display()

    def _display(self):
        opened = self.state.is_open(self.key)
        self.header.configure(text=('▾ ' if opened else '▸ ') + self.title)
        if opened:
            self.content.pack(fill=tk.X)
        else:
            self.content.pack_forget()


def inspector_section(panel, layer_type, title):
    if not hasattr(panel, '_section_state'):
        panel._section_state = SectionState()
    section = CollapsibleSection(panel.inspector_container, title, panel._section_state,
                                 (layer_type, title))
    section.pack(fill=tk.X, pady=4)
    return section.content
