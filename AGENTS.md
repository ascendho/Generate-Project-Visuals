# Repository Guidelines

## Project Structure & Module Organization

- `scripts/render_cover.py` renders, rasterizes, and validates cover, social-preview, and promo assets.
- `scripts/render_logo.py` validates logo concepts and produces Mark and Lockup SVG/PNG files.
- `assets/` contains the clean-editorial SVG templates and generated artwork.
- `references/clean-editorial.md` defines the JSON schema, visual system, and SVG constraints.
- `SKILL.md` documents the agent workflow; `agents/openai.yaml` provides skill metadata.
- `README.md` and `README.zh-CN.md` are the user-facing guides.

Keep reusable rendering logic in `scripts/`, stable templates in `assets/`, and temporary previews under `/tmp`, not in the repository.

## Build, Test, and Development Commands

This project has no separate build step. Rendering requires Python 3, Playwright, and Chromium:

```sh
python -m pip install playwright
python -m playwright install chromium
python3 -m py_compile scripts/*.py
```

Use `python3 scripts/render_cover.py --help` or `python3 scripts/render_logo.py --help` to inspect CLI commands. Render cover work to a temporary directory before publishing:

```sh
python3 scripts/render_cover.py render assets/<slug>-cover.json \
  --output-dir /tmp/<slug>-preview
python3 scripts/render_cover.py validate assets/<slug>-cover.json \
  --output-dir assets
```

Use the equivalent `render_logo.py preview`, `render`, and `validate` commands for logos. Add `--force` only when replacing existing generated files intentionally.

## Coding Style & Naming Conventions

Follow the existing Python style: four-space indentation, type hints, `pathlib.Path`, uppercase module constants, `snake_case` functions, and leading underscores for internal helpers. Keep CLI errors actionable and raise `CoverError` or `LogoError` for validation failures.

Use lowercase hyphenated repository slugs and filenames such as `example-project-cover-zh.svg`. Preserve exact template viewboxes, safe-area attributes, and the approved blue/charcoal palette.

## Testing Guidelines

There is currently no automated test suite or coverage threshold. For every change, run `py_compile`, exercise the affected CLI path, and validate generated files. Inspect SVG and PNG output at full size and thumbnail size, including localized and RTL variants when relevant. Test failure cases for unsafe SVG content, invalid JSON, and unexpected overwrites.

## Commit & Pull Request Guidelines

No repository commit history establishes a message convention. Use short, imperative subjects such as `Validate localized promo output`. Keep commits focused. Pull requests should explain the behavior changed, list commands run, link related issues, and include before/after images for visual changes. Do not commit temporary previews, caches, or unapproved generated concepts.
