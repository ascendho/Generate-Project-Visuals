# 生成项目视觉资产

> English guide: [README.md](README.md)

<p align="center">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/releases/latest"><img alt="Latest Release" src="https://img.shields.io/github/v/release/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <a href="https://github.com/ascendho/Generate-Project-Visuals/commits/master"><img alt="Last Commit" src="https://img.shields.io/github/last-commit/ascendho/Generate-Project-Visuals?style=flat-square"></a>
  <a href=".github/workflows/release.yml"><img alt="Release Skill" src="https://github.com/ascendho/Generate-Project-Visuals/actions/workflows/release.yml/badge.svg"></a>
  <a href="plugins/generate-github-cover/skills/generate-github-cover/SKILL.md"><img alt="Codex Skill" src="https://img.shields.io/badge/Codex-Plugin%20%2B%20Skill-412991?style=flat-square&logo=openai&logoColor=white"></a>
</p>

<p align="center">
  <img src="assets/generate-project-visuals-cover-zh.png" alt="生成项目视觉资产中文封面" width="100%">
</p>

Generate Project Visuals 是一个 Codex Plugin 和可独立安装的 Skill。它会读取仓库并生成项目 Logo Mark、Logo Lockup、README Cover、`1280×640` Social Preview 和 `16:9` 宣传图。默认只生成英文图片；其它语言仅在用户明确指定或现有配置已经包含时生成。所有公开图片都按精确尺寸输出为 PNG；SVG 仅用于 Skill 内置模板和 `/tmp` 中的临时 Logo 方案。

项目品牌名为 **Generate Project Visuals**，稳定的 Plugin、Skill 和调用名称仍为 `generate-github-cover`。

## 工作流程

1. Skill 读取仓库规则、文档、包信息、入口代码、配置和现有视觉素材，确定项目定位。
2. Skill 在仓库外创建三个临时 Logo Mark 方向，并展示给用户选择。
3. 用户确认方向后，Skill 渲染并校验最终 Logo Mark 和 Logo Lockup。
4. Skill 写入可编辑的 Cover 配置，再渲染并校验 README Cover、Social Preview 和宣传图；默认只生成英文，用户明确指定时才生成其它语言。

## 安装

渲染器需要 Python 3.10+、Playwright、Segno 和 Chromium。以下示例使用
macOS 和 Linux 常见的 `python3`；如果 `python` 指向 Python 3.10 或更高版本，
也可以使用它。

```sh
python3 -m pip install "playwright==1.61.0" "segno==1.6.6"
python3 -m playwright install chromium
```

Skill 会在创建方案或渲染文件前检查 Python 依赖和 Chromium 运行环境。
如果依赖缺失，它会给出准确的修复命令；未经用户同意不会安装任何依赖。

### Codex Plugin（推荐）

```sh
codex plugin marketplace add ascendho/Generate-Project-Visuals --ref master
codex plugin add generate-github-cover@generate-project-visuals
```

第一条命令将这个 GitHub 仓库注册为 Marketplace 来源，第二条命令从该来源安装 Plugin；不需要先进入官方公开 Plugins Directory。安装后新建一个 Codex 会话，再调用 `$generate-github-cover` 或直接描述匹配的视觉生成任务。

### Release 压缩包（独立安装备用方案）

从 [最新 Release](https://github.com/ascendho/Generate-Project-Visuals/releases/latest) 下载 `generate-github-cover-vX.Y.Z.zip`，使用 `.sha256` 文件校验后解压到用户 Skill 目录：

```sh
shasum -a 256 -c generate-github-cover-vX.Y.Z.zip.sha256
mkdir -p "$HOME/.agents/skills"
unzip generate-github-cover-vX.Y.Z.zip -d "$HOME/.agents/skills"
```

克隆整个仓库主要用于开发。根目录 README、工作流和项目展示图片不会进入独立 Skill 压缩包。

## 使用

```text
请使用 $generate-github-cover，为当前 GitHub 项目生成或更新 Logo，以及中英文 Cover、Social Preview 和宣传图。
```

Skill 会先读取仓库规则、README、包配置、入口代码、相关配置和现有视觉素材，再编写文案和选择视觉隐喻。默认只生成文件；只有用户明确提出时，才会同步 README、GitHub 设置、提交或远程仓库。

未指定语言时，Skill 只生成英文。上面的调用示例明确要求中英文，因此会生成 `en` 和 `zh` 两套图片。用户指定语言集合时，该集合替换英文默认值；如果需要保留现有语言，应明确要求“追加”或“保留”。英文默认使用无后缀文件名，以英文为默认语言时，简体中文使用 `-zh`。

## Cover 配置

Skill 会创建 `assets/<repo-slug>-cover.json`，作为生成图片时可编辑、可复现的源配置。顶层字段保存项目身份与风格选择，`locales` 保存 Cover、Social Preview 和 Promo 的可翻译文案。Skill 会自动生成该配置，用户调用前不需要手工创建。完整字段请查看[仅英文示例](examples/cover-config.en.json)或[中英文示例](examples/cover-config.en-zh.json)。

如果 AI 生成的文案不合适，可以直接修改对应语言下的 `headline`、两条 `description_lines`、`notice` 或 `cta`，然后重新执行 `render --force` 和 `validate`。只修改文案时不需要编辑模板；每个语言配置必须保持完整，`description_lines` 必须始终包含两个字符串。

`source_files` 是来源记录，只填写已经读取并实际用于定位或文案的仓库相对路径；它不会让渲染器自动读取文件。不要加入秘密、缓存、生成物或无关文件。

Cover 是用于 README 的紧凑 `5:1` 横幅，输出尺寸为 `4000x800`；右栏的两行说明应保持简短。可选的 `social_preview` 与 `cover` 结构相同，缺省时回退到 `cover`；当保持 `1280x640` Social Preview 的较长文案时使用该字段。

## 修改文案并重新生成

正常使用时，Skill 会自动写入配置并执行渲染与校验。如果 AI 生成的文案不理想，可以直接让 Skill 修改并重新生成，也可以手工编辑 `assets/<repo-slug>-cover.json` 中的对应语言。通过 Release 压缩包独立安装的用户可随后运行：

```sh
SKILL_DIR="$HOME/.agents/skills/generate-github-cover"

python3 "$SKILL_DIR/scripts/render_cover.py" render \
  assets/<repo-slug>-cover.json --output-dir assets --force

python3 "$SKILL_DIR/scripts/render_cover.py" validate \
  assets/<repo-slug>-cover.json --output-dir assets
```

`--force` 表示有意覆盖现有 PNG，`validate` 用于检查预期文件和精确尺寸。默认语言使用无后缀文件名，其它语言使用 `-<locale>` 后缀。

## 自动发布

`tools/package_skill.py` 会校验 Plugin 版本和 Skill 内容，生成可复现 ZIP 与 SHA-256 校验文件。推送语义化版本标签后，GitHub Actions 会自动发布两份文件：

```sh
# 先将 plugin.json 更新为同一语义化版本并提交。
git tag -a v0.2.1 -m "Generate Project Visuals v0.2.1"
git push origin v0.2.1
```

## 分享图片中的链接

PNG 等位图不能包含可点击区域，因此宣传图会同时显示仓库地址和二维码。在网页中需要点击跳转时，应使用普通链接包裹图片。

## 参与贡献

欢迎通过 Issue 和 Pull Request 提交错误修复、文档改进、渲染器改进或新视觉风格。较大的功能或会改变公开渲染行为的改动，请先创建 Issue 讨论。

新增风格时，请参考 `styles/cover/<style-id>/` 下的现有 [Cover 示例](plugins/generate-github-cover/skills/generate-github-cover/styles/cover/clean-editorial/)，或 `styles/logo/<style-id>/` 下的现有 [Logo 示例](plugins/generate-github-cover/skills/generate-github-cover/styles/logo/clean-geometric/)。临时预览放在 `/tmp`，公开资产保持为 PNG；视觉类 Pull Request 请附验证结果和修改前后对比图。

## 支持与政策

- 支持：[GitHub Issues](https://github.com/ascendho/Generate-Project-Visuals/issues)
- 隐私：[隐私政策](PRIVACY.md)
- 条款：[使用条款](TERMS.md)

## 许可证

本项目采用 [MIT License](LICENSE)。
