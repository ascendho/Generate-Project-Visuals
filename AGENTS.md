# Repository Guidelines

## Project Structure & Module Organization

- `plugins/generate-github-cover/` is the installable Codex Plugin.
- `plugins/generate-github-cover/skills/generate-github-cover/` contains `SKILL.md`, agent metadata, render scripts, visual references, and stable SVG templates.
- `assets/` contains this repository's generated Logo, Cover, Social Preview, Promo files, and their source JSON; do not place reusable templates there.
- `.agents/plugins/marketplace.json` exposes the Plugin through the repository marketplace.
- `tools/package_skill.py` builds the standalone Skill archive; `.github/workflows/release.yml` publishes tagged releases.
- `README.md` and `README.zh-CN.md` are synchronized user guides.

Keep temporary concepts and previews under `/tmp`, never in the repository.

## Build, Test, and Development Commands

There is no separate build step. Install runtime dependencies and Chromium:

```sh
python -m pip install playwright segno
python -m playwright install chromium
```

Use the nested renderers from the repository root:

```sh
SKILL_DIR=plugins/generate-github-cover/skills/generate-github-cover
python3 -m py_compile "$SKILL_DIR"/scripts/*.py tools/package_skill.py
python "$SKILL_DIR/scripts/render_cover.py" render \
  assets/<slug>-cover.json --output-dir /tmp/<slug>-preview
python "$SKILL_DIR/scripts/render_cover.py" validate \
  assets/<slug>-cover.json --output-dir assets
python tools/package_skill.py v0.1.0 --check-only
```

Use the equivalent `render_logo.py` commands for Logo work. Add `--force` only when replacing generated files intentionally.

## Coding Style & Naming Conventions

Use four-space Python indentation, type hints, `pathlib.Path`, uppercase module constants, `snake_case` functions, and leading underscores for internal helpers. Raise `CoverError`, `LogoError`, or `PackageError` with actionable messages. Use lowercase hyphenated slugs such as `example-project-cover-zh.svg`. Preserve template viewboxes, safe-area attributes, and the approved blue/charcoal palette.

## Testing Guidelines

No coverage threshold is defined. Every change must pass Python compilation, Skill and Plugin structure validation, affected CLI paths, and generated-asset validation. Inspect SVG and PNG output at full and thumbnail sizes. For packaging changes, build into `/tmp`, inspect archive contents, verify the checksum, and confirm repository docs, caches, and showcase artwork are excluded.

## Commit & Pull Request Guidelines

Follow the existing short, imperative style, for example `Package skill releases`. Keep commits focused. Pull requests should describe behavior, list validation commands, link issues, and include before/after images for visual changes. Never commit caches, temporary previews, or unapproved Logo concepts. A release commit must update the Plugin version before the matching `vX.Y.Z` tag is pushed.
