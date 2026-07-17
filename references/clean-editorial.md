# Clean Editorial

Use this reference when writing the Cover specification or reviewing output.

## Specification

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
        "description_lines": ["One supporting sentence split naturally,", "with its conclusion on line two."],
        "notice": "A short, accurate project boundary or usage note",
        "cta": "View the project"
      }
    },
    "zh": {
      "language": "zh-CN",
      "cover": {
        "headline": "一句简洁的中文项目价值陈述",
        "description_lines": ["第一行简要说明项目的定位与核心能力，", "第二行完成同一句说明。"]
      },
      "promo": {
        "headline": "一句适合分享的中文项目价值陈述",
        "description_lines": ["第一行简要说明项目的定位与核心能力，", "第二行完成同一句说明。"],
        "notice": "简短、准确的使用边界或项目说明",
        "cta": "扫码查看项目"
      }
    }
  },
  "source_files": ["AGENTS.md", "README.md", "pyproject.toml", "src/example/cli.py"]
}
```

Rules:

- Use a lowercase hyphenated `repository_slug` and preserve the official
  capitalization of `project_name`.
- When the user does not name target languages, create exactly `en` and `zh`,
  use `language: en` and `language: zh-CN`, and set `default_locale` to `en`.
- When the user explicitly names a language set, generate exactly that set and
  use the requested default or the first language listed. Preserve existing or
  default locales only when the user asks to add, retain, or include them.
- Do not infer extra output locales from translated repository documentation.
- Keep all translatable copy in `locales`; `default_locale` must name one entry.
- Each locale requires a BCP 47 `language`, complete Cover copy, and complete
  Promo copy. Keep one concise headline and exactly two supporting lines.
- Make the headline an editorial positioning statement rather than a feature
  list. Use the two supporting lines to identify the project's concrete
  purpose, workflow, or outputs so a first-time viewer knows what it does.
- Omit terminal `。` and `.` from Simplified Chinese image headlines by
  default. Keep normal punctuation in supporting copy and honor explicit user
  requests for a different headline style.
- `project_url` must be an HTTPS GitHub repository URL without credentials,
  query parameters, or fragments.
- `logo_lockup` is optional. It must reference a validated `1600x400` Lockup
  SVG inside the specification directory.
- The default locale uses unsuffixed filenames. Every other locale key creates
  a Cover, Social Preview, and Promo with that suffix.
- Treat `source_files` as provenance, not as an automatic loader. Record only
  repository-relative files already read and actually used to support the
  positioning or copy. Include `AGENTS.md` and other documentation when they
  informed the result; exclude secrets, caches, generated outputs, unrelated
  files, and unsupported claims.

## Visual System

- Cover: `2048x1024` SVG, rendered at `4096x2048` and `1280x640`.
- Promo: `1920x1080` SVG, rendered at `3840x2160`.
- White background, blue `#2855d9` accent, charcoal `#202124` primary text.
- Modern sans-serif project identity; serif editorial headline.
- Use true or well-supported italics only for Latin, Cyrillic, and Greek.
  Render CJK and other scripts upright; mirror link layout for RTL languages.
- Restrained contour linework around the perimeter, clear of text and QR.
- Cover safe area: x=`128..1920`, y=`128..896`.
- Promo safe area: x=`120..1800`, y=`100..980`.

This is one stable style. Update it in place; do not add version suffixes.
Avoid mascots, screenshots, gradients, external fonts, remote images, and
image-model assets unless the user explicitly approves an extension.

## Logo System

Create three repository-specific concepts from distinct metaphors found in the
project. Keep the execution style simple and geometric, but do not reuse one
fixed bracket, path, node, letter, or AI symbol across unrelated projects.

Candidate Mark requirements:

- exact `viewBox="0 0 512 512"` and transparent background;
- only basic SVG geometry, with no more than 16 visible elements;
- only `#2855d9`, `#202124`, and `none` for fill and stroke;
- no text, fonts, gradients, masks, filters, embedded data, scripts, external
  references, or animation;
- recognizable in color, monochrome inspection, and at 16px.

Avoid generic brains, robots, sparkles, neural-network heads, chat bubbles,
glowing circuits, and visual similarity to established brands. Do not use an
image model in the default workflow.

Final outputs use the same approved geometry:

- Logo Mark: `512x512` SVG and transparent `1024x1024` PNG, with no text.
- Logo Lockup: `1600x400` SVG and transparent `3200x800` PNG, combining the
  Mark with the exact project name in editable bold system-sans text.

Transparency viewers may show a checkerboard behind PNG or SVG files. That
checkerboard is editor UI, not image content; do not add a white rectangle to
hide it.
