# Settings UI for Sublime Text 4

A native-styled Settings editor for Sublime Text 4 (using inline / minihtml). 

Currently, Sublime Text only allows editing settings via a plain JSON file. This plugin brings a visual, categorised interface akin to VS Code's settings panel directly to Sublime Text.

## Features

- **Native Look & Feel:** Colors are dynamically pulled from the active color scheme via minihtml variables (e.g., `var(--background)`, `var(--foreground)`, `var(--bluish)`). The panel perfectly matches your current theme.
- **Categorised Navigation:** Easily navigate through well-organized categories like Appearance, Editor, Status Bar, Files, and more.
- **Search:** Quickly search for settings across all categories.
- **Rich Input:** 
  - Toggle booleans instantly.
  - Increment/decrement number settings or type exact values.
  - Native pickers for color schemes and UI themes with live previews.
  - Dropdowns for settings with multiple predefined choices.
  - Free-form text and JSON inputs for more complex settings.
- **Dynamic Schema:** Automatically discovers settings from Default preferences that aren't manually curated, ensuring you can still edit them via the UI.

## Installation

### Manual Installation
1. Clone or download this repository into your Sublime Text `Packages` directory.
   - macOS: `~/Library/Application Support/Sublime Text/Packages`
   - Windows: `%APPDATA%\Sublime Text\Packages`
   - Linux: `~/.config/sublime-text/Packages`
2. Restart Sublime Text.

## Usage

You can open the Settings UI using one of the following methods:
- Go to `Preferences > Settings UI` from the main menu.
- Open the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) and search for `Preferences: Settings UI`.

## Design Notes

- No hardcoded font families; the panel inherits the editor's default font.
- Left column: Category navigator. Right column: Selected category's settings or search results.
- Built exclusively using Sublime Text 4's `minihtml` rendering engine without external webviews.
