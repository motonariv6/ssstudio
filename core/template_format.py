"""Portable, data-only Template Format v1 (placeholder-only directory packages)."""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass, fields, replace

from PIL import ImageColor

from core.models import Project, Page, ImageLayer, TextLayer, GradientConfig, FrameConfig, ImageEffectsConfig
from core.panorama import PanoramaConfig
from core.renderer import render_page, get_text_layer_metrics

FORMAT = 'ssstudio-template'
VERSION = 1
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
STORES = ('any', 'apple_app_store', 'google_play')


class TemplateError(ValueError):
    """A package could not be read, validated, applied or exported."""


def _object(value, location):
    if not isinstance(value, dict):
        raise TemplateError(f'{location} must be an object')
    return value


def _string(value, location, nonempty=False):
    if not isinstance(value, str) or len(value) > 20000 or (nonempty and not value.strip()):
        raise TemplateError(f'{location} must be a valid string' + (' (not empty)' if nonempty else ''))
    # Machine paths have no place in this portable, asset-free format.
    if value.startswith(('/', '~/')) or re.match(r'^[A-Za-z]:[\\/]', value) or '/Users/' in value or '/home/' in value:
        raise TemplateError(f'{location} contains a machine-specific path')
    return value


def _number(value, location, low, high, integer=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and low <= value <= high
    except OverflowError:
        valid = False
    if not valid:
        raise TemplateError(f'{location} must be between {low} and {high}')
    if integer and type(value) is not int:
        raise TemplateError(f'{location} must be an integer')
    return value


def _color(value, location):
    _string(value, location)
    try:
        ImageColor.getrgb(value)
    except (ValueError, TypeError) as exc:
        raise TemplateError(f'{location} is not a valid color') from exc


def _config(data, default, location, excluded=()):
    """Read only model fields, checking types before passing data to models."""
    _object(data, location)
    result = {}
    for field in fields(default):
        key = field.name
        if key not in data or key in excluded:
            continue
        value, fallback = data[key], getattr(default, key)
        where = f'{location}.{key}'
        if isinstance(fallback, bool):
            if type(value) is not bool:
                raise TemplateError(f'{where} must be a boolean')
        elif isinstance(fallback, str):
            _string(value, where)
        elif isinstance(fallback, (int, float)):
            _number(value, where, -100000, 100000, integer=isinstance(fallback, int))
        else:
            continue
        if 'color' in key:
            _color(value, where)
        result[key] = value
    return result


@dataclass
class TemplatePackage:
    manifest: dict

    @property
    def name(self):
        return self.manifest['name']

    def to_dict(self):
        return copy.deepcopy(self.manifest)

    def create_page(self):
        # No IDs are stored: each application gets new page/layer identities.
        return Page.from_dict(copy.deepcopy(self.manifest['content']))


def validate_manifest(data):
    """Return canonical v1 data; unknown fields are ignored, invalid data is rejected."""
    _object(data, 'manifest')
    required = ('format', 'version', 'id', 'name', 'description', 'author', 'tags',
                'store', 'screen_count', 'target', 'content')
    for key in required:
        if key not in data:
            raise TemplateError(f'Missing required field: {key}')
    if data['format'] != FORMAT:
        raise TemplateError(f'Invalid template format; expected {FORMAT}')
    if type(data['version']) is not int or data['version'] != VERSION:
        raise TemplateError(f'Unsupported template version: {data["version"]}; supported version is {VERSION}')
    result = {'format': FORMAT, 'version': VERSION}
    for key in ('id', 'name', 'description', 'author'):
        result[key] = _string(data[key], key, nonempty=key in ('id', 'name'))
    tags = data['tags']
    if not isinstance(tags, list) or len(tags) > 100:
        raise TemplateError('tags must be an array of at most 100 strings')
    result['tags'] = [_string(tag, 'tags') for tag in tags]
    result['created_with'] = _string(data.get('created_with', 'SSStudio'), 'created_with')
    if data['store'] not in STORES:
        raise TemplateError('store must be any, apple_app_store or google_play')
    result['store'] = data['store']
    result['screen_count'] = _number(data['screen_count'], 'screen_count', 1, 4, integer=True)
    target = _object(data['target'], 'target')
    for key in ('canvas_width', 'canvas_height'):
        if key not in target:
            raise TemplateError(f'Missing required field: target.{key}')
    result['target'] = {key: _number(target[key], f'target.{key}', 1, 8192, integer=True)
                        for key in ('canvas_width', 'canvas_height')}
    for key in ('preset_name', 'device_type'):
        result['target'][key] = _string(target.get(key, 'Custom' if key == 'preset_name' else 'custom'), f'target.{key}')
    if 'asset_type' in target:
        result['target']['asset_type'] = _string(target['asset_type'], 'target.asset_type')
    if target['canvas_width'] * target['canvas_height'] * result['screen_count'] > 32000000:
        raise TemplateError('Template workspace exceeds 32 million pixels')
    content = _object(data['content'], 'content')
    for key in ('background', 'panorama', 'layers'):
        if key not in content:
            raise TemplateError(f'Missing required field: content.{key}')
    bg = GradientConfig(**_config(content['background'], GradientConfig(), 'background'))
    if bg.direction not in ('vertical', 'horizontal', 'diagonal'):
        raise TemplateError('Invalid background direction')
    for key in ('intensity', 'spotlight_x', 'spotlight_y', 'spotlight_strength'):
        _number(getattr(bg, key), f'background.{key}', 0, 1)
    _number(bg.spotlight_radius, 'background.spotlight_radius', 0, 10)
    panorama = PanoramaConfig(**_config(content['panorama'], PanoramaConfig(), 'panorama'))
    try:
        panorama.validate()
    except ValueError as exc:
        raise TemplateError(str(exc)) from exc
    if (panorama.screen_count if panorama.enabled else 1) != result['screen_count']:
        raise TemplateError('screen_count does not match panorama configuration')
    raw_layers = content['layers']
    if not isinstance(raw_layers, list) or len(raw_layers) > 200:
        raise TemplateError('content.layers must be an array of at most 200 layers')
    layers, placeholders = [], set()
    for index, raw in enumerate(raw_layers):
        _object(raw, f'layer {index}')
        kind = raw.get('layer_type')
        if kind not in ('image', 'text'):
            raise TemplateError(f'Unsupported layer type at layer {index}: {kind}')
        if kind == 'image':
            if raw.get('file_path', ''):
                raise TemplateError('v1 image layers must be placeholders without source paths')
            layer = ImageLayer(**_config(raw, ImageLayer(), f'layer {index}',
                                        excluded=('id', 'file_path', 'original_width', 'original_height')))
            layer.frame = FrameConfig(**_config(raw.get('frame', {}), FrameConfig(), 'frame'))
            layer.effects = ImageEffectsConfig(**_config(raw.get('effects', {}), ImageEffectsConfig(), 'effects'))
            if layer.effects.fade_direction != 'bottom':
                raise TemplateError('v1 supports only bottom fade')
            if not 0 <= layer.effects.fade_start < layer.effects.fade_end <= 1:
                raise TemplateError('effects requires 0 <= fade_start < fade_end <= 1')
            for config, name in ((layer.frame, 'frame'), (layer.effects, 'effects')):
                _number(config.shadow_opacity, name + '.shadow_opacity', 0, 1)
                _number(config.shadow_blur, name + '.shadow_blur', 0, 1000 if name == 'frame' else 100)
                for axis in ('x', 'y'):
                    _number(getattr(config, 'shadow_offset_' + axis), name + '.shadow_offset_' + axis,
                            -1000 if name == 'frame' else -100, 1000 if name == 'frame' else 100)
            _number(layer.frame.corner_radius, 'frame.corner_radius', 0, 1000)
            _number(layer.frame.border_width, 'frame.border_width', 0, 100)
            for start, end in ((layer.crop_left, layer.crop_right), (layer.crop_top, layer.crop_bottom)):
                if not 0 <= start < end <= 1:
                    raise TemplateError('Crop coordinates must be normalized and ordered')
            _number(layer.scale, 'image.scale', .05, 10)
            _number(layer.opacity, 'image.opacity', 0, 1)
            layer.placeholder_id = _string(raw.get('placeholder_id', f'image_{index + 1}'), 'placeholder_id', True)
            layer.placeholder_label = _string(raw.get('placeholder_label', layer.name), 'placeholder_label')
            if layer.placeholder_id in placeholders:
                raise TemplateError('Duplicate placeholder_id')
            placeholders.add(layer.placeholder_id)
        else:
            layer = TextLayer(**_config(raw, TextLayer(), f'layer {index}', excluded=('id',)))
            _number(layer.font_size, 'text.font_size', 6, 1000, integer=True)
            _number(layer.max_width, 'text.max_width', 0, 32768, integer=True)
            _number(layer.line_spacing, 'text.line_spacing', .1, 10)
            _number(layer.letter_spacing, 'text.letter_spacing', -100, 100, integer=True)
            if layer.align not in ('left', 'center', 'right') or layer.font_weight not in ('regular', 'bold', 'heavy'):
                raise TemplateError('Invalid text alignment or font weight')
            if len(layer.text) > 2000 or layer.text.count('\n') > 50:
                raise TemplateError('Template text exceeds 2000 characters or 51 explicit lines')
            width, height, _, _ = get_text_layer_metrics(layer, result['target']['canvas_width'])
            if width > 16384 or height > 16384 or (width + 40) * (height + 40) > 16000000:
                raise TemplateError('Template text rendering area is too large')
        serialized = layer.to_dict()
        for key in ('id', 'file_path', 'original_width', 'original_height'):
            serialized.pop(key, None)
        layers.append(serialized)
    result['content'] = {'background': bg.to_dict(), 'panorama': panorama.to_dict(), 'layers': layers}
    return TemplatePackage(result)


def template_from_page(project, page, name, description='', author='', tags=None):
    content = page.to_dict()
    content.pop('id')
    content.pop('name')
    placeholder_ids = set()
    for index, layer in enumerate(content['layers']):
        layer.pop('id')
        if layer['layer_type'] == 'image':
            for key in ('file_path', 'original_width', 'original_height'):
                layer.pop(key, None)
            placeholder_id = layer.get('placeholder_id') or f'image_{index + 1}'
            while placeholder_id in placeholder_ids:
                placeholder_id += '_copy'
            placeholder_ids.add(placeholder_id)
            layer['placeholder_id'] = placeholder_id
            layer['placeholder_label'] = layer.get('placeholder_label') or layer['name']
    target_data = {'canvas_width': project.canvas_width, 'canvas_height': project.canvas_height,
                   'preset_name': project.preset_name, 'device_type': project.device_type}
    if project.asset_type:
        target_data['asset_type'] = project.asset_type
    return validate_manifest({'format': FORMAT, 'version': VERSION, 'id': str(uuid.uuid4()),
        'name': name, 'description': description, 'author': author, 'tags': tags or [],
        'created_with': 'SSStudio', 'store': project.store,
        'screen_count': page.panorama.screen_count if page.panorama.enabled else 1,
        'target': target_data, 'content': content})


def load_template_package(path):
    """Read a directory or its template.json; never follow asset/source references."""
    manifest_path = Path(path)
    if manifest_path.is_dir():
        manifest_path /= 'template.json'
    try:
        with manifest_path.open('rb') as source:
            raw = source.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise TemplateError('Template manifest exceeds 2 MiB')
        return validate_manifest(json.loads(raw.decode('utf-8')))
    except TemplateError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise TemplateError(f'Cannot read template: {exc}') from exc


def render_template_preview(template):
    """Render background/text only; never read any source screenshot or asset."""
    page = template.create_page()
    target = template.manifest['target']
    factor = min(1, 960 / (target['canvas_width'] * template.manifest['screen_count']),
                 640 / target['canvas_height'])
    page.layers = [replace(layer, x=layer.x * factor, y=layer.y * factor,
                          font_size=max(6, round(layer.font_size * factor)),
                          max_width=round(layer.max_width * factor),
                          letter_spacing=round(layer.letter_spacing * factor))
                   for layer in page.layers if isinstance(layer, TextLayer)]
    project = Project(preset_name='Custom', canvas_width=max(1, round(target['canvas_width'] * factor)),
                      canvas_height=max(1, round(target['canvas_height'] * factor)), pages=[page])
    return render_page(project, page, show_guides=False).convert('RGB')


def export_template_package(project, page, destination, name, description='', author='', tags=None):
    template = template_from_page(project, page, name, description, author, tags)
    destination = Path(destination)
    staging = None
    try:
        if destination.exists() or destination.is_symlink():
            raise TemplateError('Template destination already exists; choose a new package directory')
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.ssstudio-template-', dir=destination.parent))
        manifest = json.dumps(template.to_dict(), ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
        if len(manifest) > MAX_MANIFEST_BYTES:
            raise TemplateError('Template manifest exceeds 2 MiB')
        (staging / 'template.json').write_bytes(manifest)
        render_template_preview(template).save(staging / 'preview.png')
        # Reserve the destination exclusively before publishing our files.
        destination.mkdir()
        try:
            for filename in ('template.json', 'preview.png'):
                os.replace(staging / filename, destination / filename)
        except OSError:
            shutil.rmtree(destination)
            raise
        return template
    except TemplateError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise TemplateError(f'Cannot export template: {exc}') from exc
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)


def template_compatibility_warnings(template, project):
    warnings = []
    if template.manifest['store'] not in ('any', project.store):
        warnings.append(f'Template store: {template.manifest["store"]}; current store: {project.store}.')
    target = template.manifest['target']
    if (target['canvas_width'], target['canvas_height']) != (project.canvas_width, project.canvas_height):
        warnings.append(f'Template canvas: {target["canvas_width"]} × {target["canvas_height"]}; '
                        f'current canvas: {project.canvas_width} × {project.canvas_height}. Positions keep their original pixel values.')
    return warnings


def apply_template_to_page(template, page):
    """Validate first, then replace content while retaining the working page name/ID."""
    new_page = validate_manifest(template.to_dict()).create_page()
    page.background, page.panorama, page.layers = new_page.background, new_page.panorama, new_page.layers
