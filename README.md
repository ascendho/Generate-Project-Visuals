# Generate Project Visuals

> 中文说明：[README.zh-CN.md](README.zh-CN.md)

<p align="center">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/commits/master"><img alt="Last Commit" src="https://img.shields.io/github/last-commit/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <a href="SKILL.md"><img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Skill-412991?style=flat-square&logo=openai&logoColor=white"></a>
</p>

<p align="center">
  <img src="assets/generate-project-visuals-cover.png" alt="Generate Project Visuals cover" width="100%">
</p>

This Codex skill reads a GitHub repository and generates its Logo, English and
Simplified Chinese README Covers, 1280x640 Social Preview images, and 16:9
Promo cards. SVG remains editable, while PNG files are rendered at exact output
dimensions. Other language sets can be requested explicitly.

The project is branded as Generate Project Visuals. Its stable skill name and
invocation remain `generate-github-cover`.

## Prerequisites

From the target repository:

```sh
python -m pip install -e ".[cover]"
python -m playwright install chromium
```

## Natural-Language Invocation

```text
Use the generate-github-cover skill to create or update this GitHub project's Logo and bilingual English/Chinese Cover, Social Preview, and promotional card.
```

The skill reads the repository before writing copy or choosing visual
metaphors. It creates files only; it does not update README files, GitHub
settings, commits, or remotes unless explicitly requested.

When no target languages are named, English uses the unsuffixed filenames and
Simplified Chinese uses the `-zh` suffix. An explicit language set replaces
this default; if no default language is named, the first requested language
uses the unsuffixed filenames. Ask to add or retain a language when it should
be generated alongside the default set.

## Cover Specification

Edit the single user-facing file `assets/<repo-slug>-cover.json`. Project
identity stays at the top level; every language keeps its Cover and Promo copy
under `locales`:

```json
{
  "schema_version": 3,
  "style": "clean-editorial",
  "repository_slug": "example-project",
  "project_name": "Example Project",
  "project_url": "https://github.com/owner/example-project",
  "logo_lockup": "example-project-logo-lockup.svg",
  "default_locale": "en",
  "locales": {
    "en": {
      "language": "en",
      "cover": {
        "headline": "A concise editorial statement of the project's value.",
        "description_lines": [
          "A supporting sentence split at a natural phrase boundary,",
          "with the second line completing the same sentence."
        ]
      },
      "promo": {
        "headline": "A concise statement for sharing the project.",
        "description_lines": [
          "One supporting sentence split at a natural boundary,",
          "with its conclusion on line two."
        ],
        "notice": "A short, accurate usage note",
        "cta": "View the project"
      }
    },
    "zh": {
      "language": "zh-CN",
      "cover": {
        "headline": "一句简洁的中文项目价值陈述",
        "description_lines": [
          "第一行简要说明项目的定位与核心能力，",
          "第二行完成同一句说明。"
        ]
      },
      "promo": {
        "headline": "一句适合分享的中文项目价值陈述",
        "description_lines": [
          "第一行简要说明项目的定位与核心能力，",
          "第二行完成同一句说明。"
        ],
        "notice": "简短、准确的使用边界或项目说明",
        "cta": "扫码查看项目"
      }
    }
  },
  "source_files": ["AGENTS.md", "README.md", "pyproject.toml", "src/example/cli.py"]
}
```

Use the headline for a concise editorial positioning statement, then make the
two supporting lines state the project's concrete purpose, workflow, or
outputs. Simplified Chinese image headlines omit a terminal `。` or `.` by
default; supporting copy keeps normal punctuation.

`source_files` records repository-relative files already read and used as
evidence for positioning or copy. It does not make the renderer load those
files. Include `AGENTS.md`, configuration, entry points, or other documentation
only when they materially informed the result; exclude secrets, caches,
generated outputs, and unrelated files.

For another language or RTL output, add a complete locale entry with a tag such as
`"language": "ar"` or `"language": "he"`. The renderer keeps centered text
direction-aware, mirrors the Promo QR/link block, and preserves the GitHub URL
in LTR order.

`logo_lockup` is relative to the JSON file. `default_locale` uses unsuffixed
filenames. The standard default is `en` plus `zh`; add another lowercase locale
key, such as `ja`, `ar`, or `pt-br`, only when that language is requested. The
BCP 47 `language` tag controls font, italic, and LTR/RTL behavior; users
normally edit JSON rather than SVG text.

## Render And Validate

```sh
python skills/generate-github-cover/scripts/render_cover.py render \
  assets/<repo-slug>-cover.json \
  --output-dir assets \
  --force

python skills/generate-github-cover/scripts/render_cover.py validate \
  assets/<repo-slug>-cover.json \
  --output-dir assets
```

The standard outputs are:

- `<slug>-cover.svg/png`: editable Cover and 4096x2048 PNG;
- `<slug>-social-preview.png`: 1280x640 GitHub preview;
- `<slug>-promo.svg/png`: editable default Promo and 3840x2160 PNG;
- `<slug>-cover-<locale>.svg/png`: localized Cover;
- `<slug>-social-preview-<locale>.png`: localized 1280x640 preview;
- `<slug>-promo-<locale>.svg/png`: localized Promo and 3840x2160 PNG.

With the standard bilingual default, the unsuffixed files are English and the
localized files use the `-zh` suffix for Simplified Chinese.

## Manually Update SVG Files

Open an SVG in a text editor, Figma, Illustrator, or Inkscape. Preserve its
`viewBox`, `data-safe-text="true"` or `data-safe-logo="true"` attributes,
filename suffix, and QR quiet zone. Do not add scripts, remote images, external
fonts, `data:` URLs, or unapproved links.

Regenerate PNG files without rewriting the edited SVG:

```sh
# Primary Cover: also refreshes the Social Preview
python skills/generate-github-cover/scripts/render_cover.py rasterize \
  assets/example-project-cover.svg --output-dir assets --force

# Localized Cover: also refreshes its localized Social Preview
python skills/generate-github-cover/scripts/render_cover.py rasterize \
  assets/example-project-cover-zh.svg --output-dir assets --force

# Default and localized promotional cards
python skills/generate-github-cover/scripts/render_cover.py rasterize \
  assets/example-project-promo.svg --output-dir assets --force

python skills/generate-github-cover/scripts/render_cover.py rasterize \
  assets/example-project-promo-zh.svg --output-dir assets --force
```

## Develop A Project Logo

Create exactly three temporary Mark concepts named `concept-a.svg`,
`concept-b.svg`, and `concept-c.svg`. Each uses `viewBox="0 0 512 512"`, a
transparent background, no more than 16 basic geometry elements, and only
`#2855d9`, `#202124`, and `none` for fills and strokes.

```sh
python skills/generate-github-cover/scripts/render_logo.py preview \
  --project-name "Example Project" \
  --slug example-project \
  --input-dir /tmp/example-project-logo-source \
  --output-dir /tmp/example-project-logo-preview
```

After the user explicitly approves one concept, generate the final Logo:

```sh
python skills/generate-github-cover/scripts/render_logo.py render \
  --project-name "Example Project" \
  --slug example-project \
  --mark /tmp/example-project-logo-source/concept-a.svg \
  --output-dir assets
```

Four public files are generated from the same approved concept:

- `<slug>-logo-mark.svg`: editable 512x512 symbol-only Mark;
- `<slug>-logo-mark.png`: transparent 1024x1024 PNG;
- `<slug>-logo-lockup.svg`: editable 1600x400 horizontal Lockup;
- `<slug>-logo-lockup.png`: transparent 3200x800 PNG.

The Mark is intended for avatars, favicons, and small UI. The Lockup combines
the same Mark with the exact project name for horizontal identity use. A
checkerboard shown by an editor indicates transparency and is not part of the
image.

After manually editing the Logo SVG, refresh and validate its PNG:

```sh
python skills/generate-github-cover/scripts/render_logo.py rasterize \
  assets/example-project-logo-mark.svg --output-dir assets --force

python skills/generate-github-cover/scripts/render_logo.py rasterize \
  assets/example-project-logo-lockup.svg --output-dir assets --force

python skills/generate-github-cover/scripts/render_logo.py validate \
  --slug example-project --output-dir assets
```

## Links In Shared Images

Raster images cannot contain clickable regions. The Promo therefore includes a
readable repository address and QR code. Its SVG source also links them, but a
social platform may remove that interaction. On a web page, wrap the image in
a link:

```html
<a href="https://github.com/owner/repository">
  <img src="assets/repository-promo.png" alt="Repository project card">
</a>
```

## License

Released under the [MIT License](LICENSE).
