---
name: modsync-design
description: Use this skill to generate well-branded interfaces and assets for ModSync, the multi-mod installer for Knights of the Old Republic games, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_DESIGN_ROOT`. Read the [bundle index](../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

Read the README.md file within this skill, and explore the other available files.
If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.
If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick reference
- **Three themes, one app.** K1 (deep-space blue, the default `:root`), TSL (jade/teal, `.theme-tsl`), Light (Windows installer, `.theme-light`). Always build from the semantic tokens in `tokens/colors.css` (`--surface-card`, `--text-primary`, `--brand-accent`, …) so designs re-skin automatically.
- **Fonts** are system stacks (no webfonts): Verdana for KOTOR themes, Segoe UI for Light, Consolas for code — see `tokens/typography.css`.
- **Components** load from `_ds_bundle.js` under `window.ModSyncDesignSystem_2b35e3`; link `styles.css` first. See `components/*/*.prompt.md` for usage.
- **Brand mark**: `assets/modsync-mark-k1.png` / `assets/modsync-mark-tsl.png` (recolor per theme).
- **Full app recreation** to crib from: `ui_kits/modsync-app/index.html`.
- **Voice**: warm, second-person, sentence-case body / Title Case actions, sparing emoji for wayfinding.
