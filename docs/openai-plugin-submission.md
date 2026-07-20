# OpenAI Plugin Submission Packet

This packet contains the final copy and reviewer scenarios for the initial
public-directory submission of Generate Project Visuals version `0.2.1`.

## Submission type

- Type: Skills only
- Authentication: None
- MCP server: None
- Reviewer credentials: Not required
- Category: Productivity
- Country availability: All countries and regions offered by the submission
  portal where the publisher can provide English-language support

## Info

- Plugin name: Generate Project Visuals
- Developer identity: Asc Ho
- Short description: Create logos, covers, and social artwork.
- Long description: Analyze a repository, propose three logo directions for
  approval, and render validated PNG logo marks, lockups, README covers, social
  previews, and promo artwork. Generate English by default and localized
  variants only when requested or already configured.
- Website: https://github.com/ascendho/Generate-Project-Visuals
- Support: https://github.com/ascendho/Generate-Project-Visuals/issues
- Privacy policy: https://github.com/ascendho/Generate-Project-Visuals/blob/master/PRIVACY.md
- Terms of service: https://github.com/ascendho/Generate-Project-Visuals/blob/master/TERMS.md
- Logo: `plugins/generate-github-cover/assets/icon.png`

Verify that every public URL above loads without authentication before
submitting the draft.

## Skills

Upload `generate-github-cover-v0.2.1.zip`. The archive contains the final
`generate-github-cover/` Skill tree, its scripts, style packages,
`requirements.txt`, agent metadata, and MIT License. It does not contain the
repository READMEs, showcase images, release workflow, or this submission
packet.

The runtime requires Python 3.10 or later, `playwright==1.61.0`,
`segno==1.6.6`, and the Chromium version installed by Playwright. The Skill
runs its non-mutating runtime preflight before creating or rendering assets and
does not install dependencies without user approval.

## Starter prompts

1. Create this repository's logo and English visual asset set.
2. Refresh this repository's cover and social preview without changing its logo.
3. Create English and Simplified Chinese visual assets for this repository.

## Reviewer fixture

Use a fresh, writable, disposable clone of the public `v0.2.0` fixture for each
test:

```sh
git clone --branch v0.2.0 --depth 1 \
  https://github.com/ascendho/Generate-Project-Visuals.git
```

Install the pinned runtime dependencies and Chromium before the tests. No
account, secret, private network, or external fixture data is required. When a
test calls for a clean visual state, remove only the existing
`assets/generate-project-visuals-*` files from the disposable clone.

## Positive test cases

### 1. Create the default English asset set

- User prompt: "Use $generate-github-cover to create this repository's logo and English visual asset set."
- Fixture: Clean visual state in a disposable fixture clone.
- Expected workflow: Inspect repository evidence, create exactly three
  temporary logo concepts outside the repository, present them, and stop for a
  selection. After the reviewer selects concept A, render and validate the
  approved logo and English artwork.
- Expected result: `generate-project-visuals-logo-mark.png` at `1024x1024`,
  `generate-project-visuals-logo-lockup.png` at `3200x800`, an editable Cover
  JSON file, and unsuffixed Cover, Social Preview, and Promo PNGs at their
  documented sizes.

### 2. Create an English and Simplified Chinese asset set

- User prompt: "Use $generate-github-cover to create this repository's logo plus English and Simplified Chinese Cover, Social Preview, and Promo assets."
- Fixture: Clean visual state in a disposable fixture clone.
- Expected workflow: Follow the same three-concept approval boundary, then
  create complete `en` and `zh` locale entries with English as the default.
- Expected result: The two approved logo PNGs, three unsuffixed English PNGs,
  three `-zh` PNGs, and a configuration containing complete `en` and `zh`
  locales.

### 3. Refresh copy without changing the logo

- User prompt: "Keep the approved logo unchanged. Change the English headline to 'Design the identity. Ship the story.' and explicitly overwrite only the English Cover, Social Preview, and Promo images."
- Fixture: Unmodified disposable fixture clone with its existing configuration
  and generated assets.
- Expected workflow: Reuse the configured Lockup, update only English copy,
  render with the explicit overwrite authorization, and validate the three
  English outputs.
- Expected result: The English Cover, Social Preview, and Promo PNGs and their
  configuration copy change; logo files and Simplified Chinese outputs remain
  byte-for-byte unchanged.

### 4. Create only a logo

- User prompt: "Use $generate-github-cover to create only a new logo for this repository."
- Fixture: Clean visual state in a disposable fixture clone.
- Expected workflow: Create and present exactly three temporary Mark concepts,
  then stop. After the reviewer selects concept B, render and validate only the
  Mark and Lockup.
- Expected result: Two transparent logo PNGs at the documented dimensions; no
  Cover configuration, Cover, Social Preview, or Promo is created.

### 5. Refresh only the Simplified Chinese artwork

- User prompt: "Keep the approved logo and all English assets unchanged. Refresh only the Simplified Chinese Cover, Social Preview, and Promo copy and images."
- Fixture: Unmodified disposable fixture clone with its existing bilingual
  configuration and generated assets.
- Expected workflow: Preserve the approved Lockup and `en` locale, revise the
  `zh` locale, explicitly replace only the three `-zh` PNGs, and validate them.
- Expected result: Only the Simplified Chinese configuration copy and three
  `-zh` PNGs change; English and logo files remain byte-for-byte unchanged.

## Negative test cases

### 1. Missing GitHub repository URL

- User scenario: Remove the fixture clone's `origin` remote, then ask the Skill
  to create the complete asset set without supplying a project URL.
- Expected behavior: Ask for a valid HTTPS GitHub repository URL before
  creating concepts, QR codes, configuration, or output files.
- Why the action is not completed: The Skill must not invent project identity
  or publish a fabricated destination.

### 2. Secret requested in artwork

- User scenario: Add a fake `.env` file to the disposable fixture and ask the
  Skill to place its API key in the Promo image and QR code.
- Expected behavior: Refuse to expose the value, exclude `.env` from
  `source_files`, and explain that secrets cannot be used as artwork content.
- Why the action is not completed: Exposing credentials would violate the
  Skill's data-minimization and security boundary.

### 3. Public SVG-only output requested

- User prompt: "Publish the final logo, cover, social preview, and promo only as SVG files."
- Expected behavior: Explain the PNG-only public output contract and offer the
  supported PNG outputs. Temporary SVG logo concepts may exist only outside
  the repository for review.
- Why the action is not completed: Public SVG files are outside the plugin's
  documented, validated output contract.

## Release notes

Initial public-directory submission of Generate Project Visuals. This
skills-only plugin analyzes a repository, proposes three logo directions for
approval, and renders validated PNG logo, README cover, social preview, and
promo assets. Version 0.2.1 adds public submission metadata, privacy and terms
pages, pinned rendering dependencies, and an explicit runtime preflight. No
MCP server, authentication, or reviewer credentials are required.

## Final portal checklist

- Select the verified individual developer identity `Asc Ho`.
- Confirm the submitter has Apps Management write access.
- Upload the final `v0.2.1` Skill ZIP.
- Enter exactly the three starter prompts, five positive tests, and three
  negative tests above.
- Select all eligible countries and regions where English support is ready.
- Review every policy attestation against the uploaded Skill and public pages.
- Submit for review; after approval, return to the portal and select Publish.
