import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from ui.collapsible_section import SectionState
from ui.scrollable_panel import wheel_pixels, ScrollablePanel
from ui.widgets import button_colors, DarkButton


class InspectorUXTests(unittest.TestCase):
    def test_toggle_and_section_isolation(self):
        state = SectionState()
        key = ('image', 'Transform')
        self.assertTrue(state.is_open(key))
        self.assertFalse(state.toggle(key))
        self.assertTrue(state.is_open(('text', 'Transform')))
        self.assertTrue(state.is_open(('image', 'Crop')))
        self.assertTrue(state.toggle(key))
        self.assertTrue(SectionState().is_open(key))

    def test_wheel_platforms_and_small_trackpad_delta(self):
        self.assertEqual(wheel_pixels(1, system='aqua'), -6)
        self.assertEqual(wheel_pixels(-1, system='aqua'), 6)
        self.assertEqual(wheel_pixels(120, system='win32'), -40)
        self.assertEqual(wheel_pixels(button=4, system='x11'), -40)
        self.assertEqual(wheel_pixels(button=5, system='x11'), 40)
        self.assertEqual(wheel_pixels(1000, system='aqua'), -80)

    def test_wheel_during_slider_drag_does_not_scroll(self):
        panel = SimpleNamespace(canvas=Mock(), _system='aqua')
        self.assertEqual(ScrollablePanel._wheel(panel, SimpleNamespace(state=0x100)), 'break')
        panel.canvas.yview_scroll.assert_not_called()
        ScrollablePanel._wheel(panel, SimpleNamespace(state=0, delta=-2, num=None))
        panel.canvas.yview_scroll.assert_called_once_with(12, 'units')

    def test_button_visual_states(self):
        colors = ('normal', 'hover', 'active', 'white')
        self.assertEqual(button_colors('normal', False, False, *colors), ('normal', 'white'))
        self.assertEqual(button_colors('normal', True, False, *colors), ('hover', 'white'))
        self.assertEqual(button_colors('normal', True, True, *colors), ('active', 'white'))
        self.assertEqual(button_colors('disabled', True, True, *colors), ('normal', '#636366'))

    def test_button_release_outside_and_disabled_do_not_invoke(self):
        button = SimpleNamespace(_pressed=True, _draw=Mock(), invoke=Mock(),
                                 winfo_width=lambda: 100, winfo_height=lambda: 30)
        DarkButton._on_release(button, SimpleNamespace(x=120, y=10))
        button.invoke.assert_not_called()
        button._pressed = True
        DarkButton._on_release(button, SimpleNamespace(x=50, y=10))
        button.invoke.assert_called_once()
        command = Mock()
        DarkButton.invoke(SimpleNamespace(_state='disabled', _command=command))
        command.assert_not_called()

# Run these with SSSTUDIO_GUI_TESTS=1 on a machine with a Tk display.
import os
import tkinter as tk
from core.models import Project, Page, ImageLayer, TextLayer
from ui.layer_sidebar import LayerSidebar
from ui.collapsible_section import CollapsibleSection


@unittest.skipUnless(os.environ.get('SSSTUDIO_GUI_TESTS') == '1', 'requires a Tk display')
class InspectorTkTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry('390x360')
        self.addCleanup(self.root.destroy)
        self.project = Project(pages=[Page(layers=[ImageLayer(), TextLayer()])])
        self.selected = self.project.active_page.layers[0]
        self.panel = LayerSidebar(self.root, lambda: self.project, lambda: self.project.active_page,
                                  lambda: self.selected, lambda layer: None, lambda: None)
        self.panel.pack(fill=tk.BOTH, expand=True)
        self.root.update()

    def sections(self):
        return {w.title: w for w in self.panel.inspector_container.winfo_children()
                if isinstance(w, CollapsibleSection)}

    def test_sections_rebuild_and_scroll_bounds(self):
        self.assertEqual(set(self.sections()), {'Transform', 'Crop', 'Image Effects', 'Device Frame & Shadow'})
        self.panel.canvas_scroll.yview_moveto(1)
        self.root.update()
        self.assertAlmostEqual(self.panel.canvas_scroll.yview()[1], 1, delta=.005)
        self.assertGreater(self.panel.canvas_scroll.yview()[0], 0)
        self.sections()['Image Effects'].toggle()
        self.root.update()
        self.assertFalse(self.sections()['Image Effects'].content.winfo_ismapped())
        self.panel.refresh()
        self.root.update()
        self.assertFalse(self.sections()['Image Effects'].content.winfo_ismapped())
        self.selected = self.project.active_page.layers[1]
        self.panel.refresh()
        self.root.update()
        self.assertEqual(set(self.sections()), {'Transform', 'Text', 'Typography'})
        self.assertTrue(self.sections()['Transform'].content.winfo_ismapped())
        self.selected = self.project.active_page.layers[0]
        self.panel.refresh()
        self.root.update()
        self.assertFalse(self.sections()['Image Effects'].content.winfo_ismapped())
        self.root.geometry('390x680')
        self.root.update()
        self.assertEqual(int(float(self.panel.canvas_scroll.itemcget(self.panel._scroll_window, 'width'))),
                         self.panel.canvas_scroll.winfo_width())

    def test_descendant_wheel_drag_isolation_and_button_api(self):
        content = self.sections()['Transform'].content
        slider = next(w for row in content.winfo_children() for w in row.winfo_children()
                      if isinstance(w, tk.Scale))
        self.assertEqual(slider.bindtags()[0], self.panel.scroll_panel._tag)
        self.panel.canvas_scroll.yview_moveto(0)
        value = slider.get()
        slider.event_generate('<MouseWheel>', delta=-3)
        self.root.update()
        self.assertGreater(self.panel.canvas_scroll.yview()[0], 0)
        self.assertEqual(slider.get(), value)
        view = self.panel.canvas_scroll.yview()
        slider.event_generate('<MouseWheel>', delta=-3, state=0x100)
        self.root.update()
        self.assertEqual(self.panel.canvas_scroll.yview(), view)
        command = Mock()
        button = DarkButton(content, text='Test', command=command)
        button.pack()
        self.root.update()
        button.configure(text='A longer label', bg='#112233', fg='#ffffff')
        self.assertEqual(button.cget('text'), 'A longer label')
        self.assertEqual(button.cget('bg'), '#112233')
        button.set_state('disabled')
        button.invoke()
        command.assert_not_called()
        button.set_state('normal')
        button.invoke()
        command.assert_called_once()
