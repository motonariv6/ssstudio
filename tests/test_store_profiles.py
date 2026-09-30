import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image, ImageChops

from core.models import CANVAS_PRESETS, Project, Page, ImageLayer, TextLayer, FrameConfig
from core.store_profiles import get_store_preset_labels
from core.store_validation import validate_store_canvas, validate_project_export
from core.project import save_project_to_json, load_project_from_json
from core.exporter import export_single_page, export_all_pages
from core.renderer import render_page
from core.templates import TEMPLATE_FACTORIES
from ui.canvas_sidebar import CanvasSidebar
from ui.property_panel import PropertyPanel
from ui.page_manager import PageManagerBar
from ui.main_window import MainWindow


GOOGLE_PRESETS = {
    'Google Play Phone Portrait': (1080, 1920, 'phone', 'portrait'),
    'Google Play Phone Landscape': (1920, 1080, 'phone', 'landscape'),
    'Google Play Tablet Portrait': (1080, 1920, 'tablet', 'portrait'),
    'Google Play Tablet Landscape': (1920, 1080, 'tablet', 'landscape'),
}


class StoreProfileTests(unittest.TestCase):
    def test_legacy_profiles_keep_keys_dimensions_and_description(self):
        for key, size in {'iPhone 6.9-inch': (1290, 2796), 'iPhone 6.5-inch': (1242, 2688),
                          'iPhone 6.3-inch': (1206, 2622), 'iPad 13-inch': (2064, 2752),
                          'Custom': (1290, 2796)}.items():
            with self.subTest(key=key):
                profile = CANVAS_PRESETS[key]
                self.assertEqual((profile['width'], profile['height']), size)
                self.assertEqual(profile['name'], key)
                self.assertEqual(profile['description'], profile['desc'])
                self.assertTrue(profile['description'])
                self.assertEqual(profile['store'], 'custom' if key == 'Custom' else 'apple_app_store')

    def test_google_profiles_and_selection(self):
        project = Project()
        for key, (w, h, device, orientation) in GOOGLE_PRESETS.items():
            with self.subTest(key=key):
                profile = CANVAS_PRESETS[key]
                self.assertEqual((profile['width'], profile['height'], profile['device_type'], profile['orientation']),
                                 (w, h, device, orientation))
                project.set_preset(key)
                self.assertEqual((project.canvas_width, project.canvas_height, project.device_type,
                                  project.orientation, project.store), (w, h, device, orientation, 'google_play'))
                self.assertEqual(validate_project_export(project), [])

    def test_custom_retains_store_device_and_updates_orientation(self):
        project = Project()
        project.set_preset('Google Play Tablet Portrait')
        project.set_custom_size(1000, 500)
        self.assertEqual((project.preset_name, project.store, project.device_type, project.orientation),
                         ('Custom', 'google_play', 'tablet', 'landscape'))
        project.set_custom_size(500, 500)
        self.assertEqual(project.orientation, 'square')
        project.set_store('apple_app_store')
        self.assertEqual((project.canvas_width, project.canvas_height), (500, 500))
        project.set_preset('iPhone 6.3-inch')
        self.assertEqual((project.store, project.device_type), ('apple_app_store', 'phone'))
        project.set_preset('Custom')
        self.assertEqual((project.canvas_width, project.canvas_height), (1290, 2796))
        self.assertEqual(project.store, 'apple_app_store')

    def test_labels_are_store_specific_and_keys_stable(self):
        self.assertEqual(get_store_preset_labels('google_play')['Phone Portrait'], 'Google Play Phone Portrait')
        self.assertNotIn('iPhone 6.9-inch', get_store_preset_labels('google_play'))
        self.assertIn('Custom', get_store_preset_labels('google_play'))
        self.assertIn('iPhone 6.9-inch', get_store_preset_labels('apple_app_store'))

    def test_old_apple_json_dimensions_and_crop_unchanged(self):
        data = {'name': 'Legacy', 'preset_name': 'iPad 13-inch', 'canvas_width': 2064,
                'canvas_height': 2752, 'active_page_index': 0, 'pages': [Page(layers=[
                    ImageLayer(crop_left=.2, crop_top=.1, crop_right=.8, crop_bottom=.9)]).to_dict()]}
        project = Project.from_dict(data)
        output = project.to_dict()
        for key, value in data.items():
            self.assertEqual(output[key], value)
        self.assertEqual((project.store, project.device_type, project.orientation),
                         ('apple_app_store', 'tablet', 'portrait'))
        # Old Custom/unknown profiles retain stored dimensions and are not Google validated.
        for key in ['Custom', 'Legacy unknown preset']:
            old = Project.from_dict(dict(data, preset_name=key, canvas_width=200, canvas_height=100))
            self.assertEqual((old.canvas_width, old.canvas_height), (200, 100))
            self.assertEqual(validate_project_export(old), [])

    def test_save_load_roundtrip_with_store_and_crop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'project.json')
            for key in GOOGLE_PRESETS:
                project = Project(pages=[Page(layers=[ImageLayer(crop_right=.5)])])
                project.set_preset(key)
                for custom in [False, True]:
                    if custom:
                        project.set_custom_size(640, 320)
                    self.assertTrue(save_project_to_json(project, path)[0])
                    loaded, message = load_project_from_json(path)
                    self.assertIsNotNone(loaded, message)
                    self.assertEqual(loaded.to_dict(), project.to_dict())
            # Loading a legacy file infers metadata without rewriting its dimensions.
            data = Project().to_dict()
            for field in ['store', 'device_type', 'orientation']:
                del data[field]
            Path(path).write_text(json.dumps(data))
            loaded, message = load_project_from_json(path)
            self.assertIsNotNone(loaded, message)
            self.assertEqual(loaded.store, 'apple_app_store')
            self.assertEqual((loaded.canvas_width, loaded.canvas_height), (1290, 2796))


class StoreValidationTests(unittest.TestCase):
    def test_google_dimension_boundaries(self):
        for w, h in [(1080, 1920), (1920, 1080), (320, 320), (320, 640),
                     (640, 320), (1920, 3840), (3840, 1920), (3840, 3840)]:
            with self.subTest(size=(w, h)):
                self.assertEqual(validate_store_canvas('google_play', w, h), [])
        for w, h, reason in [(319, 500, '320'), (500, 319, '320'), (3841, 2000, '3840'),
                             (2000, 3841, '3840'), (320, 641, '2:1'), (641, 320, '2:1'),
                             (0, 500, '320'), (320.5, 500, 'integer')]:
            with self.subTest(size=(w, h)):
                self.assertIn(reason, ' '.join(validate_store_canvas('google_play', w, h)))
        self.assertEqual(validate_store_canvas('apple_app_store', 1290, 2796), [])

    def test_invalid_export_does_not_render_create_or_overwrite(self):
        project = Project(preset_name='Custom', store='google_play', canvas_width=319, canvas_height=640)
        with tempfile.TemporaryDirectory() as tmp, patch('core.exporter.render_page') as render:
            output = Path(tmp) / 'existing.png'
            output.write_bytes(b'keep existing file')
            ok, message, dims = export_single_page(project, project.active_page, str(output))
            self.assertFalse(ok)
            self.assertIn('320', message)
            self.assertEqual(output.read_bytes(), b'keep existing file')
            folder = Path(tmp) / 'new_folder'
            results = export_all_pages(project, str(folder))
            self.assertTrue(results)
            self.assertTrue(all(not ok and '320' in msg for _, ok, msg, _ in results))
            self.assertFalse(folder.exists())
            render.assert_not_called()

    def test_google_rgb_exports_and_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Project()
            for key, (w, h, _, _) in GOOGLE_PRESETS.items():
                project.set_preset(key)
                path = Path(tmp) / 'single.png'
                result = export_single_page(project, project.active_page, str(path))
                self.assertTrue(result[0], result[1])
                with Image.open(path) as image:
                    self.assertEqual((image.size, image.mode), ((w, h), 'RGB'))
            project.pages.append(Page(name='Second'))
            results = export_all_pages(project, str(Path(tmp) / 'batch'))
            self.assertEqual(len(results), 2)
            self.assertTrue(all(ok for _, ok, _, _ in results))

    def test_ui_exports_show_reason_before_opening_file_picker(self):
        project = Project(preset_name='Custom', store='google_play', canvas_width=319, canvas_height=600)
        fake = SimpleNamespace(project=project)
        fake._validate_export = lambda: MainWindow._validate_export(fake)
        with patch('ui.main_window.messagebox.showerror') as error, \
             patch('ui.main_window.filedialog.asksaveasfilename') as single, \
             patch('ui.main_window.filedialog.askdirectory') as batch:
            MainWindow.on_export_current(fake)
            MainWindow.on_export_all(fake)
            self.assertEqual(error.call_count, 2)
            self.assertIn('320', error.call_args.args[1])
            single.assert_not_called()
            batch.assert_not_called()


class StoreRegressionTests(unittest.TestCase):
    def test_store_metadata_does_not_change_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = str(Path(tmp) / 'image.png')
            Image.new('RGBA', (200, 300), (40, 100, 180, 200)).save(image_path)
            project = Project(canvas_width=320, canvas_height=640, pages=[Page(layers=[
                ImageLayer(file_path=image_path, x=160, y=350, scale=.8, rotation=12,
                           opacity=.7, crop_right=.6, frame=FrameConfig()),
                TextLayer(text='Store screenshot', x=160, y=30, font_size=24)])])
            state = np.random.get_state()
            self.addCleanup(np.random.set_state, state)
            np.random.seed(42)
            apple = render_page(project, project.active_page)
            project.set_custom_size(320, 640)
            project.set_store('google_play')
            np.random.seed(42)
            google = render_page(project, project.active_page)
            self.assertIsNone(ImageChops.difference(apple, google).convert('RGB').getbbox())

    def test_duplicate_page_preserves_profile_and_crop(self):
        project = Project(pages=[Page(layers=[ImageLayer(crop_right=.6)])])
        project.set_preset('Google Play Tablet Landscape')
        fake = SimpleNamespace(get_project=lambda: project, refresh=Mock(), on_page_changed=Mock())
        PageManagerBar.duplicate_current_page(fake)
        self.assertEqual(project.active_page.layers[0].crop_right, .6)
        self.assertNotEqual(project.pages[0].id, project.pages[1].id)
        self.assertNotEqual(project.pages[0].layers[0].id, project.pages[1].layers[0].id)
        self.assertEqual((project.store, project.device_type, project.orientation), ('google_play', 'tablet', 'landscape'))

    def test_templates_preserve_profile(self):
        project = Project()
        project.set_preset('Google Play Phone Landscape')
        fake = SimpleNamespace(project=project, refresh_all=Mock())
        with patch('ui.main_window.messagebox.askyesno', return_value=True):
            for template in TEMPLATE_FACTORIES:
                MainWindow.on_apply_template(fake, template)
                self.assertEqual(project.preset_name, 'Google Play Phone Landscape')
                self.assertEqual((project.canvas_width, project.canvas_height), (1920, 1080))

    def test_custom_size_ui_keeps_google_store_in_both_panels(self):
        for panel in [CanvasSidebar, PropertyPanel]:
            project = Project()
            project.set_preset('Google Play Phone Portrait')
            fake = SimpleNamespace(get_project=lambda: project, canvas_w_var=Mock(), canvas_h_var=Mock(),
                                   _refresh_canvas_profile=Mock(), on_change=Mock())
            fake.canvas_w_var.get.return_value = '319'
            fake.canvas_h_var.get.return_value = '500'
            panel._apply_custom_canvas_size(fake)
            self.assertEqual((project.preset_name, project.store), ('Custom', 'google_play'))
            self.assertTrue(validate_project_export(project))


if __name__ == '__main__':
    unittest.main()
