# SettingsUI — Real Plugin Design

**Date:** 2026-06-21  
**Status:** Approved

## Goal

Convert the existing SettingsUI prototype into a distributable, Package Control-ready Sublime Text 4 plugin. The plugin provides a visual, categorised settings editor — replacing the plain JSON file workflow — using ST's native minihtml/Phantom rendering.

## Approach Selected

**B — Full polish, Package Control ready.** Add missing distribution files, fix naming (remove VS Code references), fix two UX bugs, delete the dev-only script. No architectural refactor.

## Architecture

No structural change to the 7-module split. Folder renamed from `settings-ui` → `SettingsUI` (ST uses the folder name as the package name).

```
SettingsUI/
├── SettingsUI.py          entry: plugin_loaded/unloaded, commands, listeners
├── panel.py               window/view wiring, scroll-sync, nav router
├── renderer.py            stateless HTML builders (no sublime import side-effects)
├── schema.py              settings catalogue (pure Python, no sublime import)
├── schema_loader.py       dynamic schema enrichment from Default prefs
├── pickers.py             quick-panel / input-panel pickers
├── prefs.py               Settings I/O
├── state.py               shared mutable state (_filter, _category)
├── __init__.py            one-line comment, keeps package importable
├── Default.sublime-commands
├── Main.sublime-menu
├── README.md
└── [new files — see below]
```

`update_plugin.py` is deleted — it's a dev script that patches `SettingsUI.py` in place and has no place in a distributable package.

## New Files

| File | Purpose |
|------|---------|
| `Default (OSX).sublime-keymap` | Cmd+, → `settings_ui_open` |
| `Default (Windows).sublime-keymap` | Ctrl+, → `settings_ui_open` |
| `Default (Linux).sublime-keymap` | Ctrl+, → `settings_ui_open` |
| `SettingsUI.sublime-settings` | Plugin settings (starts with `"open_on_startup": false`) |
| `LICENSE` | MIT |
| `CHANGELOG.md` | v0.1.0 initial release entry |
| `messages.json` | Package Control install/update message pointers |
| `messages/install.txt` | Welcome message shown after Package Control install |

## Code Changes

### 1. Rename `vscode_*` → `settings_ui_*` (all files)

| Old constant / string | New |
|---|---|
| `PANEL_PHANTOM_NAV = "vscode_panel_nav"` | `"settings_ui_panel_nav"` |
| `PANEL_PHANTOM_CONTENT = "vscode_panel_content"` | `"settings_ui_panel_content"` |
| `NAV_MARK = "vscode_settings_nav"` | `"settings_ui_nav"` |
| `CONTENT_MARK = "vscode_settings_content"` | `"settings_ui_content"` |
| `prefs listener key "vscode_settings_panel"` | `"settings_ui"` |
| `id="vscode-settings"` in HTML body | `id="settings-ui"` |

Files affected: `panel.py`, `renderer.py`, `SettingsUI.py`.

### 2. Focus existing window (`SettingsUI.py`)

`SettingsUiOpenCommand.run()` currently opens a new window unconditionally. Fix:

```python
def run(self):
    win = panel.get_active_settings_window()
    if win:
        win.bring_to_front()
        return
    sublime.run_command("new_window")
    # ... rest of existing layout setup
```

### 3. Add `on_close` cleanup listener (`SettingsUI.py`)

When the user closes the settings window, module state is left dirty (polling flag stays True, phantom sets keep stale view IDs). Fix with a new listener:

```python
class SettingsUiCloseListener(sublime_plugin.EventListener):
    def on_close(self, view):
        if (view.settings().get(panel.CONTENT_MARK)
                or view.settings().get(panel.NAV_MARK)):
            panel.reset_module_state()
```

`panel.reset_module_state()` already exists and clears all flags correctly.

### 4. "View Raw Config" button — nav pane, always visible

A sticky "View Raw Config" link at the **top of the nav pane** (above the SETTINGS category list). Because the nav pane has its own independent scroll, this button stays visible regardless of how far down the user scrolls the content pane.

**Placement in nav HTML** (`renderer.build_nav_html`):
```html
<!-- inserted above <span class="navhead">SETTINGS</span> -->
<a class="rawlink" href="action:raw_config">{ } Raw Config</a>
```

**CSS** (added to renderer.CSS):
```css
.rawlink { display: block; text-decoration: none; color: var(--bluish);
           font-size: 12px; padding: 6px 10px; margin-bottom: 12px;
           border: 1px solid color(var(--bluish) alpha(0.35));
           border-radius: 5px; text-align: center; }
```

**Handler** added to `panel.on_nav()`:
```python
if href == "action:raw_config":
    _open_raw_config()
    return
```

**`_open_raw_config()` in `panel.py`**:
- Finds the settings window
- Opens `Packages/User/Preferences.sublime-settings` as a real editable view in group 1 (the content group)
- Sets JSON syntax highlighting on it
- If the raw config tab is already open, focuses it instead of opening twice

```python
def _open_raw_config() -> None:
    win = get_active_settings_window()
    if not win:
        return
    path = os.path.join(sublime.packages_path(), "User", "Preferences.sublime-settings")
    # Check if already open in this window
    for v in win.views():
        if v.file_name() == path:
            win.focus_view(v)
            return
    v = win.open_file(path)
    win.set_view_index(v, 1, 0)  # open in group 1 (content area)
    v.assign_syntax("Packages/JavaScript/JSON.sublime-syntax")
```

When the user closes the raw config tab, the existing `on_activated` listener re-activates polling and the phantom content view is still in group 1 as another tab — user switches back normally.

## Data Flow (unchanged)

```
User click / keymap
    → SettingsUiOpenCommand.run()
        → panel.render()
            → schema_loader.ensure_schema_loaded()  (one-shot)
            → renderer.build_nav_html()             → PhantomSet update (left pane)
            → renderer.build_content_phantoms()     → PhantomSet update (right pane)

User clicks link in phantom
    → panel.on_nav(href)
        → prefs.set_pref() / erase_pref() / toggle_pref()
        → panel.render_content()

User scrolls content pane
    → _start_poll() 250ms loop
        → state._category update
        → panel.render_nav()
```

## Distribution Checklist

- [ ] Folder renamed to `SettingsUI`
- [ ] All `vscode_*` identifiers renamed
- [ ] `update_plugin.py` deleted
- [ ] Keymaps added
- [ ] LICENSE added (MIT)
- [ ] `messages.json` + `messages/install.txt` added
- [ ] `SettingsUI.sublime-settings` added
- [ ] Focus-existing-window fix applied
- [ ] `on_close` listener added
- [ ] "View Raw Config" button in nav pane top
- [ ] `_open_raw_config()` handler in `panel.py`
