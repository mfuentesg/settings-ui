# Schema Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `settings_ui_generate_schema` ST command that regenerates `schema.py` from the live `Default/Preferences.sublime-settings`, preserving curated entries and adding reactive default-patching to `schema_loader.py`.

**Architecture:** All logic lives in `schema_gen.py` (pure Python, no ST imports, fully testable). `gen_schema.py` is a thin ST command wrapper that feeds live ST data into `schema_gen` and writes the result. `tools/section_map.json` provides hand-maintained key→section overrides. When run, the command preserves existing curated entries from `schema.KEY_INDEX` and auto-generates entries only for keys not yet catalogued.

**Tech Stack:** Python 3.8 (ST4), pytest (tests outside ST), Sublime Text API (`sublime.load_resource`, `sublime.load_settings`, `Settings.add_on_change`)

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `schema_gen.py` | Create | Pure logic: JSONC parsing, type inference, section assignment, code generation |
| `gen_schema.py` | Create | ST WindowCommand wrapper; feeds live data into schema_gen, writes schema.py |
| `tools/section_map.json` | Create | Hand-maintained key→section overrides |
| `tests/__init__.py` | Create | Empty; marks tests as a package for pytest |
| `tests/conftest.py` | Create | Adds package root to sys.path so schema_gen is importable |
| `tests/test_schema_gen.py` | Create | Unit tests for all pure functions |
| `Default.sublime-commands` | Modify | Add `settings_ui_generate_schema` command entry |
| `schema_loader.py` | Modify | Add `add_on_change` reactive listener + `unregister_listener()` |
| `SettingsUI.py` | Modify | Call `schema_loader.unregister_listener()` in `plugin_unloaded` |

---

## Task 1: Create `tools/section_map.json`

**Files:**
- Create: `tools/section_map.json`

Section names must match titles in `schema.py` exactly (including the `›` character, U+203A).
This file covers every key from the existing schema that would be misassigned by prefix rules alone.

- [ ] **Step 1: Create the file**

```json
{
    "themed_title_bar": "APPEARANCE › THEME",
    "file_tab_style": "APPEARANCE › THEME",
    "inactive_sheet_dimming": "APPEARANCE › THEME",
    "tree_animation_enabled": "APPEARANCE › THEME",
    "animation_enabled": "APPEARANCE › THEME",
    "highlight_modified_tabs": "APPEARANCE › THEME",
    "show_tab_close_buttons": "APPEARANCE › THEME",
    "show_tab_close_buttons_on_left": "APPEARANCE › THEME",
    "bold_folder_labels": "APPEARANCE › THEME",
    "adaptive_dividers": "APPEARANCE › THEME",
    "popup_shadows": "APPEARANCE › THEME",
    "native_tabs": "APPEARANCE › THEME",
    "open_tabs_after_current": "APPEARANCE › THEME",
    "overlay_scroll_bars": "APPEARANCE › THEME",
    "enable_tab_scrolling": "APPEARANCE › THEME",
    "hide_tab_scrolling_buttons": "APPEARANCE › THEME",
    "hide_new_tab_button": "APPEARANCE › THEME",
    "show_sidebar_button": "APPEARANCE › THEME",
    "sidebar_on_right": "APPEARANCE › THEME",
    "ui_scale": "APPEARANCE › THEME",
    "hardware_acceleration": "APPEARANCE › THEME",

    "line_numbers": "EDITOR › GUTTER",
    "relative_line_numbers": "EDITOR › GUTTER",
    "gutter": "EDITOR › GUTTER",
    "margin": "EDITOR › GUTTER",
    "fold_buttons": "EDITOR › GUTTER",
    "fade_fold_buttons": "EDITOR › GUTTER",
    "fold_style": "EDITOR › GUTTER",
    "mini_diff": "EDITOR › GUTTER",

    "block_caret": "EDITOR › CARET & LINE",
    "highlight_line": "EDITOR › CARET & LINE",
    "highlight_gutter": "EDITOR › CARET & LINE",
    "highlight_line_number": "EDITOR › CARET & LINE",

    "selection_description_column_type": "EDITOR › WHITE SPACE",

    "move_to_limit_on_up_down": "EDITOR › SCROLLING",

    "draw_minimap_border": "EDITOR › MINIMAP",
    "always_show_minimap_viewport": "EDITOR › MINIMAP",
    "minimap_horizontal_scrolling": "EDITOR › MINIMAP",

    "show_definitions": "EDITOR › COMPLETION",
    "tab_completion": "EDITOR › COMPLETION",
    "syntax_detection_size_limit": "EDITOR › COMPLETION",
    "ignored_snippets": "EDITOR › COMPLETION",

    "copy_with_empty_selection": "EDITOR › FIND",
    "regex_auto_escape": "EDITOR › FIND",
    "auto_find_in_selection": "EDITOR › FIND",
    "close_find_after_find_all": "EDITOR › FIND",
    "close_find_after_replace_all": "EDITOR › FIND",
    "highlight_find_results_in_scrollbar": "EDITOR › FIND",
    "drag_text": "EDITOR › FIND",
    "focus_on_file_drop": "EDITOR › FIND",

    "word_separators": "EDITOR › WORDS",
    "sub_word_separators": "EDITOR › WORDS",

    "fallback_encoding": "FILES › ENCODING",
    "default_encoding": "FILES › ENCODING",
    "enable_hexadecimal_encoding": "FILES › ENCODING",
    "default_line_ending": "FILES › ENCODING",

    "draw_centered": "EDITOR › WORD WRAP",
    "indent_subsequent_lines": "EDITOR › WORD WRAP",

    "hot_exit": "APPLICATION › BEHAVIOR",
    "hot_exit_projects": "APPLICATION › BEHAVIOR",
    "remember_full_screen": "APPLICATION › BEHAVIOR",
    "remember_workspace": "APPLICATION › BEHAVIOR",
    "remember_layout": "APPLICATION › BEHAVIOR",
    "update_system_recent_files": "APPLICATION › BEHAVIOR",
    "shell_environment": "APPLICATION › BEHAVIOR",
    "reload_file_on_change": "APPLICATION › BEHAVIOR",
    "always_prompt_for_file_reload": "APPLICATION › BEHAVIOR",
    "reload_file_in_background": "APPLICATION › BEHAVIOR",
    "close_deleted_files": "APPLICATION › BEHAVIOR",
    "open_files_in_new_window": "APPLICATION › BEHAVIOR",
    "create_window_at_startup": "APPLICATION › BEHAVIOR",
    "show_navigation_bar": "APPLICATION › BEHAVIOR",
    "use_find_clipboard": "APPLICATION › BEHAVIOR",
    "close_windows_when_empty": "APPLICATION › BEHAVIOR",
    "show_full_path": "APPLICATION › BEHAVIOR",
    "show_rel_path": "APPLICATION › BEHAVIOR",
    "show_project_first": "APPLICATION › BEHAVIOR",
    "show_panel_on_build": "APPLICATION › BEHAVIOR",
    "show_errors_inline": "APPLICATION › BEHAVIOR",
    "show_git_status": "APPLICATION › BEHAVIOR",
    "allow_git_home_dir": "APPLICATION › BEHAVIOR",
    "git_diff_target": "APPLICATION › BEHAVIOR",
    "sublime_merge_path": "APPLICATION › BEHAVIOR",
    "preview_on_click": "APPLICATION › BEHAVIOR",
    "select_across_groups": "APPLICATION › BEHAVIOR",
    "console_max_history_lines": "APPLICATION › BEHAVIOR",

    "ignored_packages": "PACKAGES › VINTAGE"
}
```

- [ ] **Step 2: Commit**

```bash
git add tools/section_map.json
git commit -m "feat: add section_map.json for schema generator overrides"
```

---

## Task 2: Set up test infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `tests/__init__.py`** (empty file)

- [ ] **Step 2: Create `tests/conftest.py`**

```python
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 3: Verify pytest is runnable**

```bash
cd /Users/mfuentesg/code/settings-ui && python -m pytest tests/ -v
```

Expected: `no tests ran` (no test files yet) — no import errors.

- [ ] **Step 4: Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "test: add pytest infrastructure for schema_gen"
```

---

## Task 3: Create `schema_gen.py` — JSONC parsing

**Files:**
- Create: `schema_gen.py`
- Create: `tests/test_schema_gen.py`

- [ ] **Step 1: Write failing tests for JSONC parsing**

Create `tests/test_schema_gen.py`:

```python
import json
import pytest
import schema_gen


class TestStripJsoncComments:
    def test_removes_line_comment(self):
        text = '{"key": "value" // comment\n}'
        assert json.loads(schema_gen.strip_jsonc_comments(text)) == {"key": "value"}

    def test_removes_full_line_comment(self):
        text = '{\n// full line comment\n"key": true\n}'
        assert json.loads(schema_gen.strip_jsonc_comments(text)) == {"key": True}

    def test_preserves_url_double_slash(self):
        text = '{"url": "http://example.com"}'
        assert json.loads(schema_gen.strip_jsonc_comments(text)) == {"url": "http://example.com"}

    def test_empty_string(self):
        assert schema_gen.strip_jsonc_comments("") == ""


class TestParseDescriptions:
    def test_extracts_single_comment(self):
        text = '// The font size.\n"font_size": 10\n'
        result = schema_gen.parse_descriptions(text)
        assert result["font_size"] == "The font size."

    def test_joins_multiline_comment(self):
        text = '// Line one.\n// Line two.\n"key": ""\n'
        result = schema_gen.parse_descriptions(text)
        assert result["key"] == "Line one. Line two."

    def test_blank_line_clears_buffer(self):
        text = '// Old comment.\n\n"key": ""\n'
        result = schema_gen.parse_descriptions(text)
        assert "key" not in result

    def test_no_comment_no_entry(self):
        text = '"key": true\n'
        result = schema_gen.parse_descriptions(text)
        assert "key" not in result

    def test_does_not_overwrite_first_description(self):
        text = '// First.\n"key": ""\n// Second.\n"key": ""\n'
        result = schema_gen.parse_descriptions(text)
        assert result["key"] == "First."
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_schema_gen.py -v
```

Expected: `ModuleNotFoundError: No module named 'schema_gen'`

- [ ] **Step 3: Create `schema_gen.py` with parsing functions**

```python
"""
Pure schema generation logic. No Sublime Text imports — fully testable outside ST.
"""
import re
import json

_KEY_LINE = re.compile(r'^"([^"\\]+)"\s*:')


def strip_jsonc_comments(text: str) -> str:
    """Remove // line comments, preserving :// in URLs."""
    lines = []
    for line in text.splitlines():
        lines.append(re.sub(r'(?<!:)//.*$', '', line))
    return '\n'.join(lines)


def parse_descriptions(text: str) -> dict:
    """Return {key: description} extracted from // comments above each JSON key."""
    desc, buf = {}, []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("//"):
            buf.append(line[2:].strip())
        elif line == "":
            buf = []
        else:
            m = _KEY_LINE.match(line)
            if m and buf:
                desc.setdefault(m.group(1), " ".join(x for x in buf if x))
            buf = []
    return desc
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_schema_gen.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add schema_gen.py tests/test_schema_gen.py
git commit -m "feat: add schema_gen with JSONC parsing"
```

---

## Task 4: Add type inference to `schema_gen.py`

**Files:**
- Modify: `schema_gen.py`
- Modify: `tests/test_schema_gen.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_schema_gen.py`:

```python
class TestInferEntry:
    def test_bool_default(self):
        e = schema_gen.infer_entry("auto_indent", True, "")
        assert e == {"key": "auto_indent", "title": "Auto Indent",
                     "desc": "", "type": "bool", "default": True}

    def test_int_default(self):
        e = schema_gen.infer_entry("tab_size", 4, "")
        assert e["type"] == "number"
        assert e["step"] == 1
        assert e["is_float"] is False

    def test_float_default(self):
        e = schema_gen.infer_entry("scroll_speed", 1.0, "")
        assert e["type"] == "number"
        assert e["is_float"] is True
        assert e["step"] == 0.5

    def test_str_default(self):
        e = schema_gen.infer_entry("dictionary", "en_US.dic", "")
        assert e["type"] == "string"
        assert e["default"] == "en_US.dic"

    def test_list_default(self):
        e = schema_gen.infer_entry("rulers", [], "")
        assert e["type"] == "json"

    def test_none_default(self):
        e = schema_gen.infer_entry("some_key", None, "")
        assert e["type"] == "json"

    def test_enum_from_comment(self):
        desc = 'Valid values are "word", "line", "character"'
        e = schema_gen.infer_entry("word_wrap", "word", desc)
        assert e["type"] == "enum"
        assert e["choices"] == ["word", "line", "character"]
        assert e["default"] == "word"

    def test_enum_default_not_in_choices_uses_first(self):
        desc = 'Options: "a", "b", "c"'
        e = schema_gen.infer_entry("key", "z", desc)
        assert e["default"] == "a"

    def test_enum_requires_at_least_two_choices(self):
        desc = 'Only "one" option'
        e = schema_gen.infer_entry("key", "one", desc)
        assert e["type"] == "string"

    def test_enum_ignores_more_than_six(self):
        desc = '"a", "b", "c", "d", "e", "f", "g"'
        e = schema_gen.infer_entry("key", "a", desc)
        assert e["type"] == "string"

    def test_exact_color_scheme(self):
        e = schema_gen.infer_entry("color_scheme", "Mariana", "")
        assert e["type"] == "picker"
        assert e["cmd"] == "select_color_scheme"

    def test_exact_light_color_scheme(self):
        e = schema_gen.infer_entry("light_color_scheme", "", "")
        assert e["type"] == "respick"
        assert e["kind"] == "color_scheme"

    def test_exact_theme(self):
        e = schema_gen.infer_entry("theme", "auto", "")
        assert e["type"] == "picker"
        assert e["cmd"] == "select_theme"

    def test_exact_dark_theme(self):
        e = schema_gen.infer_entry("dark_theme", "", "")
        assert e["type"] == "respick"
        assert e["kind"] == "theme"

    def test_exact_font_face(self):
        e = schema_gen.infer_entry("font_face", "", "")
        assert e["type"] == "listpick"
        assert e["provider"] == "fonts"

    def test_title_derived_from_key(self):
        e = schema_gen.infer_entry("some_setting_key", True, "")
        assert e["title"] == "Some Setting Key"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_schema_gen.py::TestInferEntry -v
```

Expected: `AttributeError: module 'schema_gen' has no attribute 'infer_entry'`

- [ ] **Step 3: Add type inference to `schema_gen.py`**

Append after `parse_descriptions`:

```python
_ENUM_RE = re.compile(r'"([^"]{1,40})"')

_EXACT_MAP = {
    "color_scheme":       {"type": "picker",   "cmd": "select_color_scheme"},
    "light_color_scheme": {"type": "respick",  "kind": "color_scheme"},
    "dark_color_scheme":  {"type": "respick",  "kind": "color_scheme"},
    "theme":              {"type": "picker",   "cmd": "select_theme"},
    "light_theme":        {"type": "respick",  "kind": "theme"},
    "dark_theme":         {"type": "respick",  "kind": "theme"},
    "font_face":          {"type": "listpick", "provider": "fonts"},
}


def infer_entry(key: str, default, desc: str) -> dict:
    """Return a schema entry dict for (key, default, desc)."""
    title = key.replace("_", " ").title()
    base = {"key": key, "title": title, "desc": desc, "default": default}

    if key in _EXACT_MAP:
        return dict(base, **_EXACT_MAP[key])

    quoted = list(dict.fromkeys(_ENUM_RE.findall(desc)))
    if 2 <= len(quoted) <= 6:
        df = default if default in quoted else quoted[0]
        return dict(base, type="enum", default=df, choices=quoted)

    if isinstance(default, bool):
        return dict(base, type="bool")
    if isinstance(default, int):
        return dict(base, type="number", presets=None, step=1, is_float=False)
    if isinstance(default, float):
        return dict(base, type="number", presets=None, step=0.5, is_float=True)
    if isinstance(default, str):
        return dict(base, type="string", presets=None)
    return dict(base, type="json")
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_schema_gen.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add schema_gen.py tests/test_schema_gen.py
git commit -m "feat: add type inference to schema_gen"
```

---

## Task 5: Add section assignment to `schema_gen.py`

**Files:**
- Modify: `schema_gen.py`
- Modify: `tests/test_schema_gen.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_schema_gen.py`:

```python
class TestAssignSection:
    def test_section_map_overrides_prefix(self):
        assert schema_gen.assign_section("file_tab_style",
                                         {"file_tab_style": "APPEARANCE › THEME"},
                                         schema_gen._PREFIX_RULES) == "APPEARANCE › THEME"

    def test_prefix_auto_complete(self):
        assert schema_gen.assign_section("auto_complete_delay", {},
                                         schema_gen._PREFIX_RULES) == "EDITOR › COMPLETION"

    def test_prefix_find(self):
        assert schema_gen.assign_section("find_selected_text", {},
                                         schema_gen._PREFIX_RULES) == "EDITOR › FIND"

    def test_prefix_show_falls_back_to_status_bar(self):
        assert schema_gen.assign_section("show_encoding", {},
                                         schema_gen._PREFIX_RULES) == "STATUS BAR"

    def test_unmapped_goes_to_other(self):
        assert schema_gen.assign_section("unknown_setting", {},
                                         schema_gen._PREFIX_RULES) == "OTHER"

    def test_prefix_vintage(self):
        assert schema_gen.assign_section("vintage_start_in_command_mode", {},
                                         schema_gen._PREFIX_RULES) == "PACKAGES › VINTAGE"

    def test_prefix_font(self):
        assert schema_gen.assign_section("font_size", {},
                                         schema_gen._PREFIX_RULES) == "APPEARANCE › FONT"

    def test_prefix_index(self):
        assert schema_gen.assign_section("index_files", {},
                                         schema_gen._PREFIX_RULES) == "FILES › INDEXING & SIDEBAR"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_schema_gen.py::TestAssignSection -v
```

Expected: `AttributeError: module 'schema_gen' has no attribute 'assign_section'`

- [ ] **Step 3: Add section assignment to `schema_gen.py`**

Append after `infer_entry`:

```python
_PREFIX_RULES = [
    ("auto_complete_",    "EDITOR › COMPLETION"),
    ("line_padding_",     "EDITOR › CARET & LINE"),
    ("control_character_","EDITOR › WHITE SPACE"),
    ("ensure_newline_",   "FILES › SAVE"),
    ("auto_hide_",        "UI › AUTO HIDE"),
    ("hide_pointer_",     "UI › AUTO HIDE"),
    ("auto_indent",       "EDITOR › INDENTATION"),
    ("smart_indent",      "EDITOR › INDENTATION"),
    ("indent_",           "EDITOR › INDENTATION"),
    ("shift_tab_",        "EDITOR › INDENTATION"),
    ("translate_",        "EDITOR › INDENTATION"),
    ("detect_",           "EDITOR › INDENTATION"),
    ("tab_size",          "EDITOR › INDENTATION"),
    ("find_",             "EDITOR › FIND"),
    ("font_",             "APPEARANCE › FONT"),
    ("scroll_",           "EDITOR › SCROLLING"),
    ("match_",            "EDITOR › BRACKETS & TAGS"),
    ("caret_",            "EDITOR › CARET & LINE"),
    ("ruler_",            "EDITOR › RULERS"),
    ("index_",            "FILES › INDEXING & SIDEBAR"),
    ("goto_",             "FILES › INDEXING & SIDEBAR"),
    ("folder_",           "FILES › INDEXING & SIDEBAR"),
    ("file_",             "FILES › INDEXING & SIDEBAR"),
    ("binary_",           "FILES › INDEXING & SIDEBAR"),
    ("image_",            "FILES › INDEXING & SIDEBAR"),
    ("trim_",             "FILES › SAVE"),
    ("save_",             "FILES › SAVE"),
    ("vintage_",          "PACKAGES › VINTAGE"),
    ("word_",             "EDITOR › WORD WRAP"),
    ("wrap_",             "EDITOR › WORD WRAP"),
    ("draw_",             "EDITOR › WHITE SPACE"),
    ("spell_check",       "EDITOR › SPELL CHECK"),
    ("spelling_",         "EDITOR › SPELL CHECK"),
    ("dictionary",        "EDITOR › SPELL CHECK"),
    ("reveal_",           "UI › AUTO HIDE"),
    ("show_",             "STATUS BAR"),
]


def assign_section(key: str, section_map: dict, prefix_rules: list) -> str:
    """Return the section title for key. section_map takes priority over prefix_rules."""
    if key in section_map:
        return section_map[key]
    for prefix, section in prefix_rules:
        if key == prefix or key.startswith(prefix):
            return section
    return "OTHER"
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_schema_gen.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add schema_gen.py tests/test_schema_gen.py
git commit -m "feat: add section assignment to schema_gen"
```

---

## Task 6: Add `build_sections` to `schema_gen.py`

**Files:**
- Modify: `schema_gen.py`
- Modify: `tests/test_schema_gen.py`

`build_sections` produces an ordered dict of `section_title → [entry_dict, ...]`.
For keys already in `existing_sections`, it preserves their curated entry and section.
For new keys, it infers the entry and assigns a section.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_schema_gen.py`:

```python
class TestBuildSections:
    def _existing(self):
        return [
            ("APPEARANCE › FONT", [
                {"key": "font_size", "title": "Font Size", "desc": "Curated.",
                 "type": "number", "default": 10, "presets": [10, 12], "step": 1, "is_float": False},
            ]),
        ]

    def test_existing_entry_preserved(self):
        prefs = [("font_size", 12, "From prefs.")]
        result = schema_gen.build_sections(prefs, self._existing(), {})
        assert result["APPEARANCE › FONT"][0]["desc"] == "Curated."

    def test_existing_entry_in_existing_section(self):
        prefs = [("font_size", 12, "From prefs.")]
        result = schema_gen.build_sections(prefs, self._existing(), {})
        assert "APPEARANCE › FONT" in result

    def test_new_key_inferred_and_assigned(self):
        prefs = [("font_size", 12, ""), ("brand_new_key", True, "A new bool.")]
        result = schema_gen.build_sections(prefs, self._existing(), {})
        new_key_sections = [s for s, entries in result.items()
                            if any(e["key"] == "brand_new_key" for e in entries)]
        assert new_key_sections == ["OTHER"]
        entry = next(e for e in result["OTHER"] if e["key"] == "brand_new_key")
        assert entry["type"] == "bool"

    def test_section_map_routes_new_key(self):
        prefs = [("hot_exit", "always", "")]
        section_map = {"hot_exit": "APPLICATION › BEHAVIOR"}
        result = schema_gen.build_sections(prefs, [], section_map)
        assert "APPLICATION › BEHAVIOR" in result
        assert result["APPLICATION › BEHAVIOR"][0]["key"] == "hot_exit"

    def test_existing_sections_appear_before_new(self):
        prefs = [("font_size", 10, ""), ("unknown_key", True, "")]
        result = schema_gen.build_sections(prefs, self._existing(), {})
        keys = list(result.keys())
        assert keys[0] == "APPEARANCE › FONT"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_schema_gen.py::TestBuildSections -v
```

Expected: `AttributeError: module 'schema_gen' has no attribute 'build_sections'`

- [ ] **Step 3: Add `build_sections` to `schema_gen.py`**

Append after `assign_section`:

```python
def build_sections(prefs_data: list, existing_sections: list, section_map: dict) -> dict:
    """
    Build ordered {section_title: [entry_dict, ...]} from prefs_data.

    prefs_data:        list of (key, default, desc) in prefs file order
    existing_sections: list of (title, [entry_dict, ...]) from schema.SECTIONS
    section_map:       dict key→section override (from section_map.json)

    Existing entries are preserved verbatim; new keys get inferred entries.
    Existing section order is maintained; new sections are appended.
    """
    existing_entry = {}
    existing_key_section = {}
    for title, entries in existing_sections:
        for entry in entries:
            existing_entry[entry["key"]] = entry
            existing_key_section[entry["key"]] = title

    result = {}
    for title, _ in existing_sections:
        result[title] = []

    for key, default, desc in prefs_data:
        if key in existing_entry:
            section = existing_key_section[key]
            result[section].append(existing_entry[key])
        else:
            section = assign_section(key, section_map, _PREFIX_RULES)
            if section not in result:
                result[section] = []
            result[section].append(infer_entry(key, default, desc))

    return {k: v for k, v in result.items() if v}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_schema_gen.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add schema_gen.py tests/test_schema_gen.py
git commit -m "feat: add build_sections to schema_gen"
```

---

## Task 7: Add code generation to `schema_gen.py`

**Files:**
- Modify: `schema_gen.py`
- Modify: `tests/test_schema_gen.py`

`entry_to_code` serializes one entry dict to the appropriate `b()`/`e()`/etc. call.
`sections_to_code` produces the full `SECTIONS = [...]` block.
`replace_sections_block` swaps the SECTIONS block in a `schema.py` source string.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_schema_gen.py`:

```python
class TestEntryToCode:
    def test_bool(self):
        e = {"key": "foo", "title": "Foo", "desc": "A foo.", "type": "bool", "default": True}
        assert schema_gen.entry_to_code(e) == "b('foo', 'Foo', 'A foo.', True)"

    def test_enum(self):
        e = {"key": "k", "title": "K", "desc": "", "type": "enum",
             "default": "a", "choices": ["a", "b"]}
        assert schema_gen.entry_to_code(e) == "e('k', 'K', '', 'a', ['a', 'b'])"

    def test_number_int(self):
        e = {"key": "k", "title": "K", "desc": "", "type": "number",
             "default": 4, "presets": None, "step": 1, "is_float": False}
        assert schema_gen.entry_to_code(e) == "n('k', 'K', '', 4)"

    def test_number_float_with_step(self):
        e = {"key": "k", "title": "K", "desc": "", "type": "number",
             "default": 1.0, "presets": None, "step": 0.5, "is_float": True}
        assert schema_gen.entry_to_code(e) == "n('k', 'K', '', 1.0, step=0.5, is_float=True)"

    def test_number_with_presets(self):
        e = {"key": "k", "title": "K", "desc": "", "type": "number",
             "default": 10, "presets": [10, 12, 14], "step": 1, "is_float": False}
        assert schema_gen.entry_to_code(e) == "n('k', 'K', '', 10, presets=[10, 12, 14])"

    def test_string(self):
        e = {"key": "k", "title": "K", "desc": "", "type": "string",
             "default": "UTF-8", "presets": None}
        assert schema_gen.entry_to_code(e) == "s('k', 'K', '', 'UTF-8')"

    def test_json(self):
        e = {"key": "k", "title": "K", "desc": "", "type": "json", "default": []}
        assert schema_gen.entry_to_code(e) == "j('k', 'K', '', [])"

    def test_picker(self):
        e = {"key": "color_scheme", "title": "Color Scheme", "desc": "",
             "type": "picker", "default": "Mariana", "cmd": "select_color_scheme"}
        assert schema_gen.entry_to_code(e) == \
            "pk('color_scheme', 'Color Scheme', '', 'Mariana', 'select_color_scheme')"

    def test_respick(self):
        e = {"key": "light_color_scheme", "title": "Light Color Scheme", "desc": "",
             "type": "respick", "default": "", "kind": "color_scheme"}
        assert schema_gen.entry_to_code(e) == \
            "rp('light_color_scheme', 'Light Color Scheme', '', '', 'color_scheme')"

    def test_listpick(self):
        e = {"key": "font_face", "title": "Font Face", "desc": "",
             "type": "listpick", "default": "", "provider": "fonts"}
        assert schema_gen.entry_to_code(e) == \
            "lp('font_face', 'Font Face', '', '', 'fonts')"


class TestSectionsToCode:
    def test_produces_valid_python(self):
        import ast
        sections = {"SEC": [{"key": "k", "title": "K", "desc": "", "type": "bool", "default": True}]}
        code = schema_gen.sections_to_code(sections)
        assert code.startswith("SECTIONS = [")
        ast.parse(code)

    def test_empty_sections(self):
        code = schema_gen.sections_to_code({})
        assert code == "SECTIONS = [\n]"


class TestReplaceSectionsBlock:
    _source = (
        'def b(): pass\n\nSECTIONS = [\n    ("A", []),\n]\n\nKEY_INDEX = {}\n'
    )

    def test_replaces_sections(self):
        new_code = 'SECTIONS = [\n    ("B", []),\n]'
        result = schema_gen.replace_sections_block(self._source, new_code)
        assert "B" in result
        assert "A" not in result

    def test_preserves_preamble(self):
        new_code = 'SECTIONS = [\n]'
        result = schema_gen.replace_sections_block(self._source, new_code)
        assert result.startswith("def b(): pass")

    def test_preserves_postamble(self):
        new_code = 'SECTIONS = [\n]'
        result = schema_gen.replace_sections_block(self._source, new_code)
        assert "KEY_INDEX = {}" in result

    def test_raises_on_missing_marker(self):
        with pytest.raises(ValueError):
            schema_gen.replace_sections_block("no sections here", "SECTIONS = [\n]")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_schema_gen.py::TestEntryToCode tests/test_schema_gen.py::TestSectionsToCode tests/test_schema_gen.py::TestReplaceSectionsBlock -v
```

Expected: `AttributeError: module 'schema_gen' has no attribute 'entry_to_code'`

- [ ] **Step 3: Add code generation functions to `schema_gen.py`**

Append after `build_sections`:

```python
def entry_to_code(entry: dict) -> str:
    """Serialize an entry dict to a Python helper call string."""
    t = entry["type"]
    k = repr(entry["key"])
    ti = repr(entry["title"])
    d = repr(entry["desc"])
    df = repr(entry["default"])

    if t == "bool":
        return "b(%s, %s, %s, %s)" % (k, ti, d, df)
    if t == "enum":
        ch = repr(entry["choices"])
        return "e(%s, %s, %s, %s, %s)" % (k, ti, d, df, ch)
    if t == "number":
        step = entry.get("step", 1)
        is_float = entry.get("is_float", False)
        presets = entry.get("presets")
        extra = []
        if presets is not None:
            extra.append("presets=%s" % repr(presets))
        if step != 1:
            extra.append("step=%s" % repr(step))
        if is_float:
            extra.append("is_float=True")
        args = ", ".join([k, ti, d, df] + extra)
        return "n(%s)" % args
    if t == "string":
        presets = entry.get("presets")
        if presets is not None:
            return "s(%s, %s, %s, %s, presets=%s)" % (k, ti, d, df, repr(presets))
        return "s(%s, %s, %s, %s)" % (k, ti, d, df)
    if t == "json":
        return "j(%s, %s, %s, %s)" % (k, ti, d, df)
    if t == "picker":
        cmd = repr(entry["cmd"])
        return "pk(%s, %s, %s, %s, %s)" % (k, ti, d, df, cmd)
    if t == "respick":
        kind = repr(entry["kind"])
        return "rp(%s, %s, %s, %s, %s)" % (k, ti, d, df, kind)
    if t == "listpick":
        provider = repr(entry["provider"])
        return "lp(%s, %s, %s, %s, %s)" % (k, ti, d, df, provider)
    return "j(%s, %s, %s, %s)" % (k, ti, d, df)


def sections_to_code(sections: dict) -> str:
    """Produce the SECTIONS = [...] Python block from an ordered section dict."""
    lines = ["SECTIONS = ["]
    for title, entries in sections.items():
        lines.append("    (%s, [" % repr(title))
        for entry in entries:
            lines.append("        %s," % entry_to_code(entry))
        lines.append("    ]),")
    lines.append("]")
    return "\n".join(lines)


def replace_sections_block(source: str, new_sections_code: str) -> str:
    """Replace the SECTIONS = [...] block in schema.py source with new_sections_code."""
    marker = "SECTIONS = ["
    start = source.find(marker)
    if start == -1:
        raise ValueError("'SECTIONS = [' not found in source")
    depth = 1
    i = start + len(marker)
    while i < len(source) and depth > 0:
        if source[i] == "[":
            depth += 1
        elif source[i] == "]":
            depth -= 1
        i += 1
    return source[:start] + new_sections_code + source[i:]
```

- [ ] **Step 4: Run all tests — verify they pass**

```bash
python -m pytest tests/test_schema_gen.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add schema_gen.py tests/test_schema_gen.py
git commit -m "feat: add code generation to schema_gen"
```

---

## Task 8: Create `gen_schema.py` ST command

**Files:**
- Create: `gen_schema.py`

This command is a developer tool. It runs inside ST, has no automated tests,
and is verified manually.

- [ ] **Step 1: Create `gen_schema.py`**

```python
"""
ST command: settings_ui_generate_schema

Usage (command palette): "Settings UI: Generate Schema"
Usage (console):         window.run_command("settings_ui_generate_schema")

Reads Default/Preferences.sublime-settings, merges with existing schema.KEY_INDEX,
and rewrites the SECTIONS block in schema.py. ST auto-reloads the plugin on save.
"""
import os
import json
import sublime
import sublime_plugin
from . import schema as _schema
from . import schema_gen

_TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.py")


def _load_prefs_data() -> list:
    """Return [(key, default, desc), ...] from Default/Preferences.sublime-settings."""
    plat = {"osx": "OSX", "windows": "Windows", "linux": "Linux"}.get(
        sublime.platform(), ""
    )
    paths = ["Packages/Default/Preferences.sublime-settings"]
    if plat:
        paths.append("Packages/Default/Preferences (%s).sublime-settings" % plat)

    merged_values = {}
    merged_descs = {}
    key_order = []

    for path in paths:
        try:
            text = sublime.load_resource(path)
        except Exception:
            continue
        try:
            values = sublime.decode_value(schema_gen.strip_jsonc_comments(text))
        except Exception:
            try:
                values = sublime.decode_value(text)
            except Exception:
                continue
        descs = schema_gen.parse_descriptions(text)
        for key, val in values.items():
            if key not in merged_values:
                key_order.append(key)
            merged_values[key] = val
            merged_descs.setdefault(key, descs.get(key, ""))

    return [(k, merged_values[k], merged_descs[k]) for k in key_order]


class SettingsUiGenerateSchemaCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        section_map_path = os.path.join(_TOOLS_DIR, "section_map.json")
        try:
            with open(section_map_path, encoding="utf-8") as f:
                section_map = json.load(f)
        except Exception as ex:
            sublime.error_message("Settings UI: Cannot load section_map.json\n%s" % ex)
            return

        prefs_data = _load_prefs_data()
        if not prefs_data:
            sublime.error_message(
                "Settings UI: Failed to load Default/Preferences.sublime-settings"
            )
            return

        sections = schema_gen.build_sections(prefs_data, _schema.SECTIONS, section_map)
        new_sections_code = schema_gen.sections_to_code(sections)

        try:
            with open(_SCHEMA_PATH, encoding="utf-8") as f:
                source = f.read()
        except Exception as ex:
            sublime.error_message("Settings UI: Cannot read schema.py\n%s" % ex)
            return

        try:
            new_source = schema_gen.replace_sections_block(source, new_sections_code)
        except ValueError as ex:
            sublime.error_message("Settings UI: %s" % ex)
            return

        with open(_SCHEMA_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_source)

        total_keys = sum(len(v) for v in sections.values())
        sublime.status_message(
            "Settings UI: schema.py regenerated — %d keys across %d sections"
            % (total_keys, len(sections))
        )
```

- [ ] **Step 2: Verify no import errors**

From the ST console after saving the file:

```python
import SettingsUI.gen_schema
```

Expected: no errors.

- [ ] **Step 3: Run the command manually**

```python
sublime.active_window().run_command("settings_ui_generate_schema")
```

Expected:
- Status bar shows `Settings UI: schema.py regenerated — N keys across M sections`
- `schema.py` is rewritten (check diff: `git diff schema.py`)
- New keys from ST (if any) appear in appropriate sections
- All existing curated entries are preserved with their original titles/descriptions

- [ ] **Step 4: Commit**

```bash
git add gen_schema.py
git commit -m "feat: add settings_ui_generate_schema ST command"
```

---

## Task 9: Update `Default.sublime-commands`

**Files:**
- Modify: `Default.sublime-commands`

- [ ] **Step 1: Add the command entry**

Replace the file contents with:

```json
[
    {
        "caption": "Preferences: Settings UI",
        "command": "settings_ui_open"
    },
    {
        "caption": "Settings UI: Generate Schema",
        "command": "settings_ui_generate_schema"
    }
]
```

- [ ] **Step 2: Verify it appears in the command palette**

Open Sublime Text command palette (`Cmd+Shift+P`), type "Generate Schema".
Expected: `Settings UI: Generate Schema` appears.

- [ ] **Step 3: Commit**

```bash
git add Default.sublime-commands
git commit -m "feat: add Generate Schema to command palette"
```

---

## Task 10: Add reactive patching to `schema_loader.py` + update `SettingsUI.py`

**Files:**
- Modify: `schema_loader.py`
- Modify: `SettingsUI.py`

When `Default/Preferences.sublime-settings` changes (e.g. after an ST update installs),
the schema defaults should re-patch without a full plugin reload.
Since we cannot call `add_on_change` on a packed resource, we listen on the user's
`Preferences.sublime-settings` — any write to it triggers a re-patch of defaults,
which is safe and keeps the schema current with the user's active environment.

- [ ] **Step 1: Add listener functions to `schema_loader.py`**

Append after `ensure_schema_loaded`:

```python
def _repatch_defaults() -> None:
    """Re-patch schema defaults from current ST prefs. Safe to call repeatedly."""
    try:
        defaults, _ = _load_default_prefs()
        for entry in schema.KEY_INDEX.values():
            if entry["key"] in defaults:
                entry["default"] = defaults[entry["key"]]
    except Exception:
        pass


def register_listener() -> None:
    """Call from plugin_loaded() to enable reactive default-patching."""
    sublime.load_settings("Preferences.sublime-settings").add_on_change(
        "settings_ui_schema", _repatch_defaults
    )


def unregister_listener() -> None:
    """Call from plugin_unloaded() to remove the listener."""
    sublime.load_settings("Preferences.sublime-settings").clear_on_change(
        "settings_ui_schema"
    )
```

- [ ] **Step 2: Call `register_listener` from `plugin_loaded` in `SettingsUI.py`**

In `SettingsUI.py`, find the `plugin_loaded` function. After `schema_loader` is imported at the top, add the call. The current `plugin_loaded` body starts by checking for an active window — add `schema_loader.register_listener()` call at the top of the function body, before the `win = panel.get_active_settings_window()` check:

```python
def plugin_loaded() -> None:
    schema_loader.register_listener()
    win = panel.get_active_settings_window()
    ...
```

- [ ] **Step 3: Call `unregister_listener` from `plugin_unloaded` in `SettingsUI.py`**

Add to the existing `plugin_unloaded` function, alongside the existing `clear_on_change` call:

```python
def plugin_unloaded() -> None:
    prefs.prefs().clear_on_change("settings_ui")
    schema_loader.unregister_listener()   # ← add this line
    panel.reset_module_state()
    state._filter   = ""
    state._category = 0
    schema_loader._schema_loaded = False
```

- [ ] **Step 4: Verify no errors on plugin reload**

Save `SettingsUI.py` to trigger hot-reload. In the ST console:

```python
sublime.active_window().run_command("settings_ui_open")
```

Expected: panel opens normally, no errors in console.

- [ ] **Step 5: Commit**

```bash
git add schema_loader.py SettingsUI.py
git commit -m "feat: add reactive default-patching via add_on_change in schema_loader"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Generator command inside ST (uses `load_resource`) | Task 8 |
| `tools/section_map.json` overrides | Task 1 |
| Prefix rules for section assignment | Task 5 |
| Type inference: exact map, enum from comment, value type | Task 4 |
| Full mode: replaces SECTIONS block | Tasks 7 + 8 |
| Preserve existing curated entries | Task 6 (`build_sections`) |
| Platform-specific prefs merged | Task 8 (`_load_prefs_data`) |
| `add_on_change` reactive patching | Task 10 |
| `clear_on_change` in `plugin_unloaded` | Task 10 |
| `plugin_loaded` sequence documented | Task 10 |
| Command palette entry | Task 9 |

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency:**
- `infer_entry` used consistently across Tasks 4, 6, 7
- `_PREFIX_RULES` defined in Task 5, referenced by `assign_section` in Task 5 and `build_sections` in Task 6 — consistent
- `entry_to_code` called from `sections_to_code` — both defined in Task 7 — consistent
- `register_listener` / `unregister_listener` defined in Task 10 schema_loader, called in Task 10 SettingsUI — consistent
