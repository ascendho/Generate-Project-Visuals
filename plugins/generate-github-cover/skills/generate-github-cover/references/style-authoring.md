# Adding Visual Styles

Add Cover and Logo styles independently under `styles/cover/<style-id>/` and
`styles/logo/<style-id>/`. Use lowercase hyphenated identifiers and keep the
manifest `id` identical to its directory name.

A Cover style requires `style.json`, `reference.md`, and `templates/cover.svg`,
`templates/social.svg`, and `templates/promo.svg`. Preserve the placeholder
contract used by the existing templates, declare all artboard sizes, safe boxes,
fit limits, identity placement, and palette values in the manifest, and validate
every supported locale at full and thumbnail sizes.

A Logo style requires `style.json` and `reference.md`. Declare its palette,
Mark and Lockup viewboxes, PNG sizes, geometry limit, wordmark layout, and contact
sheet size. Keep candidate validation deterministic and explain style-specific
concept rules in the reference.

The registry discovers valid style manifests automatically. Do not add a Python
registry entry. Change the renderers only when a new style requires a genuinely
new layout primitive rather than different templates or manifest values.
