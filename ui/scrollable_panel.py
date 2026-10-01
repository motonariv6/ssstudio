"""Reusable vertical scrolling with wheel bindings local to panel descendants."""
import tkinter as tk
from tkinter import ttk


def wheel_pixels(delta=0, button=None, system='aqua'):
    if button in (4, 5):
        return -40 if button == 4 else 40
    if system == 'aqua':
        return max(-80, min(80, round(-delta * 6)))
    return round(-delta / 120 * 40)


class ScrollablePanel(tk.Frame):
    def __init__(self, master, bg, **kwargs):
        super().__init__(master, bg=bg, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, yscrollincrement=1)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=bg)
        self.window = self.canvas.create_window((0, 0), window=self.content, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._tag = 'PanelWheel' + str(self)
        self._system = self.tk.call('tk', 'windowingsystem')
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self.bind_class(self._tag, sequence, self._wheel)
        self.canvas.bind('<Configure>', self._resize)
        self.content.bind('<Configure>', self._layout)
        self.bind('<Destroy>', self._cleanup, add='+')
        self._bind_children(self)

    def _bind_children(self, widget):
        tags = widget.bindtags()
        if self._tag not in tags:
            widget.bindtags((self._tag,) + tags)
        for child in widget.winfo_children():
            self._bind_children(child)

    def _resize(self, event):
        self.canvas.itemconfigure(self.window, width=max(1, event.width))
        self._layout()

    def _layout(self, event=None):
        height = max(self.content.winfo_reqheight(), self.canvas.winfo_height())
        self.canvas.configure(scrollregion=(0, 0, max(1, self.canvas.winfo_width()), height))
        self._bind_children(self)

    def _wheel(self, event):
        widget = getattr(event, 'widget', None)
        if widget is not None and widget.winfo_class() == 'Listbox':
            # Layer lists retain their own scrolling when there are many layers.
            return None
        # Consume wheel events during dragging, keeping sliders and the panel still.
        if not event.state & 0x100:
            pixels = wheel_pixels(getattr(event, 'delta', 0), getattr(event, 'num', None), self._system)
            self.canvas.yview_scroll(pixels, 'units')
        return 'break'

    def _cleanup(self, event):
        if event.widget is self:
            for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                self.unbind_class(self._tag, sequence)
