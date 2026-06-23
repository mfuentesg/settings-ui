# Changelog

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
