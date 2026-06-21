# SettingsUI Real Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the SettingsUI prototype into a distributable, Package Control-ready Sublime Text 4 plugin by fixing naming, adding missing distribution files, fixing two UX bugs, and adding a "View Raw Config" button.

**Architecture:** All changes are in-place — no structural refactor. The 7-module split (SettingsUI.py, panel.py, renderer.py, schema.py, schema_loader.py, pickers.py, prefs.py, state.py) stays. New files are added alongside existing ones. The folder must be renamed `settings-ui` → `SettingsUI` by the user manually (not part of this plan).

**Tech Stack:** Python 3.8+, Sublime Text 4 API (sublime, sublime_plugin), minihtml/Phantom rendering.

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| Modify | `panel.py` | Rename 4 string constants; add `import os`; add `_open_raw_config()`; add `action:raw_config` branch in `on_nav()` |
| Modify | `renderer.py` | Rename `id="vscode-settings"` in `_wrap()`; add `.rawlink` CSS; add raw config button HTML in `build_nav_html()` |
| Modify | `SettingsUI.py` | Rename prefs-listener key; fix `SettingsUiOpenCommand.run()` to focus existing window; add `SettingsUiCloseListener` class |
| Create | `Default (OSX).sublime-keymap` | Cmd+, → `settings_ui_open` |
| Create | `Default (Windows).sublime-keymap` | Ctrl+, → `settings_ui_open` |
| Create | `Default (Linux).sublime-keymap` | Ctrl+, → `settings_ui_open` |
| Create | `SettingsUI.sublime-settings` | Plugin settings stub |
| Create | `LICENSE` | MIT, Marcelo Fuentes |
| Create | `CHANGELOG.md` | v0.1.0 entry |
| Create | `messages.json` | Package Control message pointers |
| Create | `messages/install.txt` | Welcome message |
| Delete | `update_plugin.py` | Dev-only script, not for distribution |

---

## Task 1: Rename `vscode_*` identifiers to `settings_ui_*`

**Files:**
- Modify: `panel.py`
- Modify: `renderer.py`
- Modify: `SettingsUI.py`

These string constants are stored in view settings and used as phantom/listener keys. They must not reference VS Code.

- [ ] **Step 1: Update constants in `panel.py` (lines 17–20)**

Replace the four marker constants:

```python
PANEL_PHANTOM_NAV     = "settings_ui_panel_nav"
PANEL_PHANTOM_CONTENT = "settings_ui_panel_content"
NAV_MARK              = "settings_ui_nav"      # left pane
CONTENT_MARK          = "settings_ui_content"  # right pane
```

- [ ] **Step 2: Update prefs listener key in `panel.py` (line 212)**

In `_ensure_prefs_listener()`, change the `add_on_change` key:

```python
def _ensure_prefs_listener() -> None:
    """Register a one-shot listener on Preferences to keep the panel fresh."""
    global _prefs_listener_on
    if _prefs_listener_on:
        return
    prefs.prefs().add_on_change("settings_ui", _on_prefs_changed)
    _prefs_listener_on = True
```

- [ ] **Step 3: Update prefs listener key in `SettingsUI.py` (line 95)**

In `plugin_unloaded()`, change the `clear_on_change` key to match:

```python
def plugin_unloaded() -> None:
    prefs.prefs().clear_on_change("settings_ui")
    panel.reset_module_state()
    state._filter   = ""
    state._category = 0
    schema_loader._schema_loaded = False
```

- [ ] **Step 4: Update HTML body id in `renderer.py` (line 308)**

In `_wrap()`, change the body id attribute:

```python
def _wrap(inner: str, extra_style: str = "") -> str:
    """Wrap *inner* in the standard body+style shell."""
    style_attr = ' style="%s"' % extra_style if extra_style else ""
    return (
        '<body id="settings-ui"><style>' + CSS + '</style>'
        '<div class="shell"%s>' % style_attr + inner + '</div></body>'
    )
```

- [ ] **Step 5: Verify — open ST console and reload plugin**

In Sublime Text console (`Ctrl+\`` / `Cmd+\``):

```python
import importlib, SettingsUI.panel as p; print(p.NAV_MARK, p.CONTENT_MARK)
```

Expected output: `settings_ui_nav settings_ui_content`

- [ ] **Step 6: Commit**

```bash
git add panel.py renderer.py SettingsUI.py
git commit -m "refactor: rename vscode_* identifiers to settings_ui_*"
```

---

## Task 2: Fix `SettingsUiOpenCommand` + add `SettingsUiCloseListener`

**Files:**
- Modify: `SettingsUI.py`

Two bugs: (a) opening the command always creates a new window even if one exists; (b) closing the settings window leaves module state dirty (polling continues, phantom sets hold stale view IDs).

- [ ] **Step 1: Fix `SettingsUiOpenCommand.run()` to focus existing window**

Replace the existing `run()` method (lines 30–47 of `SettingsUI.py`):

```python
def run(self) -> None:
    existing = panel.get_active_settings_window()
    if existing:
        existing.bring_to_front()
        return

    sublime.run_command("new_window")
    win = sublime.active_window()

    win.set_layout({
        "cols":  [0.0, 0.28, 1.0],
        "rows":  [0.0, 1.0],
        "cells": [[0, 0, 1, 1], [1, 0, 2, 1]],
    })
    win.set_tabs_visible(False)
    win.set_status_bar_visible(False)
    win.set_sidebar_visible(False)
    win.set_minimap_visible(False)

    panel.render()
```

- [ ] **Step 2: Add `SettingsUiCloseListener` class**

After the `SettingsUiSyncListener` class (after line 60), add:

```python
class SettingsUiCloseListener(sublime_plugin.EventListener):
    """Reset module state when the settings window is closed."""

    def on_close(self, view: sublime.View) -> None:
        if (view.settings().get(panel.CONTENT_MARK)
                or view.settings().get(panel.NAV_MARK)):
            panel.reset_module_state()
```

- [ ] **Step 3: Verify focus behavior**

1. Open Command Palette → "Preferences: Settings UI" — settings window opens.
2. Click back into your main editor window.
3. Open Command Palette → "Preferences: Settings UI" again.
4. Expected: settings window comes to front, no second window opened.

- [ ] **Step 4: Verify close cleanup**

1. Open Settings UI window, then close it (Cmd+W / Ctrl+W on the window).
2. In ST console: `import SettingsUI.panel as p; print(p._polling, p._phantom_sets)`
3. Expected: `False {}`

- [ ] **Step 5: Commit**

```bash
git add SettingsUI.py
git commit -m "fix: focus existing settings window; reset state on window close"
```

---

## Task 3: Add "View Raw Config" button to nav pane

**Files:**
- Modify: `renderer.py`
- Modify: `panel.py`

A sticky button at the top of the left nav pane (above the category list) that opens `Packages/User/Preferences.sublime-settings` as an editable tab in the content area (group 1). Always visible because the nav pane scrolls independently.

- [ ] **Step 1: Add `.rawlink` CSS to `renderer.py`**

In the `CSS` string (after the `.navreset` rule, around line 41), add:

```python
    .rawlink { display: block; text-decoration: none; color: var(--bluish);
               font-size: 12px; padding: 6px 10px; margin-bottom: 12px;
               border: 1px solid color(var(--bluish) alpha(0.35));
               border-radius: 5px; text-align: center; }
```

- [ ] **Step 2: Add raw config button HTML in `build_nav_html()` in `renderer.py`**

In `build_nav_html()`, insert the raw config link as the first element inside the nav div (before the `navhead` span). Replace the current first line of `parts`:

```python
def build_nav_html(sections: list, filter_text: str, category_index: int) -> str:
    """Build the full HTML string for the navigation sidebar."""
    parts = [
        '<div class="nav">',
        '<a class="rawlink" href="action:raw_config">{ } Raw Config</a>',
        '<span class="navhead">SETTINGS</span>',
    ]
    for i, (title, _entries) in enumerate(sections):
        active = not filter_text and i == category_index
        parts.append(
            '<a class="navitem{a}" href="cat:{i}">{t}</a>'.format(
                a=" active" if active else "", i=i, t=schema.esc(title)
            )
        )
    parts.append(
        '<a class="navreset" href="action:reset_all">Restore all defaults</a>'
    )
    parts.append('</div>')
    return _wrap("".join(parts), "padding-bottom: 2000px;")
```

- [ ] **Step 3: Add `import os` to `panel.py`**

At the top of `panel.py`, the current imports are:

```python
import sublime
from . import schema, schema_loader, prefs, renderer, pickers, state
```

Add `import os`:

```python
import os
import sublime
from . import schema, schema_loader, prefs, renderer, pickers, state
```

- [ ] **Step 4: Add `_open_raw_config()` function to `panel.py`**

Add this function after `reset_module_state()` at the bottom of `panel.py`:

```python
def _open_raw_config() -> None:
    """Open Preferences.sublime-settings as an editable tab in group 1."""
    win = get_active_settings_window()
    if not win:
        return
    path = os.path.join(sublime.packages_path(), "User", "Preferences.sublime-settings")
    for v in win.views():
        if v.file_name() == path:
            win.focus_view(v)
            return
    v = win.open_file(path)
    win.set_view_index(v, 1, 0)
    v.assign_syntax("Packages/JavaScript/JSON.sublime-syntax")
```

- [ ] **Step 5: Add `action:raw_config` branch in `panel.on_nav()` in `panel.py`**

In `on_nav()`, add the raw config branch alongside the other `action:` handlers (after `action:clear_search`, before the `cmd, _sep, rest = href.partition(":")` line):

```python
    if href == "action:raw_config":
        _open_raw_config()
        return
```

The full block at the top of `on_nav()` should look like:

```python
    if href == "action:reset_all":
        prefs.reset_all()
        render_content()
        return
    if href == "action:search":
        pickers.open_search()
        return
    if href == "action:clear_search":
        state._filter = ""
        render_nav()
        render_content()
        return
    if href == "action:raw_config":
        _open_raw_config()
        return
```

- [ ] **Step 6: Verify in ST**

1. Open Settings UI (Command Palette → "Preferences: Settings UI").
2. Confirm "{ } Raw Config" button appears at top of left nav pane.
3. Click it — `Preferences.sublime-settings` opens in right pane, editable, JSON-highlighted.
4. Click it again — no second tab opens; existing raw config tab focuses.
5. Close raw config tab — switch back to Settings UI content tab works normally.

- [ ] **Step 7: Commit**

```bash
git add panel.py renderer.py
git commit -m "feat: add View Raw Config button to nav pane"
```

---

## Task 4: Add keyboard shortcuts

**Files:**
- Create: `Default (OSX).sublime-keymap`
- Create: `Default (Windows).sublime-keymap`
- Create: `Default (Linux).sublime-keymap`

ST loads the keymap file matching the current platform. All three bind the same command with the platform-appropriate modifier.

- [ ] **Step 1: Create `Default (OSX).sublime-keymap`**

```json
[
    {
        "keys": ["super+,"],
        "command": "settings_ui_open"
    }
]
```

- [ ] **Step 2: Create `Default (Windows).sublime-keymap`**

```json
[
    {
        "keys": ["ctrl+,"],
        "command": "settings_ui_open"
    }
]
```

- [ ] **Step 3: Create `Default (Linux).sublime-keymap`**

```json
[
    {
        "keys": ["ctrl+,"],
        "command": "settings_ui_open"
    }
]
```

- [ ] **Step 4: Verify in ST**

Press Cmd+, (macOS) or Ctrl+, (Windows/Linux). Expected: Settings UI opens (or focuses if already open).

Note: This overrides ST's built-in Cmd+, shortcut for plain preferences. If the user prefers not to override it, they can rebind in their personal keymap. This is the correct approach for a settings UI plugin.

- [ ] **Step 5: Commit**

```bash
git add "Default (OSX).sublime-keymap" "Default (Windows).sublime-keymap" "Default (Linux).sublime-keymap"
git commit -m "feat: add Cmd+, / Ctrl+, keybinding for settings_ui_open"
```

---

## Task 5: Add `SettingsUI.sublime-settings`

**Files:**
- Create: `SettingsUI.sublime-settings`

Provides a place for future plugin configuration. ST discovers this file automatically and merges it with `Packages/User/SettingsUI.sublime-settings` (user overrides). Starting with one setting so the file is useful immediately.

- [ ] **Step 1: Create `SettingsUI.sublime-settings`**

```json
{
    // Open the Settings UI automatically when Sublime Text starts.
    "open_on_startup": false
}
```

- [ ] **Step 2: Wire up `open_on_startup` in `plugin_loaded()` in `SettingsUI.py`**

Read the plugin setting and open the panel if true. Add to the end of `plugin_loaded()`:

```python
def plugin_loaded() -> None:
    win = panel.get_active_settings_window()
    if win:
        panel._ensure_prefs_listener()
        panel.render()
        active = win.active_view()
        if active and (
            active.settings().get(panel.CONTENT_MARK)
            or active.settings().get(panel.NAV_MARK)
        ):
            panel._start_poll()
        return

    plugin_settings = sublime.load_settings("SettingsUI.sublime-settings")
    if plugin_settings.get("open_on_startup", False):
        sublime.active_window().run_command("settings_ui_open")
```

- [ ] **Step 3: Verify**

Set `"open_on_startup": true` in `Packages/User/SettingsUI.sublime-settings`, restart ST. Settings UI should open automatically. Set back to `false`.

- [ ] **Step 4: Commit**

```bash
git add SettingsUI.sublime-settings SettingsUI.py
git commit -m "feat: add SettingsUI.sublime-settings with open_on_startup option"
```

---

## Task 6: Add distribution files

**Files:**
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `messages.json`
- Create: `messages/install.txt`

Required for Package Control submission and good OSS hygiene.

- [ ] **Step 1: Create `LICENSE`**

```
MIT License

Copyright (c) 2026 Marcelo Fuentes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Create `CHANGELOG.md`**

```markdown
# Changelog

## [0.1.0] - 2026-06-21

### Added
- Visual, categorised settings editor via Sublime Text's minihtml/Phantom API
- Left-pane category navigation with scroll-sync
- Search across all settings
- Boolean toggles, enum radio buttons, numeric steppers
- Native pickers for color schemes, themes, and fonts
- Dynamic schema: auto-discovers settings from Default/Preferences.sublime-settings
- "View Raw Config" button to open Preferences.sublime-settings directly
- Cmd+, / Ctrl+, keyboard shortcut
- `open_on_startup` plugin setting
```

- [ ] **Step 3: Create `messages/install.txt`**

First create the directory:

```bash
mkdir -p messages
```

Then create `messages/install.txt`:

```
SettingsUI for Sublime Text 4
==============================

Thanks for installing SettingsUI!

Open the visual settings editor any time:
  • Menu: Preferences → Settings UI
  • Command Palette: "Preferences: Settings UI"
  • Keyboard: Cmd+, (macOS) / Ctrl+, (Windows / Linux)

The panel matches your active color scheme automatically.
Use "{ } Raw Config" in the left nav to view or edit
settings that aren't yet covered by the UI.

Report issues: https://github.com/mfuentesg/settings-ui
```

- [ ] **Step 4: Create `messages.json`**

```json
{
    "install": "messages/install.txt",
    "0.1.0": "messages/install.txt"
}
```

- [ ] **Step 5: Commit**

```bash
git add LICENSE CHANGELOG.md messages.json messages/install.txt
git commit -m "chore: add LICENSE, CHANGELOG, Package Control messages"
```

---

## Task 7: Delete `update_plugin.py`

**Files:**
- Delete: `update_plugin.py`

This script patches `SettingsUI.py` in place — a dev-time workaround with no place in a distributable package. Deleting it removes confusion for anyone reading the package.

- [ ] **Step 1: Delete the file**

```bash
git rm update_plugin.py
```

- [ ] **Step 2: Verify**

```bash
ls update_plugin.py
```

Expected: `ls: update_plugin.py: No such file or directory`

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove update_plugin.py dev script"
```

---

## Self-Review Against Spec

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Rename `vscode_*` → `settings_ui_*` (panel.py, renderer.py, SettingsUI.py) | Task 1 |
| Fix `SettingsUiOpenCommand` to focus existing window | Task 2 |
| Add `SettingsUiCloseListener` | Task 2 |
| "View Raw Config" button in nav pane (renderer.py) | Task 3 |
| `_open_raw_config()` handler in panel.py | Task 3 |
| Keymaps (OSX/Windows/Linux) | Task 4 |
| `SettingsUI.sublime-settings` | Task 5 |
| `LICENSE` (MIT, Marcelo Fuentes) | Task 6 |
| `CHANGELOG.md` | Task 6 |
| `messages.json` + `messages/install.txt` | Task 6 |
| Delete `update_plugin.py` | Task 7 |

All spec requirements covered. No placeholders. Types and method names consistent across all tasks (`panel.get_active_settings_window()`, `panel.reset_module_state()`, `panel.CONTENT_MARK`, `panel.NAV_MARK` — all defined in existing code and referenced correctly).
