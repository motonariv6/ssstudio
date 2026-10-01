from __future__ import annotations
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Optional
from PIL import Image, ImageDraw, ImageTk
from ui.theme import BTN_BG_DEFAULT, BTN_BG_HOVER, BTN_BG_ACTIVE, BTN_FG, FONT_SMALL


def button_colors(state, hovered, pressed, normal, hover, active, foreground):
    if state == 'disabled':
        return normal, '#636366'
    return active if pressed else hover if hovered else normal, foreground


class DarkButton(tk.Canvas):
    """Rounded theme button retaining the existing text/command/color API."""
    def __init__(self, master=None, text='', command: Optional[Callable[[], None]]=None,
                 bg=BTN_BG_DEFAULT, fg=BTN_FG, hover_bg=None, active_bg=None,
                 font=FONT_SMALL, padx=8, pady=4, cursor='pointinghand', state='normal', **kwargs):
        self._text, self._command = text, command
        self._default_bg, self._fg = bg, fg
        self._hover_bg = hover_bg or self._calculate_hover_color(bg)
        self._active_bg = active_bg or BTN_BG_ACTIVE
        self._state, self._cursor = state, cursor
        self._hovered = self._pressed = False
        self._font = tkfont.Font(master, font=font)
        self._padx, self._pady = padx, pady
        self._anchor = kwargs.pop('anchor', 'center')
        self._explicit_width = kwargs.pop('width', None)
        self._explicit_height = kwargs.pop('height', None)
        for option in ('relief', 'borderwidth', 'bd', 'highlightthickness'):
            kwargs.pop(option, None)
        super().__init__(master, bg=master.cget('bg'), highlightthickness=0, bd=0,
                         takefocus=True, cursor=cursor if state == 'normal' else 'arrow', **kwargs)
        self._size()
        self.bind('<Configure>', self._draw)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Key-space>', self._keyboard_invoke)
        self.bind('<Return>', self._keyboard_invoke)
        self.bind('<FocusIn>', self._draw)
        self.bind('<FocusOut>', self._draw)

    def _size(self):
        width = self._explicit_width or max(self._font.measure(line) for line in self._text.split('\n')) + 2 * self._padx
        height = self._explicit_height or self._font.metrics('linespace') * len(self._text.split('\n')) + 2 * self._pady
        super().configure(width=max(1, width), height=max(1, height))

    def _draw(self, event=None):
        if not self.winfo_exists():
            return
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        bg, fg = button_colors(self._state, self._hovered, self._pressed,
                               self._default_bg, self._hover_bg, self._active_bg, self._fg)
        # Supersampling makes small rounded corners smooth on Retina displays.
        scale = 3
        image = Image.new('RGB', (width * scale, height * scale), self.master.cget('bg'))
        draw = ImageDraw.Draw(image)
        radius = min(8, width / 2, height / 2) * scale
        draw.rounded_rectangle((0, 0, width * scale - 1, height * scale - 1), radius=radius, fill=bg)
        if self.focus_get() is self:
            draw.rounded_rectangle((2, 2, width * scale - 3, height * scale - 3), radius=radius,
                                   outline='#8E8E93', width=scale)
        self._photo = ImageTk.PhotoImage(image.resize((width, height), Image.Resampling.LANCZOS), master=self)
        self.delete('all')
        self.create_image(0, 0, image=self._photo, anchor='nw')
        anchor = self._anchor if self._anchor in ('w', 'e') else 'center'
        x = self._padx if anchor == 'w' else width - self._padx if anchor == 'e' else width / 2
        self.create_text(x, height / 2, text=self._text, fill=fg, font=self._font, anchor=anchor)

    def configure(self, cnf=None, **kwargs):
        if cnf is not None and not isinstance(cnf, dict):
            return super().configure(cnf, **kwargs)
        if cnf:
            kwargs = {**cnf, **kwargs}
        if not kwargs:
            return super().configure()
        for name, attr in [('text', '_text'), ('command', '_command'), ('fg', '_fg'),
                           ('foreground', '_fg'), ('bg', '_default_bg'), ('background', '_default_bg'),
                           ('hover_bg', '_hover_bg'), ('active_bg', '_active_bg'), ('state', '_state'),
                           ('padx', '_padx'), ('pady', '_pady'), ('anchor', '_anchor')]:
            if name in kwargs:
                setattr(self, attr, kwargs.pop(name))
                if name in ('bg', 'background'):
                    self._hover_bg = self._calculate_hover_color(self._default_bg)
        if 'font' in kwargs:
            self._font = tkfont.Font(self, font=kwargs.pop('font'))
        if kwargs:
            super().configure(**kwargs)
        super().configure(cursor=self._cursor if self._state == 'normal' else 'arrow')
        self._size()
        self._draw()

    config = configure

    def cget(self, key):
        values = {'text': self._text, 'bg': self._default_bg, 'background': self._default_bg,
                  'fg': self._fg, 'foreground': self._fg, 'state': self._state,
                  'padx': self._padx, 'pady': self._pady, 'anchor': self._anchor}
        return values[key] if key in values else super().cget(key)

    def _calculate_hover_color(self, color):
        try:
            rgb = [int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
            return '#' + ''.join(f'{min(255, int(value * 1.25) + 15):02x}' for value in rgb)
        except (ValueError, TypeError, AttributeError):
            return BTN_BG_HOVER

    def set_command(self, command):
        self._command = command

    def set_bg(self, bg, hover_bg=None):
        self._default_bg = bg
        self._hover_bg = hover_bg or self._calculate_hover_color(bg)
        self._draw()

    def set_state(self, state):
        self._pressed = False
        self.configure(state=state)

    def invoke(self):
        if self._state == 'normal' and self._command:
            return self._command()

    def _keyboard_invoke(self, event=None):
        self.invoke()
        return 'break'

    def _on_enter(self, event=None):
        self._hovered = True
        self._draw()

    def _on_leave(self, event=None):
        self._hovered = False
        self._draw()

    def _on_press(self, event=None):
        if self._state == 'normal':
            self._pressed = True
            self.focus_set()
            self._draw()

    def _on_release(self, event=None):
        pressed = self._pressed
        self._pressed = False
        inside = event is None or (0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height())
        self._draw()
        if pressed and inside:
            self.invoke()
