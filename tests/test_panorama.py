import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image, ImageChops

from core.models import Project, Page, ImageLayer, TextLayer, FrameConfig, GradientConfig
from core.panorama import PanoramaConfig, get_workspace_geometry
from core.project import save_project_to_json, load_project_from_json
from core.renderer import render_page, render_image_layer, create_gradient_background
from core.exporter import export_single_page, export_all_pages, get_all_output_paths
from ui.canvas_view import CanvasView
from ui.page_manager import PageManagerBar


class PanoramaGeometryTests(unittest.TestCase):
    def test_single_and_panorama_sizes_and_exact_partition(self):
        project = Project(canvas_width=321, canvas_height=640)
        page = project.active_page
        for count in [1, 2, 3, 4]:
            page.panorama = PanoramaConfig(enabled=count > 1, screen_count=count)
            geometry = get_workspace_geometry(project, page)
            self.assertEqual((geometry.width, geometry.height), (321 * count, 640))
            expected = tuple((i*321, 0, (i+1)*321, 640) for i in range(count))
            self.assertEqual(geometry.screen_rectangles, expected)
            self.assertEqual(geometry.slice_boxes, expected)
            self.assertEqual(geometry.boundaries, tuple(321*i for i in range(1, count)))
            covered = [x for l, _, r, _ in geometry.slice_boxes for x in range(l, r)]
            self.assertEqual(covered, list(range(geometry.width)))

    def test_legacy_m1_m2_project_and_panorama_roundtrip(self):
        project = Project(pages=[Page(layers=[ImageLayer(crop_left=.2, crop_right=.8)])])
        project.set_preset('Google Play Phone Landscape')
        data = project.to_dict()
        del data['pages'][0]['panorama']
        loaded = Project.from_dict(data)
        self.assertFalse(loaded.active_page.panorama.enabled)
        self.assertEqual(loaded.active_page.panorama.screen_count, 1)
        self.assertEqual(loaded.store, 'google_play')
        self.assertEqual(loaded.active_page.layers[0].crop_left, .2)
        loaded.active_page.panorama = PanoramaConfig(True, 3)
        loaded.pages.append(Page(panorama=PanoramaConfig(True, 2)))
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'panorama.json')
            self.assertTrue(save_project_to_json(loaded, path)[0])
            restored, message = load_project_from_json(path)
            self.assertIsNotNone(restored, message)
            self.assertEqual(restored.to_dict(), loaded.to_dict())

    def test_unsupported_settings_rejected(self):
        for data in [{'enabled': True, 'screen_count': n} for n in [0, 1, 5, 2.5, True]] + [
            {'enabled': True, 'screen_count': 2, 'direction': 'vertical'}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                PanoramaConfig.from_dict(data)

    def test_mode_and_profile_switches_preserve_layers(self):
        layer = ImageLayer(x=1400, y=300, crop_right=.5, scale=.8)
        project = Project(pages=[Page(layers=[layer])])
        before = layer.to_dict()
        page = project.active_page
        page.panorama = PanoramaConfig(True, 3)
        project.set_preset('Google Play Phone Portrait')
        self.assertEqual(get_workspace_geometry(project, page).width, 3240)
        project.set_preset('iPhone 6.9-inch')
        self.assertEqual(get_workspace_geometry(project, page).width, 3870)
        page.panorama.enabled = False
        self.assertEqual(get_workspace_geometry(project, page).width, 1290)
        self.assertEqual(before, layer.to_dict())

    def test_duplicate_page_keeps_independent_panorama(self):
        project = Project(pages=[Page(panorama=PanoramaConfig(True, 3))])
        fake = SimpleNamespace(get_project=lambda: project, refresh=Mock(), on_page_changed=Mock())
        PageManagerBar.duplicate_current_page(fake)
        self.assertEqual(project.active_page.panorama.screen_count, 3)
        project.active_page.panorama.screen_count = 2
        self.assertEqual(project.pages[0].panorama.screen_count, 3)


class PanoramaRenderExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.source = self.folder / 'source.png'
        image = Image.new('RGBA', (240, 240), 'red')
        image.paste('blue', (120, 0, 240, 240))
        image.save(self.source)
        self.layer = ImageLayer(file_path=str(self.source), x=320, y=320, crop_right=.5,
                                scale=.75, frame=FrameConfig(enabled=False))
        self.page = Page(name='feature', panorama=PanoramaConfig(True, 3),
                         background=GradientConfig(color_start='#000000', color_end='#FFFFFF',
                                                   direction='horizontal', intensity=1, spotlight_enabled=False))
        self.project = Project(preset_name='Custom', store='google_play', canvas_width=320,
                               canvas_height=640, pages=[self.page])
        state = np.random.get_state()
        self.addCleanup(np.random.set_state, state)

    def test_full_render_continuous_gradient_and_no_guides(self):
        image = render_page(self.project, self.page)
        self.assertEqual(image.size, (960, 640))
        row = np.asarray(image)[400, :, 0].astype(int)
        self.assertLess(row[319], row[640])
        self.assertLess(abs(row[320]-row[319]), 3)
        self.assertLess(abs(row[640]-row[639]), 3)
        self.assertLess(row[0], 2)
        self.assertGreater(row[-1], 252)
        np.random.seed(9)
        clean = render_page(self.project, self.page)
        np.random.seed(9)
        guides = render_page(self.project, self.page, show_guides=True)
        self.assertIsNotNone(ImageChops.difference(clean, guides).convert('RGB').getbbox())

    def test_cropped_image_crosses_boundary_with_unchanged_scale(self):
        self.page.layers = [self.layer]
        image = render_page(self.project, self.page)
        for x in [319, 320]:
            self.assertEqual(image.getpixel((x, 320)), (255, 0, 0, 255))
        fake = SimpleNamespace(get_project=lambda: self.project)
        bbox = CanvasView.get_layer_bbox_canvas(fake, self.layer)
        self.assertEqual(bbox, (224, 128, 416, 512))
        self.page.panorama.enabled = False
        self.assertEqual(CanvasView.get_layer_bbox_canvas(fake, self.layer), bbox)

    def test_text_crosses_boundary(self):
        self.page.background = GradientConfig(color_start='#000000', color_end='#000000', spotlight_enabled=False)
        self.page.layers = [TextLayer(text='MMMM MMMM', x=320, y=100, font_size=48, max_width=620)]
        pixels = np.asarray(render_page(self.project, self.page))
        for left, right in [(200, 320), (320, 440)]:
            self.assertGreater(np.count_nonzero(pixels[100:180, left:right, 0] > 200), 100)

    def test_preview_allocates_scaled_buffers_and_preserves_model(self):
        self.page.layers = [self.layer, TextLayer(text='Across screens', x=320, y=20, font_size=40)]
        self.layer.frame = FrameConfig()
        self.layer.rotation = 15
        self.layer.opacity = .6
        before = self.project.to_dict()
        with patch('core.renderer.create_gradient_background', wraps=create_gradient_background) as bg, \
             patch('core.renderer.render_image_layer', wraps=render_image_layer) as image:
            preview = render_page(self.project, self.page, scale_factor=.25)
            self.assertEqual(preview.size, (240, 160))
            self.assertEqual(bg.call_args.args[:2], (240, 160))
            self.assertEqual(image.call_args.kwargs['render_scale'], .25)
        self.assertEqual(self.project.to_dict(), before)

    def test_preview_image_geometry_matches_downsampled_export(self):
        self.page.layers = [self.layer]
        np.random.seed(1)
        full = render_page(self.project, self.page).resize((240, 160), Image.Resampling.LANCZOS)
        preview = render_page(self.project, self.page, scale_factor=.25)
        # Different resolution dithering/filter edges can differ slightly; the
        # red crop content must have the same centroid and occupied rectangle.
        def red_bounds(image):
            pixels = np.asarray(image)
            ys, xs = np.where((pixels[:,:,0] > 240) & (pixels[:,:,1] < 10))
            return min(xs), min(ys), max(xs), max(ys)
        a, b = red_bounds(full), red_bounds(preview)
        for x, y in zip(a, b):
            self.assertLessEqual(abs(x-y), 1)

    def test_exports_reassemble_exact_full_render(self):
        self.page.layers = [self.layer, TextLayer(text='MMMM MMMM', x=320, y=40, font_size=48)]
        for count in [2, 3, 4]:
            self.page.panorama.screen_count = count
            np.random.seed(27)
            expected = render_page(self.project, self.page).convert('RGB')
            base = self.folder / f'count{count}' / 'feature.png'
            np.random.seed(27)
            with patch('core.exporter.render_page', wraps=render_page) as render:
                ok, message, dims = export_single_page(self.project, self.page, str(base))
                self.assertTrue(ok, message)
                render.assert_called_once()
                self.assertFalse(render.call_args.kwargs['show_guides'])
            self.assertEqual(dims, (320, 640))
            paths = sorted(base.parent.glob('*.png'))
            self.assertEqual(len(paths), count)
            joined = Image.new('RGB', expected.size)
            for index, path in enumerate(paths):
                with Image.open(path) as piece:
                    self.assertEqual((piece.mode, piece.size), ('RGB', (320, 640)))
                    joined.paste(piece, (index*320, 0))
            self.assertIsNone(ImageChops.difference(joined, expected).getbbox())

    def test_mixed_page_export_all_order_and_collisions(self):
        self.page.name = 'people'
        self.project.pages.extend([Page(name='people', panorama=PanoramaConfig(True, 2)), Page(name='single')])
        target = self.folder / 'batch'
        expected = ['01_people_01.png', '01_people_02.png', '01_people_03.png',
                    '02_people_01.png', '02_people_02.png', '03_single.png']
        self.assertEqual([Path(p).name for p in get_all_output_paths(self.project, str(target))], expected)
        results = export_all_pages(self.project, str(target))
        self.assertEqual([name for name, _, _, _ in results], expected)
        self.assertTrue(all(ok for _, ok, _, _ in results))
        before = {p.name: p.read_bytes() for p in target.iterdir()}
        with patch('core.exporter.render_page') as render:
            failed = export_all_pages(self.project, str(target))
            self.assertTrue(all(not ok and 'already exist' in msg for _, ok, msg, _ in failed))
            render.assert_not_called()
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
        self.assertTrue(all(ok for _, ok, _, _ in export_all_pages(self.project, str(target), overwrite=True)))

    def test_current_collision_preflight_writes_no_siblings(self):
        existing = self.folder / 'feature_02.png'
        existing.write_bytes(b'preserve')
        ok, message, _ = export_single_page(self.project, self.page, str(self.folder / 'feature.png'))
        self.assertFalse(ok)
        self.assertIn('already exist', message)
        self.assertEqual(list(self.folder.glob('feature*')), [existing])
        self.assertEqual(existing.read_bytes(), b'preserve')

    def test_google_validates_slices_not_workspace(self):
        self.project.set_custom_size(1080, 1920)
        self.page.panorama.screen_count = 4
        # Workspace exceeds 3840 but each screenshot is a valid Google profile.
        with patch('core.exporter.render_page', return_value=Image.new('RGBA', (4320,1920),'red')):
            self.assertTrue(export_single_page(self.project,self.page,str(self.folder/'valid.png'))[0])
        self.project.set_custom_size(319, 640)
        with patch('core.exporter.render_page') as render:
            ok, reason, _ = export_single_page(self.project,self.page,str(self.folder/'invalid.png'))
            self.assertFalse(ok)
            self.assertIn('320',reason)
            render.assert_not_called()
        self.assertFalse(list(self.folder.glob('invalid*')))

    def test_single_keeps_exact_filename_dimensions_and_overwrite(self):
        self.page.panorama.enabled = False
        path = self.folder / 'single.png'
        path.write_bytes(b'existing')
        result = export_single_page(self.project, self.page, str(path))
        self.assertTrue(result[0],result[1])
        with Image.open(path) as image:
            self.assertEqual(image.size,(320,640))
        self.assertFalse(list(self.folder.glob('single_*')))


if __name__ == '__main__':
    unittest.main()
