---
name: generate-github-cover
description: Analyze a GitHub repository and generate PNG-only Logo Mark, Logo Lockup, README Cover, 1280x640 Social Preview, and 16:9 Promo assets. Generate English artwork by default and additional or alternative locales only when explicitly requested or already configured. Use for requests to create, refresh, localize, or standardize project logos, repository banners, Open Graph images, social cards, Covers, or shareable project artwork from repository evidence.
---

# Generate Project Visuals

Create repository artwork from evidence in the repository. Use the bundled
renderers for deterministic temporary SVG layout and final PNG output. Do not
call an image model in the default workflow.

Resolve `<skill-dir>` to the directory containing this file. The Skill may be
installed through a Plugin, copied into a user Skill directory, or checked out
in a source repository; never assume it is inside the target repository.
Resolve `<python>` to an available Python 3.10+ interpreter, normally `python3`
on Unix-like systems or `python` on Windows, and use that executable for every
command below. Verify the candidate with `<python> --version`; if an unversioned
command is too old, check for a versioned executable such as `python3.11`. If no
compatible interpreter exists, stop and report the requirement.

## Analyze the Repository

1. Find the repository root, inspect `git status`, and preserve unrelated work.
2. Read every applicable `AGENTS.md`, primary and translated READMEs, package
   metadata, entry points, relevant documentation and configuration, existing
   visuals, and the Git remote.
3. Record the exact project name, audience, workflow, differentiator, visual
   direction, and repository-relative files actually used. Exclude secrets,
   caches, generated outputs, unrelated files, and unsupported claims.
4. Normalize the project URL to an HTTPS GitHub repository URL. Ask rather than
   inventing it when no valid remote is available.

## Check the Runtime

After repository analysis succeeds and before creating concepts or rendering
files, run:

```sh
<python> <skill-dir>/scripts/check_runtime.py
```

Continue only when the command reports `"ok": true`. If it fails, show the
reported remediation commands and ask before installing packages or Chromium.
Never install dependencies without the user's approval.

## Select Styles

Use `clean-editorial` for `cover_style` and `clean-geometric` for `logo_style`
unless the user requests another installed style. Read the selected references:

- `styles/cover/<cover-style>/reference.md`
- `styles/logo/<logo-style>/reference.md`

Read [references/style-authoring.md](references/style-authoring.md) only when
adding or changing a reusable style package.

## Create the Logo

1. Derive three distinct, project-specific visual metaphors from the repository.
2. Author exactly three temporary `512x512` Mark SVG inputs named
   `concept-a.svg`, `concept-b.svg`, and `concept-c.svg` under `/tmp`. Follow the
   selected Logo style reference; never place concepts in the repository.
3. Generate and inspect the PNG contact sheet:

   ```sh
   <python> <skill-dir>/scripts/render_logo.py preview \
     --style clean-geometric \
     --project-name "Example Project" \
     --slug example-project \
     --input-dir /tmp/example-project-logo-concepts \
     --output-dir /tmp/example-project-logo-preview
   ```

4. Present all three concepts and stop. Do not select one without user approval.
5. After approval, render and validate the selected concept:

   ```sh
   <python> <skill-dir>/scripts/render_logo.py render \
     --style clean-geometric \
     --project-name "Example Project" \
     --slug example-project \
     --mark /tmp/example-project-logo-concepts/concept-a.svg \
     --output-dir assets

   <python> <skill-dir>/scripts/render_logo.py validate \
     --style clean-geometric --slug example-project --output-dir assets
   ```

Do not adopt a Logo in other artwork until the user confirms it. Public Logo
outputs are only transparent `<slug>-logo-mark.png` at `1024x1024` and
`<slug>-logo-lockup.png` at `3200x800`.

## Create Localized Artwork

Write `assets/<slug>-cover.json` with `schema_version: 4`, explicit
`cover_style` and `logo_style`, the approved Lockup PNG path, and all copy under
`locales`. Use `source_files` only as provenance for files actually read.

For a new specification with no requested languages, create only a complete
`en` entry with `language: en` and `default_locale: en`. Treat locales already
present in an existing specification as explicitly configured and preserve
them. When the user names a language set, generate exactly that set unless the
user asks to add, retain, or include languages. Use `en` as `default_locale`
when present; otherwise use the first language the user names. Translated
documentation alone does not authorize extra locales.

Each locale needs one concise positioning headline and exactly two supporting
lines for Cover and Promo. Optional `social_preview` copy falls back to Cover.
Keep Simplified Chinese headlines free of terminal punctuation unless requested.

Render to `/tmp` first, inspect every PNG at full and thumbnail sizes, then
render approved assets into `assets/` and validate:

```sh
<python> <skill-dir>/scripts/render_cover.py render \
  assets/<slug>-cover.json --output-dir /tmp/<slug>-preview
<python> <skill-dir>/scripts/render_cover.py render \
  assets/<slug>-cover.json --output-dir assets --force
<python> <skill-dir>/scripts/render_cover.py validate \
  assets/<slug>-cover.json --output-dir assets
```

Use `--force` only for an explicitly requested update. The default locale uses
unsuffixed filenames; other locales use `-<locale>`. Each locale produces only:

- `<slug>-cover[-<locale>].png` at `4000x800`;
- `<slug>-social-preview[-<locale>].png` at `1280x640`;
- `<slug>-promo[-<locale>].png` at `3840x2160`.

By default, generate assets only. Do not edit README files, GitHub settings,
commits, tags, or remotes unless the user explicitly requests those actions.

## Failure Handling

- Stop after a failed runtime preflight and report its actionable remediation.
- Reject schema v3, non-PNG Lockups, incomplete locales, unsafe paths,
  unexpected overwrites, invalid PNG transparency, and unsupported styles.
- Shorten copy that cannot fit at the style's minimum type sizes.
- Ask for positioning when repository evidence is insufficient.
- Revise Logo concepts that resemble known brands or fail at small sizes.
