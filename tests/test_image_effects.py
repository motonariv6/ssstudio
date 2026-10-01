import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from core.models import ImageEffectsConfig, ImageLayer, FrameConfig, Project, Page
from core.image_effects import apply_bottom_fade, build_bottom_fade_mask, create_alpha_shadow
from core.renderer import render_image_layer, render_page
from core.project import save_project_to_json, load_project_from_json
from core.exporter import export_single_page, export_all_pages
from core.panorama import PanoramaConfig


class ImageEffectsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'source.png'
        self.source = Image.new('RGBA', (80, 100), (255, 0, 0, 128))
        self.source.paste((0, 0, 0, 0), (0, 0, 20, 100))
        self.source.save(self.path)
        self.layer = ImageLayer(file_path=str(self.path), x=150, y=150,
                                frame=FrameConfig(enabled=False))
        self.project = Project(preset_name='Custom', canvas_width=300, canvas_height=400,
                               pages=[Page(layers=[self.layer])])

    def test_defaults_legacy_roundtrip_and_duplicate(self):
        config = self.layer.effects
        self.assertFalse(config.fade_enabled)
        self.assertFalse(config.shadow_enabled)
        legacy = self.layer.to_dict()
        del legacy['effects']
        self.assertEqual(ImageLayer.from_dict(legacy).effects, config)
        self.layer.effects = ImageEffectsConfig(True, 'bottom', .3, .9, True, .6, 12, -20, 30, '#223344')
        target = str(Path(self.tmp.name) / 'project.json')
        self.assertTrue(save_project_to_json(self.project, target)[0])
        loaded, message = load_project_from_json(target)
        self.assertIsNotNone(loaded, message)
        self.assertEqual(loaded.active_page.layers[0].effects, self.layer.effects)
        duplicate = copy.deepcopy(self.project.active_page)
        duplicate.layers[0].effects.fade_start = .2
        self.assertEqual(self.layer.effects.fade_start, .3)

    def test_fade_disabled_and_alpha(self):
        self.assertEqual(apply_bottom_fade(self.source, ImageEffectsConfig()).tobytes(), self.source.tobytes())
        faded = apply_bottom_fade(self.source, ImageEffectsConfig(fade_enabled=True, fade_start=.5))
        self.assertEqual(faded.getpixel((40, 0)), (255, 0, 0, 128))
        self.assertEqual(faded.getpixel((40, 99))[3], 0)
        self.assertEqual(faded.getpixel((0, 60))[3], 0)
        mask = build_bottom_fade_mask(self.source.size, .5, 1)
        self.assertEqual(faded.getpixel((40, 75))[3], 128 * mask.getpixel((40, 75)) // 255)
        self.assertEqual(self.source.getpixel((40, 99))[3], 128)

    def test_invalid_values(self):
        for start, end in [(1, 1), (4, -2), (float('nan'), float('inf')), (None, 'bad')]:
            config = ImageEffectsConfig(fade_start=start, fade_end=end)
            config.normalize()
            self.assertTrue(0 <= config.fade_start < config.fade_end <= 1)
            self.assertEqual(build_bottom_fade_mask((10, 10), start, end).getpixel((5, 9)), 0)

    def test_shadow_shape_opacity_offset_blur_and_disabled(self):
        self.assertIsNone(create_alpha_shadow(self.source, ImageEffectsConfig()))
        config = ImageEffectsConfig(shadow_enabled=True, shadow_blur=0, shadow_opacity=.5,
                                    shadow_offset_x=-10, shadow_offset_y=20, shadow_color='#123456')
        shadow, x, y = create_alpha_shadow(self.source, config)
        self.assertEqual((x, y), (-10, 20))
        self.assertEqual(shadow.getpixel((40, 30)), (18, 52, 86, 64))
        self.assertEqual(shadow.getpixel((0, 30))[3], 0)
        config.shadow_blur = 8
        blurred, x, y = create_alpha_shadow(self.source, config)
        self.assertGreater(blurred.width, shadow.width)
        self.assertGreater(blurred.getpixel((24 + 19, 24 + 40))[3], 0)
        self.assertLess(blurred.getpixel((24 + 20, 24 + 40))[3], 64)

    def test_disabled_renderer_matches_previous(self):
        # Golden pixels captured from the pre-effects renderer (RGBA PNG fixture).
        expected = {
            (False, 0): 'd7cef4a2b0aaad1ccbe887b7c29358cbcfad6a31ae87f8080fd78e8a99f8d844',
            (False, 17): '018f4d2bc46b9e83f00fc692c2751462385c94dac87d1922492b058e561d5e37',
            (True, 0): 'c8d2c1053e1fa3077dc76b75852e90fadf27bd18bd3a25bee0dd5ac3e56cc1f8',
            (True, 17): 'a89f7fd94434424f255351e0f18ef50724cb756dc5d6d5130dd323c92e145909',
        }
        for frame in [False, True]:
            for rotation in [0, 17]:
                self.layer.frame.enabled = frame
                self.layer.rotation = rotation
                self.layer.opacity = .6
                image, x, y = render_image_layer(self.layer, 300, 400)
                self.assertEqual((x, y), (30, 0) if rotation == 0 else (-9, -29))
                self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(), expected[frame, rotation])

    def test_crop_fade_frame_rotation_and_group_opacity(self):
        self.layer.crop_top = .2
        self.layer.effects = ImageEffectsConfig(fade_enabled=True)
        image, x, y = render_image_layer(self.layer, 300, 400)
        self.assertEqual(image.size, (240, 240))
        self.assertEqual(image.getpixel((120, 239))[3], 0)
        self.layer.effects.shadow_enabled = True
        self.layer.effects.shadow_offset_x = -40
        for frame in [False, True]:
            self.layer.frame.enabled = frame
            for frame_shadow in [False, True]:
                self.layer.frame.shadow_enabled = frame_shadow
                for rotation in [0, 25]:
                    self.layer.rotation = rotation
                    image, x, y = render_image_layer(self.layer, 300, 400)
                    self.assertGreater(image.width, 240)
                    self.assertAlmostEqual(x + image.width / 2, 150, delta=1)
                    self.assertAlmostEqual(y + image.height / 2, 150, delta=1)
                    self.assertEqual(render_page(self.project, self.project.active_page).size, (300, 400))
        self.layer.opacity = 0
        self.assertIsNone(render_image_layer(self.layer, 300, 400)[0].getbbox())

    def test_faded_shadow_and_preview_scale(self):
        config = ImageEffectsConfig(fade_enabled=True, shadow_enabled=True, shadow_blur=0,
                                    shadow_offset_x=0, shadow_offset_y=0, shadow_opacity=1)
        faded = apply_bottom_fade(self.source, config)
        shadow, _, _ = create_alpha_shadow(faded, config)
        self.assertEqual(shadow.getchannel('A').tobytes(), faded.getchannel('A').tobytes())
        self.layer.effects = ImageEffectsConfig(shadow_enabled=True)
        full, x, y = render_image_layer(self.layer, 300, 400)
        small, sx, sy = render_image_layer(self.layer, 300, 400, .5)
        self.assertAlmostEqual(small.width * 2, full.width, delta=2)
        self.assertAlmostEqual(sx * 2, x, delta=2)
        self.assertAlmostEqual(sy * 2, y, delta=2)

    def test_panorama_export_continuity_and_source_unchanged(self):
        original = self.path.read_bytes()
        page = self.project.active_page
        page.panorama = PanoramaConfig(enabled=True, screen_count=2)
        self.layer.x = 300
        self.layer.effects = ImageEffectsConfig(fade_enabled=True, shadow_enabled=True)
        with patch('core.renderer.np.random.rand', side_effect=lambda *shape: np.full(shape, .5)):
            workspace = render_page(self.project, page).convert('RGB')
            base = str(Path(self.tmp.name) / 'current.png')
            self.assertTrue(export_single_page(self.project, page, base)[0])
            slices = [Image.open(Path(self.tmp.name) / f'current_{i:02}.png') for i in (1, 2)]
            joined = Image.new('RGB', workspace.size)
            for i, piece in enumerate(slices):
                self.assertEqual(piece.mode, 'RGB')
                joined.paste(piece, (i * 300, 0))
                piece.close()
            self.assertEqual(joined.tobytes(), workspace.tobytes())
            results = export_all_pages(self.project, str(Path(self.tmp.name) / 'all'))
            self.assertEqual(len(results), 2)
            self.assertTrue(all(result[1] for result in results))
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
