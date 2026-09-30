import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from unittest.mock import Mock, patch

from PIL import Image, ImageChops
from core.models import ImageLayer, FrameConfig, Project, Page
from core.image_geometry import get_image_layer_crop_box, get_image_layer_source_dimensions
from core.renderer import render_image_layer, render_page, get_cached_image
from core.project import save_project_to_json, load_project_from_json
from core.exporter import export_single_page
from ui.canvas_view import CanvasView
from ui.layer_sidebar import LayerSidebar
from ui.property_panel import PropertyPanel
from ui.crop_dialog import CropDialog


class ImageCropTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'source.png'
        image = Image.new('RGBA', (200, 100), 'red')
        image.paste('blue', (100, 0, 200, 100))
        image.save(self.path)
        self.original = self.path.read_bytes()
        self.layer = ImageLayer(file_path=str(self.path), x=150, y=150,
                                frame=FrameConfig(enabled=False), crop_right=0.5)
        self.project = Project(canvas_width=300, canvas_height=300,
                               pages=[Page(layers=[self.layer])])

    def crop(self, layer):
        return layer.crop_left, layer.crop_top, layer.crop_right, layer.crop_bottom

    def test_defaults_and_legacy_json(self):
        self.assertEqual(self.crop(ImageLayer()), (0, 0, 1, 1))
        data = self.project.to_dict()
        for key in list(data['pages'][0]['layers'][0]):
            if key.startswith('crop_'):
                del data['pages'][0]['layers'][0][key]
        path = Path(self.tmp.name) / 'legacy.json'
        path.write_text(json.dumps(data))
        project, message = load_project_from_json(str(path))
        self.assertIsNotNone(project, message)
        self.assertEqual(self.crop(project.active_page.layers[0]), (0, 0, 1, 1))

    def test_save_reload_and_source_unchanged(self):
        self.layer.crop_left, self.layer.crop_top, self.layer.crop_bottom = .1, .2, .8
        path = str(Path(self.tmp.name) / 'project.json')
        self.assertTrue(save_project_to_json(self.project, path)[0])
        loaded, message = load_project_from_json(path)
        self.assertIsNotNone(loaded, message)
        self.assertEqual(self.crop(loaded.active_page.layers[0]), self.crop(self.layer))
        render_page(loaded, loaded.active_page)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_crop_box_and_dimensions(self):
        self.assertEqual(get_image_layer_crop_box(self.layer, (200, 100)), (0, 0, 100, 100))
        self.assertEqual(get_image_layer_source_dimensions(self.layer, (200, 100)), (100, 100))
        self.layer.crop_left, self.layer.crop_right = .8, .2
        self.layer.crop_top, self.layer.crop_bottom = -10, 20
        self.assertEqual(get_image_layer_crop_box(self.layer, (200, 100)), (40, 0, 160, 100))

    def test_invalid_and_tiny_crops(self):
        for left, right in [(1, 1), (.5, .5000001), (-2, -1), (2, 3), (float('nan'), float('inf')), (None, 'bad')]:
            with self.subTest(left=left, right=right):
                self.layer.crop_left, self.layer.crop_right = left, right
                l, t, r, b = get_image_layer_crop_box(self.layer, (200, 100))
                self.assertTrue(0 <= l < r <= 200)
                self.assertGreaterEqual(r-l, 2)
                self.assertGreaterEqual(b-t, 1)
        self.assertEqual(get_image_layer_crop_box(ImageLayer(), (1, 1)), (0, 0, 1, 1))

    def test_render_and_canvas_geometry(self):
        image, x, y = render_image_layer(self.layer, 300, 300)
        self.assertEqual(image.size, (240, 240))
        self.assertEqual(image.getpixel((120, 120)), (255, 0, 0, 255))
        view = SimpleNamespace(get_project=lambda: self.project)
        self.assertEqual(CanvasView.get_layer_bbox_canvas(view, self.layer), (30, 30, 270, 270))
        self.layer.reset_crop()
        self.assertEqual(render_image_layer(self.layer, 300, 300)[0].size, (240, 120))
        self.assertEqual(CanvasView.get_layer_bbox_canvas(view, self.layer), (30, 90, 270, 210))
        self.assertEqual(get_cached_image(str(self.path)).size, (200, 100))

    def test_frame_opacity_rotation_and_shadow_use_crop(self):
        self.layer.frame = FrameConfig(corner_radius=20, border_width=2)
        self.layer.opacity = .5
        image, _, _ = render_image_layer(self.layer, 300, 300)
        self.assertEqual(image.size, (240, 240))
        self.assertEqual(image.getpixel((120, 120))[3], 127)
        self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.layer.rotation = 90
        self.assertEqual(render_image_layer(self.layer, 300, 300)[0].size, (240, 240))
        with patch('core.renderer.create_shadow_image', return_value=(Image.new('RGBA', (1, 1)), 0, 0)) as shadow:
            render_page(self.project, self.project.active_page)
            self.assertEqual(shadow.call_args.args[:2], (240, 240))

    def test_export_matches_preview(self):
        output = str(Path(self.tmp.name) / 'export.png')
        state = np.random.get_state()
        self.addCleanup(np.random.set_state, state)
        np.random.seed(7)
        self.assertTrue(export_single_page(self.project, self.project.active_page, output)[0])
        np.random.seed(7)
        with Image.open(output) as exported:
            self.assertEqual(exported.mode, 'RGB')
            preview = render_page(self.project, self.project.active_page, scale_factor=.5, show_guides=False).convert('RGB')
            expected = exported.convert("RGBA").resize(preview.size, Image.Resampling.LANCZOS).convert("RGB")
            self.assertIsNone(ImageChops.difference(preview, expected).getbbox())

    def test_panel_reset_and_replace(self):
        for panel, module in [(LayerSidebar, 'ui.layer_sidebar'), (PropertyPanel, 'ui.property_panel')]:
            fake = SimpleNamespace(on_change=Mock(), refresh=Mock())
            self.layer.crop_right = .5
            panel._reset_image_crop(fake, self.layer)
            self.assertEqual(self.crop(self.layer), (0, 0, 1, 1))
            self.layer.crop_right = .5
            with patch(module + '.filedialog.askopenfilename', return_value=''):
                panel._replace_image_layer_file(fake, self.layer)
            self.assertEqual(self.layer.crop_right, .5)
            with patch(module + '.filedialog.askopenfilename', return_value=str(self.path)):
                panel._replace_image_layer_file(fake, self.layer)
            self.assertEqual(self.crop(self.layer), (0, 0, 1, 1))

    def test_dialog_move_and_resize_stay_within_source(self):
        fake = SimpleNamespace(source=Image.new('RGBA', (200, 100)), sx=1, sy=1,
                               _draw=Mock(), _drag=('move', 0, 0, [20, 10, 120, 80]))
        CropDialog._motion(fake, SimpleNamespace(x=500, y=-500))
        self.assertEqual(fake.box, [100, 0, 200, 70])
        fake._drag = ('nw', 0, 0, [20, 10, 120, 80])
        CropDialog._motion(fake, SimpleNamespace(x=500, y=500))
        self.assertEqual(fake.box, [118, 79, 120, 80])
        fake._drag = ('se', 0, 0, [20, 10, 120, 80])
        CropDialog._motion(fake, SimpleNamespace(x=500, y=500))
        self.assertEqual(fake.box, [20, 10, 200, 100])

    def test_dialog_draft_reset_and_apply(self):
        fake = SimpleNamespace(layer=self.layer, source=Image.new('RGBA', (200, 100)),
                               box=[20, 10, 180, 80], _draw=Mock(), destroy=Mock(), on_apply=Mock())
        CropDialog.reset(fake)
        self.assertEqual(self.crop(self.layer), (0, 0, .5, 1))
        self.assertEqual(fake.box, [0, 0, 200, 100])
        fake.box = [20, 10, 180, 80]
        CropDialog.apply(fake)
        self.assertEqual(self.crop(self.layer), (.1, .1, .9, .8))
        fake.on_apply.assert_called_once()


if __name__ == '__main__':
    unittest.main()
