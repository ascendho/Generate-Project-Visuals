# Generate Project Visuals

> 中文说明：[README.zh-CN.md](README.zh-CN.md)

<p align="center">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/releases/latest"><img alt="Latest Release" src="https://img.shields.io/github/v/release/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/commits/master"><img alt="Last Commit" src="https://img.shields.io/github/last-commit/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <a href=".github/workflows/release.yml"><img alt="Release Skill" src="https://github.com/ascendho/Generate-Project-Visuals/actions/workflows/release.yml/badge.svg"></a>
  <a href="plugins/generate-github-cover/skills/generate-github-cover/SKILL.md"><img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Plugin%20%2B%20Skill-412991?style=flat-square&logo=openai&logoColor=white"></a>
</p>

<p align="center">
  <img src="assets/generate-project-visuals-cover.png" alt="Generate Project Visuals cover" width="100%">
</p>

Generate Project Visuals is a Codex Plugin and standalone Skill that reads a
repository and creates its Logo Mark, Logo Lockup, English and Simplified
Chinese README Covers, `1280x640` Social Previews, and `16:9` Promo images.
Every public image is exported as PNG at an exact size; SVG is limited to
bundled templates and temporary Logo concepts. Other languages are generated
only when explicitly requested.

The project brand is **Generate Project Visuals**. The stable Plugin, Skill,
and invocation name remains `generate-github-cover`.

## Install

The renderer requires Python 3.10+, Playwright, Segno, and Chromium:

```sh
python -m pip install playwright segno
python -m playwright install chromium
```

### Codex Plugin (recommended)

```sh
codex plugin marketplace add ascendho/Generate-Project-Visuals --ref master
codex plugin add generate-github-cover@generate-project-visuals
```

Start a new Codex thread after installation, then invoke
`$generate-github-cover` or describe a matching visual-generation task.

### Skill Installer

Ask Codex:

```text
Use $skill-installer to install the skill from https://github.com/ascendho/Generate-Project-Visuals/tree/master/plugins/generate-github-cover/skills/generate-github-cover
```

### Local development link

For an editable checkout, run this from the repository root to link the bundled
Skill into the user Skill directory:

```sh
mkdir -p "$HOME/.agents/skills"
ln -s "$PWD/plugins/generate-github-cover/skills/generate-github-cover" \
  "$HOME/.agents/skills/generate-github-cover"
```

Edits in this checkout are then used immediately. Run `git pull` here to sync
remote changes. Start a new Codex thread or restart Codex if an update is not
detected; recreate the link if the repository is moved.

### Release archive

Download `generate-github-cover-vX.Y.Z.zip` from the
[latest Release](https://github.com/ascendho/Generate-Project-Visuals/releases/latest),
verify its `.sha256` file, and extract it into the user Skill directory:

```sh
mkdir -p "$HOME/.agents/skills"
unzip generate-github-cover-vX.Y.Z.zip -d "$HOME/.agents/skills"
```

Cloning the whole repository is intended for development. Repository READMEs,
workflow files, and showcase artwork are deliberately not included in the
standalone Skill archive.

## Use

```text
Use the generate-github-cover skill to create or update this GitHub project's Logo and bilingual English/Chinese Cover, Social Preview, and promotional card.
```

The Skill reads repository guidance, READMEs, package metadata, entry points,
configuration, and existing visuals before writing copy or choosing visual
metaphors. It generates files only unless the user explicitly requests README,
GitHub settings, commit, or remote updates.

English is the unsuffixed default and Simplified Chinese uses `-zh`. An
explicit locale set replaces this default; ask to add or retain a language
when it should be generated alongside English and Chinese.

## Repository layout

```text
assets/                          Project showcase and generated artwork
plugins/generate-github-cover/  Installable Codex Plugin
  .codex-plugin/plugin.json
  skills/generate-github-cover/
    SKILL.md                     Agent workflow
    scripts/                     Renderers and style registry
    references/                 Style-authoring guidance
    styles/
      cover/clean-editorial/    Cover manifest, reference, and templates
      logo/clean-geometric/     Logo manifest and reference
.agents/plugins/marketplace.json
.github/workflows/release.yml    Tag-triggered release automation
tools/package_skill.py           Reproducible Skill packager
```

Reusable templates live inside their self-contained Cover style, not the root
`assets/` directory. Cover and Logo styles are discovered independently, so a
new style can be added as another manifest-backed directory without changing a
central registry.

## Cover specification

Create `assets/<repo-slug>-cover.json` in the target repository. The top level
holds project identity and `locales` holds all translatable Cover and Promo
copy:

```json
{
  "schema_version": 4,
  "cover_style": "clean-editorial",
  "logo_style": "clean-geometric",
  "repository_slug": "example-project",
  "project_name": "Example Project",
  "project_url": "https://github.com/owner/example-project",
  "logo_lockup": "example-project-logo-lockup.png",
  "default_locale": "en",
  "locales": {
    "en": {
      "language": "en",
      "cover": {
        "headline": "A concise editorial statement of the project's value.",
        "description_lines": ["A short concrete statement,", "completed on line two."]
      },
      "social_preview": {
        "headline": "A concise editorial statement of the project's value.",
        "description_lines": ["A longer supporting statement for the wider layout,", "completed naturally on line two."]
      },
      "promo": {
        "headline": "A concise statement for sharing the project.",
        "description_lines": ["A concrete supporting statement,", "completed naturally on line two."],
        "notice": "A short, accurate usage note",
        "cta": "View the project"
      }
    },
    "zh": {
      "language": "zh-CN",
      "cover": {
        "headline": "一句简洁的中文项目价值陈述",
        "description_lines": ["第一行简要说明项目能力，", "第二行自然完成同一句说明。"]
      },
      "social_preview": {
        "headline": "一句简洁的中文项目价值陈述",
        "description_lines": ["第一行完整说明项目定位与核心能力，", "第二行自然完成同一句说明。"]
      },
      "promo": {
        "headline": "一句适合分享的中文项目价值陈述",
        "description_lines": ["第一行具体说明项目能力，", "第二行自然完成同一句说明。"],
        "notice": "简短、准确的使用说明",
        "cta": "扫码查看项目"
      }
    }
  },
  "source_files": ["AGENTS.md", "README.md", "pyproject.toml", "src/example/cli.py"]
}
```

`source_files` is provenance: list only repository-relative files that were
actually read and used. It does not make the renderer load those files. Exclude
secrets, caches, generated output, and unrelated files.

Cover is a compact `5:1` README banner rendered at `4000x800`. Keep its two
supporting lines short for the right column. Optional `social_preview` copy
uses the same shape and falls back to `cover`; use it when the unchanged
`1280x640` Social Preview needs longer wording.

## Render and validate

When developing from this checkout:

```sh
SKILL_DIR=plugins/generate-github-cover/skills/generate-github-cover

python "$SKILL_DIR/scripts/render_cover.py" render \
  assets/<repo-slug>-cover.json --output-dir assets --force

python "$SKILL_DIR/scripts/render_cover.py" validate \
  assets/<repo-slug>-cover.json --output-dir assets
```

The default locale produces `<slug>-cover.png`,
`<slug>-social-preview.png`, and `<slug>-promo.png`. Additional locales use
`-<locale>` suffixes. Copy changes belong in the JSON specification and are
applied by the full `render` command.

## Develop a Logo

Create exactly three temporary Mark concepts named `concept-a.svg`,
`concept-b.svg`, and `concept-c.svg`, then preview them:

```sh
SKILL_DIR=plugins/generate-github-cover/skills/generate-github-cover

python "$SKILL_DIR/scripts/render_logo.py" preview \
  --style clean-geometric \
  --project-name "Example Project" \
  --slug example-project \
  --input-dir /tmp/example-project-logo-source \
  --output-dir /tmp/example-project-logo-preview
```

After the user selects one concept, render and validate it:

```sh
SKILL_DIR=plugins/generate-github-cover/skills/generate-github-cover

python "$SKILL_DIR/scripts/render_logo.py" render \
  --style clean-geometric \
  --project-name "Example Project" \
  --slug example-project \
  --mark /tmp/example-project-logo-source/concept-a.svg \
  --output-dir assets

python "$SKILL_DIR/scripts/render_logo.py" validate \
  --style clean-geometric --slug example-project --output-dir assets
```

This produces only a transparent `1024x1024` Mark PNG and transparent
`3200x800` Lockup PNG. The temporary concept SVGs stay under `/tmp`.

## Releases

`tools/package_skill.py` validates the Plugin version and Skill contents,
creates a reproducible ZIP, and writes its SHA-256 checksum. A semantic version
tag runs the GitHub Actions workflow and publishes both files automatically:

```sh
# First update plugin.json to the same semantic version and commit it.
git tag v0.2.0
git push origin v0.2.0
```

## Links in shared images

Raster images cannot contain clickable regions. Promo images therefore include
the repository address and a QR code. On a web page, wrap the image in an
ordinary link when click-through behavior is needed.

## License

Released under the [MIT License](LICENSE).
