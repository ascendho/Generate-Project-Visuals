# 生成项目视觉资产

> English guide: [README.md](README.md)

<p align="center">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/commits/master"><img alt="Last Commit" src="https://img.shields.io/github/last-commit/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <a href="SKILL.md"><img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Skill-412991?style=flat-square&logo=openai&logoColor=white"></a>
</p>

<p align="center">
  <img src="assets/generate-project-visuals-cover-zh.png" alt="生成项目视觉资产中文封面" width="100%">
</p>

此 Codex Skill 会读取 GitHub 仓库，并生成项目 Logo、中英文 README 封面、`1280×640` Social Preview 和 `16:9` 宣传图。SVG 保持可编辑，PNG 按目标尺寸精确渲染；如需其它语言，可以在请求中明确指定。

项目品牌名为 Generate Project Visuals，稳定的 Skill 名称与调用方式仍为 `generate-github-cover`。

## 环境准备

在目标仓库中运行：

```sh
python -m pip install -e ".[cover]"
python -m playwright install chromium
```

## 自然语言调用

```text
请使用 generate-github-cover skill，为当前 GitHub 项目生成或更新 Logo，以及中英文 Cover、Social Preview 和宣传图
```

Skill 会在编写文案和选择视觉隐喻之前阅读仓库。默认只生成文件，不会修改 README、GitHub 设置、提交或远程仓库，除非用户明确要求。

用户未指定目标语言时，英文使用无后缀文件名，简体中文使用 `-zh` 后缀。用户明确指定语言集合时，该集合会替换默认中英文；如果没有指定默认语言，则请求中列出的第一种语言使用无后缀文件名。若需要在默认中英文基础上扩展，请明确要求“追加”或“保留”相应语言。

## Cover 配置

编辑唯一面向用户的 `assets/<repo-slug>-cover.json`。项目身份信息放在顶层，每种语言的 Cover 和 Promo 文案统一放在 `locales`：

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
          "One supporting sentence split naturally,",
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

标题用于简洁、有质感地概括项目定位，下面两行必须具体说明项目用途、工作方式或输出内容。中文图片标题默认不使用结尾的 `。` 或 `.`，说明文字仍正常使用标点。

`source_files` 记录已经读取、并实际用于项目定位或文案的仓库相对路径；它不会让渲染器自动读取这些文件。只有在确实影响结果时，才记录 `AGENTS.md`、配置、入口代码或其它文档；不要加入秘密、缓存、生成物和无关文件。

如果需要其它语言或 RTL 图片，再添加一份完整 locale，并使用 `"language": "ar"`、
`"language": "he"` 等标签。渲染器会处理居中文字方向、镜像 Promo 的二维码与
链接区域，同时保持 GitHub URL 从左到右显示。

`logo_lockup` 路径相对于 JSON 文件。`default_locale` 使用无语言后缀文件名；标准默认值为 `en` 加 `zh`。只有用户提出需求时，才新增 `ja`、`ar`、`pt-br` 等小写 locale key。BCP 47 `language` 标签用于自动选择字体、斜体策略和 LTR/RTL 方向，通常只需修改 JSON 文案，不必手改 SVG。

## 渲染与校验

```sh
python skills/generate-github-cover/scripts/render_cover.py render \
  assets/<repo-slug>-cover.json \
  --output-dir assets \
  --force

python skills/generate-github-cover/scripts/render_cover.py validate \
  assets/<repo-slug>-cover.json \
  --output-dir assets
```

标准输出包括：

- `<slug>-cover.svg/png`：可编辑 Cover 与 `4096×2048` PNG；
- `<slug>-social-preview.png`：`1280×640` GitHub 预览图；
- `<slug>-promo.svg/png`：默认语言宣传图与 `3840×2160` PNG；
- `<slug>-cover-<locale>.svg/png`：本地化 Cover；
- `<slug>-social-preview-<locale>.png`：本地化的 `1280×640` 预览图；
- `<slug>-promo-<locale>.svg/png`：本地化宣传图与 `3840×2160` PNG。

采用标准双语默认值时，无后缀文件为英文，简体中文文件统一使用 `-zh` 后缀。

## 手动修改 SVG

可以使用文本编辑器、Figma、Illustrator 或 Inkscape 打开 SVG，直接调整文字、位置、颜色、路径或图纹透明度。请保留 `viewBox`、`data-safe-text="true"` 或 `data-safe-logo="true"` 属性、文件名后缀与二维码静区。不要加入脚本、远程图片、外部字体、`data:` URL 或未经允许的链接。

修改后，只重新生成对应 PNG，不会覆盖 SVG：

```sh
# 主 Cover：同时更新 Social Preview
python skills/generate-github-cover/scripts/render_cover.py rasterize \
  assets/example-project-cover.svg --output-dir assets --force

# 中文 Cover：同时更新对应的 Social Preview
python skills/generate-github-cover/scripts/render_cover.py rasterize \
  assets/example-project-cover-zh.svg --output-dir assets --force

# 默认语言与中文宣传图
python skills/generate-github-cover/scripts/render_cover.py rasterize \
  assets/example-project-promo.svg --output-dir assets --force

python skills/generate-github-cover/scripts/render_cover.py rasterize \
  assets/example-project-promo-zh.svg --output-dir assets --force
```

## 设计项目 Logo

先创建三个临时图形 Mark 方案，文件名固定为 `concept-a.svg`、`concept-b.svg` 和 `concept-c.svg`。每个文件使用 `viewBox="0 0 512 512"`、透明背景、不超过 16 个基础图形元素，并且填充和描边只使用 `#2855d9`、`#202124` 与 `none`。

```sh
python skills/generate-github-cover/scripts/render_logo.py preview \
  --project-name "Example Project" \
  --slug example-project \
  --input-dir /tmp/example-project-logo-source \
  --output-dir /tmp/example-project-logo-preview
```

用户明确选择一个方案后，再生成最终 Mark 与 Lockup：

```sh
python skills/generate-github-cover/scripts/render_logo.py render \
  --project-name "Example Project" \
  --slug example-project \
  --mark /tmp/example-project-logo-source/concept-a.svg \
  --output-dir assets
```

最终保留四个公开文件：

- `<slug>-logo-mark.svg`：可编辑的 `512×512` 纯图形 Mark；
- `<slug>-logo-mark.png`：透明的 `1024×1024` PNG；
- `<slug>-logo-lockup.svg`：可编辑的 `1600×400` 横向 Lockup；
- `<slug>-logo-lockup.png`：透明的 `3200×800` PNG。

Mark 用于头像、favicon 和小尺寸界面；Lockup 使用同一图形并组合精确的项目名，用于横向品牌展示。编辑器显示的棋盘格代表透明区域，并不是图片内容。

手动修改 Logo SVG 后，可以只更新 PNG 并重新校验：

```sh
python skills/generate-github-cover/scripts/render_logo.py rasterize \
  assets/example-project-logo-mark.svg --output-dir assets --force

python skills/generate-github-cover/scripts/render_logo.py rasterize \
  assets/example-project-logo-lockup.svg --output-dir assets --force

python skills/generate-github-cover/scripts/render_logo.py validate \
  --slug example-project --output-dir assets
```

## 分享图片中的链接

上传到社交平台的 PNG 或 JPEG 不能包含可点击区域，因此宣传图会同时显示项目地址和二维码。SVG 源文件也会给地址和二维码添加链接，但平台转为位图后可能丢失交互。在允许 HTML 的网页中，可以直接给图片包裹链接：

```html
<a href="https://github.com/owner/repository">
  <img src="assets/repository-promo.png" alt="项目宣传图">
</a>
```

## 许可证

本项目采用 [MIT License](LICENSE)。
