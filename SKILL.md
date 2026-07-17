---
name: generate-github-cover
description: Analyze a GitHub repository and generate maintainable project Logo Mark and Logo Lockup assets plus complete localized sets of README covers, 1280x640 social previews, and 16:9 promotional cards in a clean editorial style. Generate English and Simplified Chinese artwork by default, or honor an explicitly requested locale set. Use for requests to create, refresh, localize, or standardize project logos, repository banners, Open Graph images, social cards, project covers, or shareable project artwork from repository evidence without asking an image model to typeset the artwork.
---

# Generate GitHub Cover

Create repository artwork from evidence in the repository. Use the current
model for analysis and copywriting, then use the bundled helpers for
deterministic SVG layout and PNG rendering. Do not call an image model in this
version of the skill.

## Cover Workflow

1. Find the repository root, inspect `git status`, and preserve unrelated work.
2. Read every applicable `AGENTS.md`, then inspect primary and
   alternate-language READMEs, package metadata, entry points, relevant
   documentation and configuration, existing visuals, and the Git remote.
3. Write an evidence-based brief: exact project name, audience, workflow,
   differentiator, visual direction, and inspected paths. Track only
   repository-relative files actually used to support the positioning or copy.
   Exclude secrets, caches, generated outputs, and unrelated files. Do not
   invent claims.
4. Read [references/clean-editorial.md](references/clean-editorial.md), then
   write one `assets/<repo-slug>-cover.json`. Put all user-editable copy under
   `locales` and set `source_files` to the evidence list from step 3. Treat
   `source_files` as provenance, not as an automatic file loader; include
   `AGENTS.md` or other documentation only when it informed the result. When
   the user does not specify target languages, create complete `en` and `zh`
   entries, use `language: en` and `language: zh-CN`, and set `default_locale`
   to `en`. When the user explicitly specifies a language set, generate
   exactly that set; use the requested default or the first language listed.
   When the user says to add, retain, or include another language, preserve the
   existing/default locales and append it. Do not infer extra output locales
   merely because translated documentation exists.
   Write a concise, editorial headline that communicates the project's
   positioning, then use the two supporting lines to name its concrete purpose,
   workflow, or outputs. For Simplified Chinese, omit a terminal `。` or `.`
   from image headlines unless the user explicitly requests sentence-style
   punctuation; use normal punctuation in supporting copy.
5. Normalize the repository URL to HTTPS. Ask rather than inventing it when no
   valid GitHub remote is available.
6. Render into a temporary directory first, inspect every format at full size
   and thumbnail size, then revise weak or overflowing copy.

   ```sh
   python skills/generate-github-cover/scripts/render_cover.py render \
     assets/<repo-slug>-cover.json \
     --output-dir /tmp/<repo-slug>-cover-preview
   ```

7. Render approved assets into `assets/` and validate them. Use `--force` only
   when the user explicitly requested an update.

   ```sh
   python skills/generate-github-cover/scripts/render_cover.py validate \
     assets/<repo-slug>-cover.json \
     --output-dir assets
   ```

Use `render_cover.py rasterize` after manually editing a Cover, localized
Cover, or Promo SVG. It must regenerate only the corresponding PNG output and
must not rewrite the SVG.

By default, generate assets only. Do not edit README files, upload GitHub
settings, commit, or push unless the user explicitly requests it.

## Logo Workflow

1. Reuse the repository analysis to identify three distinct project-specific
   visual metaphors. Keep the style geometric and restrained, but do not force
   one fixed symbol language across unrelated projects.
2. Author exactly three temporary `512x512` Mark-only SVG concepts. Use basic
   geometry, transparent backgrounds, and the clean-editorial blue/charcoal
   palette. Do not include text, fonts, gradients, filters, raster images,
   scripts, or external references.
3. Generate and inspect a contact sheet:

   ```sh
   python skills/generate-github-cover/scripts/render_logo.py preview \
     --project-name "Example Project" \
     --slug example-project \
     --input-dir /tmp/example-project-logo-concepts \
     --output-dir /tmp/example-project-logo-concepts
   ```

4. Present all three concepts and stop. Do not choose a winner automatically.
5. After explicit approval, refine the selected concept and generate the two
   canonical forms in SVG and transparent PNG:

   ```sh
   python skills/generate-github-cover/scripts/render_logo.py render \
     --project-name "Example Project" \
     --slug example-project \
     --mark /tmp/example-project-logo-concepts/concept-a.svg \
     --output-dir assets

   python skills/generate-github-cover/scripts/render_logo.py validate \
     --slug example-project \
     --output-dir assets
   ```

6. Do not adopt a Logo in Cover, Promo, or README assets until the user
   confirms it. After confirmation, set `logo_lockup` in the Cover spec to the
   approved Lockup SVG and rerender when the user requests updated artwork.

## Outputs

Cover generation produces a complete set for every configured locale:

- `<slug>-cover.json` as the single editable copy and localization source;
- the default locale as `<slug>-cover.svg/png`, `<slug>-social-preview.png`,
  and `<slug>-promo.svg/png`;
- each additional locale as `<slug>-cover-<locale>.svg/png`,
  `<slug>-social-preview-<locale>.png`, and `<slug>-promo-<locale>.svg/png`.

Without an explicit language request, the default locale is English and the
additional `zh` locale produces the complete Simplified Chinese set with
`-zh` filename suffixes.

Use upright serif headlines for CJK, Arabic, Hebrew, Indic, and other scripts
without reliable italic forms. Keep editorial italics for Latin, Cyrillic, and
Greek scripts. Mirror the Promo link block for RTL languages while keeping the
repository URL itself LTR.

Approved Logo generation produces exactly:

- `<slug>-logo-mark.svg` and transparent `1024x1024` PNG;
- `<slug>-logo-lockup.svg` and transparent `3200x800` PNG.

The Mark is the symbol-only asset for avatars and small UI. The Lockup combines
the same Mark with the exact project name for horizontal identity use. Do not
generate public monochrome or version-suffixed variants.

## Failure Handling

- Report missing Playwright or Chromium instead of switching renderers.
- Shorten copy that cannot fit above the template's minimum type sizes.
- Reject incomplete locale entries instead of mixing languages across outputs.
- Refuse unexpected overwrites.
- Ask for positioning when repository evidence is insufficient.
- Revise Logo concepts that resemble known brands or fail at small sizes.
