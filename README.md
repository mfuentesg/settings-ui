# SettingsUI

[![Package Control](https://img.shields.io/packagecontrol/dt/SettingsUI.svg)](https://packagecontrol.io/packages/SettingsUI)
[![GitHub release](https://img.shields.io/github/release/mfuentesg/settings-ui.svg)](https://github.com/mfuentesg/settings-ui/releases)
[![License](https://img.shields.io/github/license/mfuentesg/settings-ui.svg)](LICENSE)

A visual settings panel for Sublime Text 4 — browse and edit `Preferences.sublime-settings` through a two-pane UI instead of editing raw JSON.

<a href="https://www.buymeacoffee.com/mfuentesg" target="_blank">
  <img height="41" src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" />
</a>

---

## Features

- **Two-pane layout** — category navigation on the left, settings on the right
- **Grouped sections** — Appearance, Editor, Files, Search, and more
- **Smart widgets** — toggles for booleans, radio buttons for enums, native pickers for color schemes, themes, and fonts
- **Live search** — filter across all settings instantly
- **Schema generator** — syncs the UI with new ST settings automatically via a single command
- **Auto-reload** — re-renders the panel whenever you save a plugin file during development
- **View Raw Config** — jump straight to `Preferences.sublime-settings` from the UI

## Installation

### Package Control (recommended)

1. Open the command palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
2. Run **Package Control: Install Package**
3. Search for **SettingsUI**

### Manual

Clone this repo into your Packages directory:

```
# macOS
~/Library/Application Support/Sublime Text/Packages/SettingsUI/

# Windows
%APPDATA%\Sublime Text\Packages\SettingsUI\

# Linux
~/.config/sublime-text/Packages/SettingsUI/
```

## Usage

Open the command palette and run **Preferences: Settings UI**, or use the keyboard shortcut:

| Platform | Shortcut |
|----------|----------|
| macOS    | `Cmd+,`  |
| Windows / Linux | `Ctrl+,` |

## Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `open_on_startup` | boolean | `false` | Open the settings panel automatically when Sublime Text starts |

Edit via **Preferences → Package Settings → SettingsUI → Settings**.

## Commands

| Command | Description |
|---------|-------------|
| **Preferences: Settings UI** | Open the visual settings panel |
| **Settings UI: Generate Schema** | Regenerate the schema from the current ST defaults |

## Requirements

Sublime Text 4 (build 4000+).

## License

MIT — see [LICENSE](LICENSE).
