# Changelog

## [Unreleased]

### Development
- Added `tests_st/test_new_view_guard.py`, a real-Sublime-Text regression test (via
  SublimeText/UnitTesting) for the first-run flash-then-crash — behavior a hand-rolled
  `sublime` fake can't faithfully validate. It drives the plugin's real, already-registered
  event listener through real view/window operations rather than instantiating the
  listener class directly (the settings-ui#3 close-deadlock regression already has this
  kind of coverage via the existing `tests_st/test_window_lifecycle.py`)
- Added `tools/run-st-tests-docker.sh` so `tests_st/` can be run locally via Docker,
  without a local Sublime Text install or license, matching what CI runs headlessly
- Pinned the `st-headless` CI job's `package-name` to `SettingsUI`, matching the actual
  package name (`Main.sublime-menu`/README/Package Control), instead of the name
  UnitTesting would otherwise derive from the GitHub repo name (`settings-ui`)

## [0.5.2] - 2026-09-18

### Fixed
- Added `args.default` (`"{}"`) to the `edit_settings` command entries in
  `Default.sublime-commands` and `Main.sublime-menu`'s `Settings` entry, per
  Package Control reviewer guidance
- Added a `Key Bindings` entry under `Preferences > Package Settings >
  SettingsUI` in `Main.sublime-menu`, so the shipped `(Example).sublime-keymap`
  files are discoverable from the menu
- `lib/pickers.py`'s font-discovery subprocess now hides its console window on
  Windows via `STARTUPINFO`/`SW_HIDE`
- Replaced `tests/conftest.py`'s manual `sys.path.insert` calls with pytest's
  declarative `pythonpath` option in `pyproject.toml`

## [0.5.1] - 2026-08-16

### Fixed
- Removed the top-level `__init__.py` — Sublime Text loads every top-level `.py`
  file in a package as a plugin, and the docs advise against shipping an
  `__init__` file there
- `Settings UI: Generate Schema` no longer reads or writes files inside the
  package directory (which is read-only when installed as a `.sublime-package`
  zip). Package files are now read through `sublime.load_resource()`, and the
  regenerated `schema.py` is written under `sublime.packages_path()`, where it
  acts as a standard package override for zipped installs
- Fixed a deadlock when closing the settings window: `on_pre_close` no longer
  schedules a redundant `close_window` while one is already in flight for that
  window, and reopening the panel while it's already open no longer races with
  the in-progress close
- Fixed a crash on first open: the new-view guard now requires both the nav
  and content panes to be present before treating a window as the settings
  window, so it no longer closes the content view while it's still being set
  up
- Files opened inside the settings window (e.g. via File → Open Recent) are
  now redirected to a normal window instead of being silently discarded
- Re-running the `Settings UI` command while the panel is already open now
  closes and reopens it instead of calling `bring_to_front()`, which could
  leave the panel inaccessible on macOS if it lived on a different Space
- Commands run from a `cmd:` link and the "View Raw Config" button now open
  in a non-settings window instead of the settings window itself
- Fixed a crash (`NameError`) when editing a JSON-typed setting from the
  panel — the `json` module was used but never imported

## [0.5.0] - 2026-06-23

### Fixed
- Added `edit_settings` command entry (`Preferences: SettingsUI Settings`) to the command palette
- Added `Preferences → Package Settings → SettingsUI → Settings` menu entry to satisfy Package Control reviewer requirements

## [0.4.0] - 2026-06-23

### Changed
- Number settings now use an inline edit link instead of a stepper widget
- Fixed minihtml spacing issues in the content pane

### Performance
- Font picker scan is significantly faster; pre-selects the current active font

## [0.3.0] - 2026-06-22

### Fixed
- Renamed active keymap files to `(Example)` variants to satisfy Package Control's
  requirement that key bindings with no context use example files

## [0.2.0] - 2026-06-22

### Changed
- Moved all helper modules into `lib/` subpackage to comply with Package Control's
  plugin isolation rules (no root-level imports)
- Added `.gitignore` to exclude `__pycache__` and compiled `.pyc` files
- Added `README.md` for Package Control submission

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
