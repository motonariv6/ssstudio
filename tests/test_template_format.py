import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from core.models import Project, Page, ImageLayer, TextLayer, FrameConfig, ImageEffectsConfig
from core.panorama import PanoramaConfig
from core.template_format import (TemplateError, MAX_MANIFEST_BYTES, validate_manifest,
    template_from_page, export_template_package, load_template_package,
    apply_template_to_page, template_compatibility_warnings, render_template_preview)
from core.project import save_project_to_json, load_project_from_json
from core.exporter import export_single_page
from core.templates import TEMPLATE_FACTORIES
from ui.main_window import MainWindow
from ui.layer_sidebar import LayerSidebar
from ui.property_panel import PropertyPanel


class TemplateFormatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'private-screenshot.png'
        Image.new('RGB', (100, 200), '#ff00ff').save(self.source)
        self.original = self.source.read_bytes()
        self.image = ImageLayer(name='Hero Screenshot', file_path=str(self.source), x=290, y=310,
            crop_left=.1, crop_top=.2, crop_right=.9, crop_bottom=.85, rotation=12, scale=.7,
            frame=FrameConfig(border_width=3, shadow_blur=20),
            effects=ImageEffectsConfig(fade_enabled=True, fade_start=.4, fade_end=.9,
                                      shadow_enabled=True, shadow_offset_x=-25, shadow_color='#112233'))
        self.text = TextLayer(text='Reusable headline', name='Headline', font_family='Helvetica',
            font_size=38, color='#334455', x=450, y=90, max_width=270, line_spacing=1.4,
            letter_spacing=2, font_weight='bold', align='right')
        self.page = Page(name='Working Page', layers=[self.image, self.text])
        self.project = Project(preset_name='Custom', canvas_width=300, canvas_height=600, pages=[self.page])
        self.manifest = template_from_page(self.project, self.page, 'Minimal Dark', 'Reusable layout',
                                           'Author', ['minimal', 'dark']).to_dict()

    def test_manifest_metadata_defaults_and_unknown_fields(self):
        self.manifest['future'] = {'anything': True}
        self.manifest['content']['layers'][0]['future'] = 'ignored'
        loaded = validate_manifest(self.manifest)
        self.assertEqual(loaded.manifest['format'], 'ssstudio-template')
        self.assertEqual(loaded.manifest['version'], 1)
        self.assertEqual(loaded.manifest['id'], self.manifest['id'])
        self.assertEqual(loaded.manifest['tags'], ['minimal', 'dark'])
        self.assertNotIn('future', loaded.to_dict())
        self.assertNotIn('future', loaded.manifest['content']['layers'][0])
        minimal = copy.deepcopy(self.manifest)
        minimal['content']['layers'] = [{'layer_type': 'image'}, {'layer_type': 'text'}]
        page = validate_manifest(minimal).create_page()
        self.assertFalse(page.layers[0].effects.fade_enabled)
        self.assertEqual(page.layers[0].file_path, '')

    def test_missing_required_fields(self):
        for key in ('format', 'version', 'id', 'name', 'description', 'author', 'tags', 'store',
                    'screen_count', 'target', 'content'):
            with self.subTest(key=key):
                data = copy.deepcopy(self.manifest)
                del data[key]
                with self.assertRaisesRegex(TemplateError, 'Missing required field'):
                    validate_manifest(data)

    def test_invalid_format_versions_and_layer_types(self):
        for key, value in [('format', 'project'), ('version', 2), ('version', True), ('version', 0),
                           ('store', 'other'), ('name', ''), ('tags', 'dark'), ('screen_count', 0)]:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.manifest)
                data[key] = value
                with self.assertRaises(TemplateError):
                    validate_manifest(data)
        self.manifest['content']['layers'][0]['layer_type'] = 'python-plugin'
        with self.assertRaisesRegex(TemplateError, 'Unsupported layer type'):
            validate_manifest(self.manifest)

    def test_invalid_numeric_types_crop_effects_and_colors(self):
        for field, value in [('x', float('nan')), ('y', float('inf')), ('scale', 'bad'),
                             ('visible', 'yes'), ('crop_left', -.1), ('crop_right', .05),
                             ('opacity', 3)]:
            with self.subTest(field=field):
                data = copy.deepcopy(self.manifest)
                data['content']['layers'][0][field] = value
                with self.assertRaises(TemplateError):
                    validate_manifest(data)
        for field, value in [('fade_end', .1), ('fade_direction', 'top'), ('shadow_blur', -1),
                             ('shadow_opacity', 2), ('shadow_offset_x', 200), ('shadow_color', 'invalid')]:
            with self.subTest(field=field):
                data = copy.deepcopy(self.manifest)
                data['content']['layers'][0]['effects'][field] = value
                with self.assertRaises(TemplateError):
                    validate_manifest(data)
        for value in (None, [], 'bad'):
            data = copy.deepcopy(self.manifest)
            data['content']['layers'][0]['frame'] = value
            with self.assertRaises(TemplateError):
                validate_manifest(data)

    def test_invalid_workspace_and_resource_limits(self):
        for count in (0, 1, 5, True):
            data = copy.deepcopy(self.manifest)
            data['content']['panorama'] = {'enabled': True, 'screen_count': count}
            with self.assertRaises(TemplateError):
                validate_manifest(data)
        data = copy.deepcopy(self.manifest)
        data['target']['canvas_width'] = 8192
        data['target']['canvas_height'] = 8192
        with self.assertRaisesRegex(TemplateError, 'million pixels'):
            validate_manifest(data)
        data = copy.deepcopy(self.manifest)
        data['content']['layers'] = [{'layer_type': 'text'}] * 201
        with self.assertRaises(TemplateError):
            validate_manifest(data)

    def test_export_is_distinct_portable_and_non_destructive(self):
        before = self.project.to_dict()
        self.image.file_path = '/Users/private-person/Secret/App.png'
        package = self.root / 'package'
        template = export_template_package(self.project, self.page, package, 'Layout')
        raw = (package / 'template.json').read_text()
        self.assertNotIn('/Users/', raw)
        self.assertNotIn('file_path', raw)
        self.assertNotIn('original_width', raw)
        self.assertEqual(sorted(p.name for p in package.iterdir()), ['preview.png', 'template.json'])
        loaded = load_template_package(package)
        self.assertEqual(loaded.to_dict(), template.to_dict())
        self.assertNotIn('pages', loaded.to_dict())
        self.image.file_path = str(self.source)
        self.assertEqual(self.project.to_dict(), before)
        self.assertEqual(self.source.read_bytes(), self.original)
        with Image.open(package / 'preview.png') as preview:
            self.assertEqual(preview.mode, 'RGB')
            self.assertLessEqual(preview.width, 960)
            self.assertLessEqual(preview.height, 640)

    def test_preview_never_loads_screenshot_and_contains_no_guides(self):
        template = validate_manifest(self.manifest)
        with patch('core.renderer.get_cached_image', side_effect=AssertionError('Source access forbidden')), \
             patch('core.renderer.draw_preview_guides', side_effect=AssertionError('Guides forbidden')):
            preview = render_template_preview(template)
        self.assertIsInstance(preview, Image.Image)
        self.assertNotIn((255, 0, 255), {color for count, color in preview.getcolors(preview.width * preview.height)})

    def test_image_layout_crop_effects_frame_text_and_layer_order_roundtrip(self):
        template = validate_manifest(self.manifest)
        recreated = template.create_page()
        self.assertEqual([layer.layer_type for layer in recreated.layers], ['image', 'text'])
        image, text = recreated.layers
        self.assertEqual((image.x, image.y, image.scale, image.rotation), (290, 310, .7, 12))
        self.assertEqual((image.crop_left, image.crop_top, image.crop_right, image.crop_bottom), (.1, .2, .9, .85))
        self.assertEqual(image.effects, self.image.effects)
        self.assertEqual(image.frame, self.image.frame)
        self.assertEqual(image.file_path, '')
        self.assertTrue(image.placeholder_id)
        self.assertEqual(image.placeholder_label, 'Hero Screenshot')
        original_text = self.text.to_dict()
        original_text.pop('id')
        new_text = text.to_dict()
        new_text.pop('id')
        self.assertEqual(new_text, original_text)
        self.assertNotEqual(image.id, template.create_page().layers[0].id)

    def test_single_panorama_two_three_four_and_store_profiles(self):
        for store in ('apple_app_store', 'google_play'):
            for count in (1, 2, 3, 4):
                with self.subTest(store=store, count=count):
                    self.project.store = store
                    self.page.panorama = PanoramaConfig(enabled=count > 1, screen_count=count)
                    destination = self.root / f'{store}-{count}'
                    export_template_package(self.project, self.page, destination, 'Portable')
                    template = load_template_package(destination / 'template.json')
                    target = Page(name='Keep Name')
                    target_id = target.id
                    apply_template_to_page(template, target)
                    self.assertEqual(target.panorama, self.page.panorama)
                    self.assertEqual(template.manifest['store'], store)
                    self.assertEqual(template.manifest['screen_count'], count)
                    self.assertEqual((target.name, target.id), ('Keep Name', target_id))
                    self.assertEqual(target.layers[0].x, 290)
                    self.assertEqual(target.layers[1].x, 450)

    def test_apply_does_not_change_project_settings_or_other_pages(self):
        target = Project(preset_name='Google Play Phone Landscape', pages=[Page(), Page()])
        other = target.pages[1].to_dict()
        settings = target.to_dict()
        settings.pop('pages')
        warnings = template_compatibility_warnings(validate_manifest(self.manifest), target)
        self.assertEqual(len(warnings), 2)
        apply_template_to_page(validate_manifest(self.manifest), target.active_page)
        actual = target.to_dict()
        actual.pop('pages')
        self.assertEqual(actual, settings)
        self.assertEqual(target.pages[1].to_dict(), other)
        any_store = copy.deepcopy(self.manifest)
        any_store['store'] = 'any'
        self.assertEqual(template_compatibility_warnings(validate_manifest(any_store), self.project), [])

    def test_apply_revalidates_before_mutating_target(self):
        template = validate_manifest(self.manifest)
        template.manifest['version'] = 99
        before = self.page.to_dict()
        with self.assertRaises(TemplateError):
            apply_template_to_page(template, self.page)
        self.assertEqual(self.page.to_dict(), before)

    def test_import_rejects_malformed_json_and_oversized_manifests(self):
        path = self.root / 'template.json'
        for raw in ('{bad', '[]', 'null', '{"version":NaN}', '\ufeff{}'):
            path.write_text(raw)
            with self.assertRaises(TemplateError):
                load_template_package(path)
        path.write_bytes(b' ' * (MAX_MANIFEST_BYTES + 1))
        with self.assertRaisesRegex(TemplateError, '2 MiB'):
            load_template_package(path)
        with self.assertRaises(TemplateError):
            load_template_package(self.root / 'missing')

    def test_excessive_text_bounds_rejected_before_rendering(self):
        for text, size, spacing in [('A' * 2001, 38, 1), ('A\n' * 51, 38, 1),
                                    ('A\n' * 50, 1000, 10)]:
            data = copy.deepcopy(self.manifest)
            data['content']['layers'][1].update(text=text, font_size=size, line_spacing=spacing)
            with self.assertRaises(TemplateError):
                validate_manifest(data)

    def test_private_paths_and_source_references_rejected(self):
        for value in ('/Users/person/a.png', '../assets/source.png', 'assets/source.png'):
            data = copy.deepcopy(self.manifest)
            data['content']['layers'][0]['file_path'] = value
            with self.assertRaises(TemplateError):
                validate_manifest(data)
        for key, value in [('name', '/Users/person/private'), ('description', 'C:\\private\\file'),
                           ('author', '/home/person/file')]:
            data = copy.deepcopy(self.manifest)
            data[key] = value
            with self.assertRaises(TemplateError):
                validate_manifest(data)

    def test_existing_directory_refused_and_failure_leaves_no_partial_package(self):
        package = self.root / 'existing'
        package.mkdir()
        sentinel = package / 'keep.txt'
        sentinel.write_text('untouched')
        with self.assertRaises(TemplateError):
            export_template_package(self.project, self.page, package, 'Layout')
        self.assertEqual(sentinel.read_text(), 'untouched')
        failed = self.root / 'failed'
        with patch('core.template_format.render_template_preview', side_effect=OSError('render failed')):
            with self.assertRaises(TemplateError):
                export_template_package(self.project, self.page, failed, 'Layout')
        self.assertFalse(failed.exists())
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ['existing', 'private-screenshot.png'])

    def test_project_roundtrip_legacy_and_replaced_placeholder_export(self):
        apply_template_to_page(validate_manifest(self.manifest), self.page)
        image = self.page.layers[0]
        project_path = self.root / 'working.json'
        self.assertTrue(save_project_to_json(self.project, str(project_path))[0])
        restored, message = load_project_from_json(str(project_path))
        self.assertIsNotNone(restored, message)
        self.assertEqual(restored.active_page.layers[0].to_dict(), image.to_dict())
        legacy = self.project.to_dict()
        for layer in legacy['pages'][0]['layers']:
            layer.pop('placeholder_id', None)
            layer.pop('placeholder_label', None)
        self.assertEqual(Project.from_dict(legacy).active_page.layers[0].placeholder_id, '')
        for panel, module in ((LayerSidebar, 'ui.layer_sidebar'), (PropertyPanel, 'ui.property_panel')):
            image.file_path = ''
            with patch(module + '.filedialog.askopenfilename', return_value=str(self.source)):
                panel._replace_image_layer_file(SimpleNamespace(refresh=Mock(), on_change=Mock()), image)
            self.assertEqual(image.crop_top, .2)
            self.assertEqual(image.effects, self.image.effects)
        self.assertTrue(export_single_page(self.project, self.page, str(self.root / 'output.png'))[0])

    def test_duplicate_placeholders_export_with_unique_ids(self):
        self.image.placeholder_id = 'hero'
        duplicate = copy.deepcopy(self.image)
        self.page.layers.append(duplicate)
        template = template_from_page(self.project, self.page, 'Duplicates')
        ids = [layer.placeholder_id for layer in template.create_page().layers if isinstance(layer, ImageLayer)]
        self.assertEqual(ids, ['hero', 'hero_copy'])

    def test_built_in_templates_export_without_migration(self):
        for name, factory in TEMPLATE_FACTORIES.items():
            page = factory(300, 600)
            template = template_from_page(self.project, page, name)
            self.assertEqual(len(template.create_page().layers), len(page.layers))

    def test_import_ui_cancel_and_validation_error_do_not_modify_page(self):
        fake = SimpleNamespace(project=self.project, refresh_all=Mock(), selected_layer=self.image,
                               canvas_view=SimpleNamespace(set_selected_layer=Mock()))
        before = self.page.to_dict()
        path = self.root / 'template.json'
        path.write_text(json.dumps(self.manifest))
        with patch('ui.main_window.filedialog.askopenfilename', return_value=str(path)), \
             patch('ui.main_window.messagebox.askyesno', return_value=False):
            MainWindow.on_import_template(fake)
        self.assertEqual(self.page.to_dict(), before)
        path.write_text('bad JSON')
        with patch('ui.main_window.filedialog.askopenfilename', return_value=str(path)), \
             patch('ui.main_window.messagebox.showerror') as error:
            MainWindow.on_import_template(fake)
        error.assert_called_once()
        fake.refresh_all.assert_not_called()

    def test_import_ui_apply_and_export_ui(self):
        fake = SimpleNamespace(project=self.project, refresh_all=Mock(), selected_layer=self.image,
                               canvas_view=SimpleNamespace(set_selected_layer=Mock()))
        path = self.root / 'template.json'
        path.write_text(json.dumps(self.manifest))
        with patch('ui.main_window.filedialog.askopenfilename', return_value=str(path)), \
             patch('ui.main_window.messagebox.askyesno', return_value=True):
            MainWindow.on_import_template(fake)
        self.assertIsNone(fake.selected_layer)
        self.assertEqual(fake.project.active_page.layers[0].file_path, '')
        fake.refresh_all.assert_called_once()
        with patch('ui.main_window.simpledialog.askstring', return_value='UI Template'), \
             patch('ui.main_window.filedialog.askdirectory', return_value=str(self.root)), \
             patch('ui.main_window.messagebox.showinfo'):
            MainWindow.on_export_template(fake)
        self.assertTrue((self.root / 'UI_Template' / 'template.json').is_file())

import os


@unittest.skipUnless(os.environ.get('SSSTUDIO_GUI_TESTS') == '1', 'requires a Tk display')
class TemplateTkTests(unittest.TestCase):
    def test_real_window_export_import_replace_save_reload_and_png(self):
        app = MainWindow()
        self.addCleanup(app.destroy)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.png'
            Image.new('RGB', (100, 200), '#ff00ff').save(source)
            layer = ImageLayer(file_path=str(source), crop_top=.2,
                               effects=ImageEffectsConfig(fade_enabled=True, shadow_enabled=True))
            app.project = Project(preset_name='Custom', canvas_width=360, canvas_height=720,
                pages=[Page(layers=[layer, TextLayer(text='Test', font_size=40)],
                            panorama=PanoramaConfig(enabled=True, screen_count=3))])
            app.refresh_all()
            app.update()
            with patch('ui.main_window.simpledialog.askstring', return_value='Tk Export'), \
                 patch('ui.main_window.filedialog.askdirectory', return_value=directory), \
                 patch('ui.main_window.messagebox.showinfo'):
                app.on_export_template()
            manifest_path = root / 'Tk_Export' / 'template.json'
            self.assertTrue(manifest_path.is_file())
            with patch('ui.main_window.filedialog.askopenfilename', return_value=str(manifest_path)), \
                 patch('ui.main_window.messagebox.askyesno', return_value=True):
                app.on_import_template()
            app.update()
            imported = app.project.active_page.layers[0]
            self.assertEqual(imported.file_path, '')
            self.assertEqual(app.project.active_page.panorama.screen_count, 3)
            app._on_layer_selected(imported)
            app.update()
            from ui.collapsible_section import CollapsibleSection
            crop = next(widget for widget in app.layer_sidebar.inspector_container.winfo_children()
                        if isinstance(widget, CollapsibleSection) and widget.title == 'Crop')
            self.assertTrue(any(widget.cget('text').startswith('Placeholder:')
                                for widget in crop.content.winfo_children()
                                if widget.winfo_class() == 'Label'))
            with patch('ui.layer_sidebar.filedialog.askopenfilename', return_value=str(source)):
                app.layer_sidebar._replace_image_layer_file(imported)
            self.assertEqual(imported.crop_top, .2)
            project_path = root / 'project.json'
            with patch('ui.main_window.filedialog.asksaveasfilename', return_value=str(project_path)), \
                 patch('ui.main_window.messagebox.showinfo'):
                app.on_save_project_as()
            with patch('ui.main_window.filedialog.askopenfilename', return_value=str(project_path)):
                app.on_open_project()
            self.assertEqual(app.project.active_page.layers[0].placeholder_id, imported.placeholder_id)
            with patch('ui.main_window.filedialog.asksaveasfilename', return_value=str(root / 'output.png')), \
                 patch('ui.main_window.messagebox.showinfo'):
                app.on_export_current()
            self.assertTrue((root / 'output_03.png').is_file())
