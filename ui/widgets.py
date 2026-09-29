from __future__ import annotations
import tkinter as tk
from typing import Callable, Optional
from ui.theme import (
    BTN_BG_DEFAULT, BTN_BG_HOVER, BTN_BG_ACTIVE, BTN_FG,
    FONT_SMALL, FONT_BOLD
)


class DarkButton(tk.Label):
    """
    Cross-platform Dark-themed button widget.
    Avoids macOS native Aqua button styling issues and ensures clear white text
    on crisp medium gray (or custom accent) backgrounds.
    """

    def __init__(
        self,
        master=None,
        text: str = "",
        command: Optional[Callable[[], None]] = None,
        bg: str = BTN_BG_DEFAULT,
        fg: str = BTN_FG,
        hover_bg: Optional[str] = None,
        active_bg: Optional[str] = None,
        font=FONT_SMALL,
        padx: int = 8,
        pady: int = 4,
        cursor: str = "pointinghand",
        state: str = "normal",
        **kwargs
    ):
        self._default_bg = bg
        self._hover_bg = hover_bg or self._calculate_hover_color(bg)
        self._active_bg = active_bg or BTN_BG_ACTIVE
        self._fg = fg
        self._command = command
        self._state = state

        super().__init__(
            master,
            text=text,
            bg=self._default_bg,
            fg=self._fg,
            font=font,
            padx=padx,
            pady=pady,
            relief=tk.FLAT,
            cursor=cursor if state == "normal" else "arrow",
            **kwargs
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _calculate_hover_color(self, hex_color: str) -> str:
        """Lightens the color slightly for hover state."""
        try:
            hex_color = hex_color.lstrip("#")
            if len(hex_color) == 6:
                r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
                r = min(255, int(r * 1.25) + 15)
                g = min(255, int(g * 1.25) + 15)
                b = min(255, int(b * 1.25) + 15)
                return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            pass
        return BTN_BG_HOVER

    def set_command(self, cmd: Callable[[], None]):
        self._command = cmd

    def set_bg(self, bg: str, hover_bg: Optional[str] = None):
        self._default_bg = bg
        self._hover_bg = hover_bg or self._calculate_hover_color(bg)
        self.configure(bg=self._default_bg)

    def _on_enter(self, event=None):
        if self._state == "normal":
            self.configure(bg=self._hover_bg)

    def _on_leave(self, event=None):
        if self._state == "normal":
            self.configure(bg=self._default_bg)

    def _on_press(self, event=None):
        if self._state == "normal":
            self.configure(bg=self._active_bg)

    def _on_release(self, event=None):
        if self._state == "normal":
            self.configure(bg=self._hover_bg)
            if self._command:
                self._command()

    def set_state(self, state: str):
        self._state = state
        if state == "disabled":
            self.configure(fg="#636366", cursor="arrow")
        else:
            self.configure(fg=self._fg, cursor="pointinghand")
