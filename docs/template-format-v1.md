# SSStudio Template Format v1

A template is one reusable page layout, distinct from a working Project JSON.
Version 1 uses a directory package:

```text
my-template/
├── template.json
└── preview.png
```

All image layers are placeholders. Bundled decorative assets and ZIP packages
are reserved for a later version; v1 does not read or copy assets or source images.
The preview contains the background and text only, without guides or screenshots.
Its longest dimensions are approximately 960 × 640 pixels, preserving workspace ratio.

## Manifest

```json
{
  "format": "ssstudio-template",
  "version": 1,
  "id": "minimal-dark",
  "name": "Minimal Dark",
  "description": "Reusable dark screenshot layout",
  "author": "",
  "tags": ["minimal", "dark"],
  "created_with": "SSStudio",
  "store": "any",
  "screen_count": 1,
  "target": {
    "canvas_width": 1290,
    "canvas_height": 2796,
    "preset_name": "iPhone 6.9-inch",
    "device_type": "phone"
  },
  "content": {
    "background": {
      "preset": "pure_black",
      "color_start": "#000000",
      "color_end": "#000000",
      "spotlight_enabled": false
    },
    "panorama": {
      "enabled": false,
      "screen_count": 1,
      "direction": "horizontal"
    },
    "layers": [
      {
        "layer_type": "image",
        "name": "Hero Screenshot",
        "placeholder_id": "hero_screenshot",
        "placeholder_label": "Hero Screenshot",
        "x": 645,
        "y": 1700,
        "scale": 0.9,
        "crop_left": 0.0,
        "crop_top": 0.0,
        "crop_right": 1.0,
        "crop_bottom": 1.0,
        "frame": {"enabled": true},
        "effects": {"fade_enabled": false, "shadow_enabled": false}
      },
      {
        "layer_type": "text",
        "name": "Headline",
        "text": "Your headline",
        "x": 645,
        "y": 220,
        "font_size": 84,
        "font_family": "Hiragino Sans",
        "font_weight": "bold",
        "align": "center"
      }
    ]
  }
}
```

Required top-level fields are `format`, `version`, `id`, `name`, `description`,
`author`, `tags`, `store`, `screen_count`, `target`, and `content`.
`created_with` defaults to `SSStudio`. IDs and names must be nonempty strings.
Export assigns a UUID template ID; import and serialization retain that identity.
Tags are an array of strings. Store is `any`, `apple_app_store`, or `google_play`.

`target.canvas_width` and `target.canvas_height` are required per-screen pixel
sizes. `preset_name` and `device_type` are advisory metadata. Applying a template
keeps the current Project Store, preset and canvas dimensions. The UI warns when
the Store or dimensions differ. Positions retain their saved pixel values;
there is no automatic layout adaptation.

`content` requires `background`, `panorama`, and `layers`. Background fields
reuse `GradientConfig`: preset, colors, direction, intensity and spotlight fields.
Panorama reuses `PanoramaConfig`: horizontal only, 2–4 screens when enabled.
The top-level `screen_count` is the actual output count (1 when panorama is off)
and must agree with the content. A disabled panorama can retain a preferred count
of 2–4 in its configuration.

The layer array is in back-to-front drawing order. Only `image` and `text` are
supported. Individual model fields default to current SSStudio defaults when
omitted; unknown fields are ignored. Page and layer IDs are omitted, and every
application creates fresh working IDs while retaining the destination page's
name and ID.

Image fields reuse `ImageLayer`: name, position, scale, rotation, opacity,
visibility, lock, normalized crop coordinates, `FrameConfig`, and
`ImageEffectsConfig`. Crop edges must be ordered within 0–1. Fade must satisfy
`0 <= fade_start < fade_end <= 1` and direction must be `bottom`. Image shadow
opacity is 0–1, blur 0–100, offsets −100–100. Frame and image shadows stay separate.
A nonempty `file_path` is rejected. Source image dimensions are not exported.
`placeholder_id` is unique within a template; omitted IDs become `image_N`.
`placeholder_label` defaults to the layer name. On export, duplicate placeholder
IDs receive `_copy` suffixes. The first Replace Image on an empty placeholder
preserves the template's crop; later replacements retain normal Reset Crop behavior.

Text fields reuse `TextLayer`: text/default copy, name, position, font family,
size/weight, color, alignment, max width, line/letter spacing, style preset,
visibility and lock. Font family names are portable preferences, not font files;
normal SSStudio font fallback applies on the destination machine.

## Reading, writing and limits

The reader accepts a package directory or its `template.json`. It checks the
format and exact supported version before constructing models. Unknown versions,
invalid types, non-finite numbers, invalid colors, unsupported layer types and
invalid crop/effects/workspace settings produce `TemplateError`. No template code
is executed, no modules are imported from a package, and preview/assets are not
read during import.

V1 limits manifests to 2 MiB, 200 layers, 100 tags, per-screen dimensions of
1–8192 pixels, and a workspace of at most 32 million pixels. String fields are
limited to 20,000 characters. Coordinates are finite and within ±100,000 pixels.
Text content is limited to 2,000 characters and 51 explicit lines. Calculated
text bounds must be at most 16,384 pixels on either axis and 16 million pixels
including renderer padding, preventing excessive allocation during rendering.
Image scale is 0.05–10; text size is 6–1000, max width 0–32768, line spacing
0.1–10 and integer letter spacing −100–100. These are import/export validation
limits; existing Project files use their unchanged loader.

Export writes into a new package directory, refuses existing destinations, and
stages files before publishing them. Validation or preview failure does not leave
a partial package. Source screenshot paths, original files, Project name and
working IDs are omitted. Machine-specific paths are rejected in known string
fields. Unknown fields are discarded on canonical serialization.

Text and layer names are intentionally retained as template content. Review them
before sharing a package; omitting screenshots does not anonymize authored text.
Imported placeholders and their labels survive Project Save / Load. Built-in
Python templates remain available alongside this external format.
