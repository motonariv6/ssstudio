# AGENTS.md — SSStudio

## Project Overview

SSStudio is a local desktop application for composing and exporting App Store / Google Play screenshot creatives.

Current implementation:

- Python 3.10+
- Tkinter GUI
- Pillow
- NumPy
- macOS is the primary supported platform
- Project data is persisted as JSON
- High-resolution image rendering is handled locally

Repository:

```text
motonariv6/ssstudio
```

Default branch:

```text
main
```

---

## Architecture

Keep the application separated into two major areas:

```text
core/
ui/
```

### core/

`core/` contains application models, rendering, templates, export, fonts, and project persistence.

Current responsibilities include:

```text
core/models.py
core/fonts.py
core/renderer.py
core/templates.py
core/exporter.py
core/project.py
```

Rules:

- `core/` must remain independent from Tkinter.
- Do not import Tkinter or UI widgets into `core/`.
- Rendering logic must be usable independently of the desktop UI.
- Project models must remain serializable.
- Prefer shared geometry/render helpers over duplicating calculations between UI and renderer.

The intended dependency direction is:

```text
UI
↓
Models / Project
↓
Renderer / Exporter
```

Do not reverse this dependency.

---

## UI

Tkinter UI code belongs under:

```text
ui/
```

Current responsibilities include:

```text
ui/main_window.py
ui/canvas_view.py
ui/page_manager.py
ui/property_panel.py
ui/theme.py
```

Rules:

- UI state should modify models and request rendering.
- Do not duplicate rendering behavior inside Tkinter widgets.
- Preview and exported output should use the same geometry and rendering rules whenever possible.
- Keep UI interactions simple and predictable.
- Avoid introducing modal workflows unless they materially simplify editing.

---

## Rendering

SSStudio is intended to generate production-quality store screenshots.

Rendering changes must preserve:

- high-resolution export quality
- alpha handling
- RGB PNG export compatibility
- existing frame behavior
- corner radius
- border
- shadow
- opacity
- rotation
- text rendering quality

Use Pillow high-quality resampling where appropriate.

Do not optimize rendering at the cost of visible export quality without explicit approval.

Preview rendering may use reduced resolution, but its geometry should remain consistent with final export.

---

## Project Compatibility

Existing project JSON files should continue loading whenever reasonably possible.

When adding fields:

- provide safe defaults
- treat absent fields as legacy project data
- preserve backward compatibility

Avoid breaking the current JSON structure unless a migration is explicitly required.

Do not modify source image files as part of normal editing operations.

Image transformations should preferably be non-destructive and represented as project metadata.

---

## Code Changes

Prefer focused changes.

Do not perform unrelated large-scale refactoring while implementing a feature or bug fix.

Before changing architecture:

1. Inspect the current implementation.
2. Reuse existing abstractions where appropriate.
3. Introduce a new abstraction only when it removes meaningful duplication or enables required functionality.

Avoid speculative frameworks and unnecessary dependencies.

Do not add an external dependency when the feature can reasonably be implemented with the existing stack.

---

## Tests

Run the full existing test suite after implementation:

```bash
./venv/bin/python -m unittest discover tests
```

New behavior should receive tests where practical.

At minimum, test:

- model serialization when models change
- project save/load behavior
- legacy JSON compatibility when persistence changes
- renderer geometry when image behavior changes
- export behavior where relevant

Do not delete or weaken existing tests simply to make a change pass.

If a test expectation is genuinely obsolete, explain why before changing it.

---

## Manual Validation

For UI-related changes, automated tests alone are not sufficient.

Where relevant, verify:

- application starts successfully
- existing projects open
- edited projects save and reopen
- preview behaves correctly
- exported PNG matches intended preview geometry
- existing image/text editing behavior still works

Report which validations were actually performed.

Do not claim manual validation that was not performed.

---

## Git Workflow

For feature work:

1. Start from an up-to-date `main`.
2. Create a dedicated feature branch.
3. Implement the scoped change.
4. Run tests.
5. Perform relevant manual validation.
6. Create a local commit.

Unless explicitly instructed otherwise:

- do not push
- do not merge
- do not create a pull request
- do not modify `main` directly

Use descriptive branch names such as:

```text
feat/m1-image-crop
feat/android-presets
feat/panorama-layout
fix/export-scaling
```

Use concise conventional-style commit messages where practical:

```text
feat: add non-destructive image crop
fix: preserve crop geometry in preview
refactor: share image layer geometry helper
```

---

## Scope Discipline

When a task has explicit requirements, implement those requirements first.

Do not automatically add adjacent features.

Examples:

If implementing image crop, do not also add:

- filters
- image effects
- aspect-ratio presets
- new export formats
- cloud storage

unless they are explicitly part of the task.

Record reasonable follow-up ideas separately instead.

---

## Product Direction

SSStudio currently prioritizes a local desktop workflow.

Near-term directions may include:

- image cropping
- Android / Google Play screenshot support
- multi-screen / panorama compositions
- reusable external template format
- community templates
- additional desktop platforms

Do not assume a web application, cloud backend, account system, or hosted service is required.

The core rendering and project model should remain portable enough that other interfaces can be added later.

---

## Completion Report

After completing a coding task, report:

- branch name
- changed files
- implementation summary
- test results
- manual validation performed
- commit SHA
- known limitations
- useful follow-up candidates

Be explicit about anything not tested or not completed.