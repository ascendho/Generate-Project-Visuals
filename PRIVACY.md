# Privacy Policy

Effective date: July 20, 2026

Generate Project Visuals is an open-source, skills-only plugin published by
Asc Ho. This policy describes the data handling performed by the plugin and
its bundled `generate-github-cover` Skill.

## Data the Skill processes

When a user invokes the Skill, it may process only the information the user
makes available in the active ChatGPT or Codex workspace, including:

- repository guidance, documentation, package metadata, source files,
  configuration, and existing visual assets;
- the repository's public GitHub URL and project metadata;
- user prompts, language choices, copy revisions, and logo selections; and
- generated configuration files, temporary logo concepts, and PNG outputs.

The Skill instructs the agent to exclude secrets, credentials, caches,
unrelated files, and unsupported claims from its analysis and generated
artwork.

## Developer collection and storage

The plugin has no developer-operated service, account system, analytics,
advertising, or telemetry. Its bundled Python scripts render local inputs and
do not send repository content or generated assets to a service controlled by
Asc Ho. Asc Ho does not receive or retain user prompts, repository contents, or
generated files through the plugin.

Generated files remain in the user's active workspace or repository until the
user moves or deletes them. Temporary logo concepts are created outside the
repository and remain subject to the retention and cleanup behavior of the
user's environment.

## OpenAI, GitHub, and local dependencies

Use of the plugin inside ChatGPT or Codex is also subject to the data handling,
retention, and administrative controls of the applicable OpenAI product and
account. If the user makes GitHub content available through a repository,
connector, or other integration, that access is also governed by the user's
GitHub and OpenAI settings.

Playwright and a local Chromium installation are used to rasterize bundled
templates, and Segno is used to generate QR codes. These dependencies run in
the user's execution environment. The QR code contains the public repository
URL supplied for the project.

## Security and user control

The Skill previews three logo directions before adopting one, refuses
unexpected overwrites, and does not edit README files, GitHub settings,
commits, tags, or remotes unless the user explicitly requests those actions.
Users should review generated copy and images before publishing them.

## Changes to this policy

Material changes will be published in this repository with an updated
effective date.

## Contact

For privacy questions or requests, open an issue at
<https://github.com/ascendho/Generate-Project-Visuals/issues>.
