# Repository Guidelines

## Project Structure & Module Organization

- `plugins/generate-github-cover/` is the installable Codex Plugin.
- `plugins/generate-github-cover/skills/generate-github-cover/` contains `SKILL.md`, render scripts, style-authoring guidance, and independently discoverable `styles/cover/` and `styles/logo/` packages.
- `assets/` contains this repository's PNG Logo, Cover, Social Preview, and Promo files plus Cover source JSON; do not place reusable templates or generated SVGs there.
- `.agents/plugins/marketplace.json` exposes the Plugin through the repository marketplace.
- `tools/package_skill.py` builds the standalone Skill archive; `.github/workflows/release.yml` publishes tagged releases.
- `README.md` and `README.zh-CN.md` are synchronized user guides.

Keep temporary concepts and previews under `/tmp`, never in the repository.

## Build, Test, and Development Commands

There is no separate build step. Install runtime dependencies and Chromium:

```sh
python3 -m pip install playwright==1.61.0 segno==1.6.6
python3 -m playwright install chromium
```

Use the nested renderers from the repository root:

```sh
SKILL_DIR=plugins/generate-github-cover/skills/generate-github-cover
python3 -m py_compile "$SKILL_DIR"/scripts/*.py tools/package_skill.py
python3 "$SKILL_DIR/scripts/render_cover.py" render \
  assets/<slug>-cover.json --output-dir /tmp/<slug>-preview
python3 "$SKILL_DIR/scripts/render_cover.py" validate \
  assets/<slug>-cover.json --output-dir assets
python3 "$SKILL_DIR/scripts/render_logo.py" validate \
  --style clean-geometric --slug <slug> --output-dir assets
python3 tools/package_skill.py v0.2.1 --check-only
```

Use `render_logo.py preview` and `render` with an explicit `--style`. Add `--force` only when replacing generated PNGs intentionally.

## Coding Style & Naming Conventions

Use four-space Python indentation, type hints, `pathlib.Path`, uppercase module constants, `snake_case` functions, and leading underscores for internal helpers. Raise `CoverError`, `LogoError`, `StyleError`, or `PackageError` with actionable messages. Use lowercase hyphenated names such as `example-project-cover-zh.png` and `styles/cover/clean-editorial/`. Preserve template placeholders, declared viewboxes, safe areas, and manifest palettes.

## Testing Guidelines

No coverage threshold is defined. Every change must pass Python compilation, Skill and Plugin structure validation, affected CLI paths, and generated-asset validation. Inspect public PNG output at full and thumbnail sizes; internal SVG templates and temporary sources must stay out of `assets/`. For packaging changes, build into `/tmp`, inspect archive contents, verify the checksum, and confirm repository docs, caches, and showcase artwork are excluded.

## Commit & Pull Request Guidelines

Follow the existing short, imperative style, for example `Package skill releases`. Keep commits focused. Pull requests should describe behavior, list validation commands, link issues, and include before/after images for visual changes. Never commit caches, temporary previews, or unapproved Logo concepts. A release commit must update the Plugin version before the matching `vX.Y.Z` tag is pushed.
