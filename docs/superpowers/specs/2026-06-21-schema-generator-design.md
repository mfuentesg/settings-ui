# Schema Generator Design

**Date:** 2026-06-21
**Status:** Approved

## Problem

`schema.py` is hand-curated. New Sublime Text settings require manual additions. The
`schema_loader.py` runtime fallback auto-discovers uncatalogued keys but produces
low-quality entries (raw key names, wrong widget types, no grouping).

## Goal

A generator command that builds `schema.py` from `Default/Preferences.sublime-settings`,
grouped into logical sections, with accurate widget types — while preserving existing
curated entries and keeping the runtime fallback as a safety net for future ST updates.

## Architecture

```
tools/
  gen_schema.py       ← ST plugin command (settings_ui_generate_schema)
  section_map.json    ← hand-maintained key→section overrides
schema.py             ← generated+curated schema (source of truth)
schema_loader.py      ← runtime fallback (unchanged role)
```

`gen_schema.py` is a Sublime Text plugin file (not a standalone script) so it can call
`sublime.load_resource()` directly. The command is run from the command palette by the
developer when needed.

## Generator Behaviour

### Input

`sublime.load_resource("Packages/Default/Preferences.sublime-settings")` — JSONC text
loaded directly inside ST. No copy-paste step required.

Platform-specific overrides are also loaded and merged:
`Packages/Default/Preferences (OSX|Windows|Linux).sublime-settings`

### Parsing

- Strip `//` line comments → `json.loads()` for values dict
- Walk lines to extract the comment block above each key → descriptions dict
  (reuse the existing `_parse_descriptions` logic from `schema_loader.py`)

### Modes

**Incremental (default):** reads current `schema.py`, skips any key already in
`KEY_INDEX`, appends new entries to their assigned sections. Existing curated entries
are never modified.

**Full (command arg `{"full": true}` or first run when `schema.py` is absent):** regenerates
`schema.py` entirely from the prefs dump, discarding any prior content. Invoked via
`window.run_command("settings_ui_generate_schema", {"full": True})` from the console.

### Output

Writes valid Python to `schema.py` — a file that can be dropped in place of the
existing one. Entries use the existing constructor helpers (`b`, `e`, `n`, `s`, `j`,
`pk`, `rp`, `lp`). Helper functions and `KEY_INDEX` are preserved verbatim (not
regenerated).

## Type Inference

Priority order per key:

1. **Exact key-name match** — rich widget type:
   - `color_scheme` → `pk(..., "select_color_scheme")`
   - `light_color_scheme`, `dark_color_scheme` → `rp(..., "color_scheme")`
   - `theme` → `pk(..., "select_theme")`
   - `light_theme`, `dark_theme` → `rp(..., "theme")`
   - `font_face` → `lp(..., "fonts")`

2. **Comment-based enum detection** — if the comment above a key contains 2–6
   double-quoted tokens (e.g. `"word"`, `"line"`, `"character"`), emit `e()` with
   those tokens as choices and the first as the default.

3. **Value-type fallback:**
   - `bool` → `b()`
   - `int` → `n(step=1)`
   - `float` → `n(step=0.5, is_float=True)`
   - `str` → `s()`
   - `list` / `dict` / `null` → `j()`

**Title:** `key.replace("_", " ").title()`
**Description:** comment text above the key in the prefs file.

## Section Grouping

Priority order:

1. **`tools/section_map.json` exact key match** — overrides everything.
   Format: `{"hot_exit": "APPLICATION › BEHAVIOR", ...}`

2. **Prefix rules** (longest prefix wins):

| Prefix / pattern | Section |
|---|---|
| `auto_complete_*` | `EDITOR › COMPLETION` |
| `find_*` | `EDITOR › FIND` |
| `font_*` | `APPEARANCE › FONT` |
| `color_scheme`, `*_color_scheme` | `APPEARANCE › COLOR SCHEME` |
| `theme`, `*_theme` | `APPEARANCE › THEME` |
| `spell_check`, `spelling_*`, `dictionary` | `EDITOR › SPELL CHECK` |
| `scroll_*` | `EDITOR › SCROLLING` |
| `match_*` | `EDITOR › BRACKETS & TAGS` |
| `caret_*`, `line_padding_*` | `EDITOR › CARET & LINE` |
| `ruler_*` | `EDITOR › RULERS` |
| `index_*`, `goto_*`, `folder_*`, `file_*`, `binary_*`, `image_*` | `FILES › INDEXING & SIDEBAR` |
| `trim_*`, `ensure_newline_*`, `save_*` | `FILES › SAVE` |
| `vintage_*` | `PACKAGES › VINTAGE` |
| `word_*`, `wrap_*` | `EDITOR › WORD WRAP` |
| `draw_*`, `control_character_*` | `EDITOR › WHITE SPACE` |
| `tab_size`, `translate_*`, `detect_*`, `auto_indent`, `smart_indent`, `indent_*`, `shift_tab_*` | `EDITOR › INDENTATION` |
| `show_*` | `STATUS BAR` |
| `auto_hide_*`, `reveal_*`, `hide_pointer_*` | `UI › AUTO HIDE` |

3. **Unmapped** → `OTHER`

## Settings Lifecycle & Event Handlers

ST's API is unavailable at module import time. `sublime.load_resource()` and
`sublime.load_settings()` may only be called from `plugin_loaded()` onward.

**Generator command:** `run()` executes after `plugin_loaded()` by ST's plugin system —
`load_resource()` is always safe there. The prefs file is ~50KB; no stutter risk.

**Startup sequence (runtime):**
```
plugin_loaded()
  └─ panel.render()
       └─ schema_loader.ensure_schema_loaded()   ← safe: post-load
            ├─ load_resource(Default/Preferences…) → patch defaults
            └─ auto-generate OTHER entries for unknown keys
```

**Reactive schema patching:** `schema_loader.py` should register
`Preferences.sublime-settings` via `add_on_change("settings_ui_schema", callback)`
so that if ST updates the prefs file at runtime (e.g. after an ST update installs), the
schema defaults are re-patched without requiring a full plugin reload. The existing
`_schema_loaded = False` reset in `plugin_unloaded()` already handles hot-reload
correctly; this adds coverage for in-session updates.

`clear_on_change("settings_ui_schema")` must be called in `plugin_unloaded()` to
avoid stale listeners.

## Runtime Fallback

`schema_loader.py` remains unchanged in role: it patches real defaults into curated
entries and appends auto-generated OTHER entries for any key not in `KEY_INDEX` at
runtime. This means new ST settings appear immediately in the UI (in OTHER) before
the generator is re-run to give them proper grouping and type.

## Developer Workflow

1. Sublime Text updates → new settings appear in OTHER section automatically.
2. Developer runs `settings_ui_generate_schema` from command palette.
3. Generator adds new entries to `schema.py` with inferred types and sections.
4. Developer reviews diff: improve titles, descriptions, presets where auto-gen fell short.
5. Commit.

## Out of Scope

- Automatic detection of `presets` arrays for numeric settings (must be added manually).
- Grouping within a section (order within a section is insertion order from prefs file).
- Any UI changes to the settings panel itself.
