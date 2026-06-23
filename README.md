# SettingsUI

A visual settings panel for Sublime Text 4 — browse and edit `Preferences.sublime-settings` through a two-pane UI instead of editing raw JSON.

## Features

- Two-pane layout: navigation on the left, settings on the right
- Groups settings into logical sections (Appearance, Editor, Files, etc.)
- Widgets matched to setting type: toggles, dropdowns, number inputs, color scheme / theme / font pickers
- Live search/filter across all settings
- Schema generator command that syncs the UI with new ST settings automatically

## Installation

Install via [Package Control](https://packagecontrol.io/packages/SettingsUI):

1. Open the command palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
2. Run **Package Control: Install Package**
3. Search for **SettingsUI**

Or clone this repo into your Packages directory:

```
~/Library/Application Support/Sublime Text/Packages/SettingsUI/   # macOS
%APPDATA%\Sublime Text\Packages\SettingsUI\                        # Windows
~/.config/sublime-text/Packages/SettingsUI/                        # Linux
```

## Usage

Open the command palette and run **Preferences: Settings UI**.

## Requirements

Sublime Text 4 (build 4000+).

## License

MIT
