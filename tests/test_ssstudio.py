import os
import unittest
import numpy as np
from PIL import Image, ImageDraw

from core.models import Project, Page, ImageLayer, TextLayer, FrameConfig, GradientConfig, CANVAS_PRESETS
from core.renderer import render_page, create_gradient_background
from core.exporter import export_single_page, export_all_pages
from core.project import save_project_to_json, load_project_from_json
from core.templates import TEMPLATE_FACTORIES, apply_theme_to_page, THEME_LEMEMO_LUXURY


class TestSSStudio(unittest.TestCase):
    def setUp(self):
        self.test_dir = "/tmp/ssstudio_test"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create a sample screenshot image
        self.sample_img_path = os.path.join(self.test_dir, "sample_screen.png")
        sample_img = Image.new("RGBA", (1170, 2532), (30, 30, 45, 255))
        draw = ImageDraw.Draw(sample_img)
        draw.rectangle([40, 80, 1130, 300], fill=(50, 50, 80, 255))
        draw.text((100, 150), "Sample App Screen", fill="white")
        sample_img.save(self.sample_img_path)

    def test_gradient_background(self):
        cfg = GradientConfig()
        cfg.apply_preset("luxury_black")
        img = create_gradient_background(400, 800, cfg)
        self.assertEqual(img.size, (400, 800))
        self.assertEqual(img.mode, "RGBA")

    def test_render_templates(self):
        for name, factory in TEMPLATE_FACTORIES.items():
            if name == "Double Device":
                page = factory(600, 1200, self.sample_img_path, self.sample_img_path)
            elif name == "Free Layout":
                page = factory(600, 1200)
            else:
                page = factory(600, 1200, self.sample_img_path)
            
            proj = Project(canvas_width=600, canvas_height=1200, pages=[page])
            rendered = render_page(proj, page, show_guides=True)
            self.assertEqual(rendered.size, (600, 1200))

    def test_save_and_load_project(self):
        proj = Project(preset_name="iPhone 6.9-inch", canvas_width=1290, canvas_height=2796)
        p1 = TEMPLATE_FACTORIES["Headline Top"](1290, 2796, self.sample_img_path)
        proj.pages = [p1]

        save_path = os.path.join(self.test_dir, "test_proj.json")
        ok, msg = save_project_to_json(proj, save_path)
        self.assertTrue(ok)

        loaded_proj, msg2 = load_project_from_json(save_path)
        self.assertIsNotNone(loaded_proj)
        self.assertEqual(loaded_proj.canvas_width, 1290)
        self.assertEqual(len(loaded_proj.pages), 1)
        self.assertEqual(len(loaded_proj.pages[0].layers), len(p1.layers))

    def test_export_single_and_batch(self):
        proj = Project(preset_name="iPhone 6.9-inch", canvas_width=1290, canvas_height=2796)
        p1 = TEMPLATE_FACTORIES["Headline Top"](1290, 2796, self.sample_img_path)
        p1.name = "people"
        p2 = TEMPLATE_FACTORIES["Split"](1290, 2796, self.sample_img_path)
        p2.name = "memory"
        proj.pages = [p1, p2]

        out_single = os.path.join(self.test_dir, "single.png")
        ok, msg, dims = export_single_page(proj, p1, out_single)
        self.assertTrue(ok)
        self.assertEqual(dims, (1290, 2796))
        self.assertTrue(os.path.exists(out_single))

        # Batch
        batch_dir = os.path.join(self.test_dir, "batch_out")
        results = export_all_pages(proj, batch_dir)
        self.assertEqual(len(results), 2)
        for fname, s_ok, _, s_dims in results:
            self.assertTrue(s_ok)
            self.assertEqual(s_dims, (1290, 2796))
            self.assertTrue(os.path.exists(os.path.join(batch_dir, fname)))


if __name__ == "__main__":
    unittest.main()
