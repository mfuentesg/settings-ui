"""
Settings UI for Sublime Text 4 — plugin entry point.

Responsibilities
----------------
* Declare the sublime_plugin command and event-listener classes that Sublime
  Text discovers automatically by scanning this file.
* Implement plugin_loaded() / plugin_unloaded() lifecycle hooks for auto-reload.
* Delegate all real work to panel.py and the other modules.

Install: symlink or copy this directory to
         ~/Library/Application Support/Sublime Text/Packages/SettingsUI/

Usage (Command Palette): Preferences: Settings UI
      (Console)        : sublime.active_window().run_command("settings_ui_open")
"""

import sublime
import sublime_plugin
from .lib import panel, state, prefs, schema_loader


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

class SettingsUiOpenCommand(sublime_plugin.WindowCommand):
    """Open the Settings UI in a dedicated two-pane window."""

    def run(self) -> None:
        existing = panel.get_active_settings_window()
        if existing:
            # bring_to_front() cannot cross macOS Spaces; user may be taken to
            # the Space where the settings window lives.
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

        # Create views and set their marks before render() scans for them.
        # render_nav/render_content both call get_active_settings_window()
        # which looks for CONTENT_MARK — if marks aren't set first, both
        # functions exit early and no phantoms are created.
        panel.get_nav_view(win)
        panel.get_content_view(win)
        panel.render()


# ---------------------------------------------------------------------------
# Event listeners
# ---------------------------------------------------------------------------

class SettingsUiSyncListener(sublime_plugin.EventListener):
    """Start the scroll-sync poll whenever the user focuses a settings pane."""

    def on_activated(self, view: sublime.View) -> None:
        if (view.settings().get(panel.CONTENT_MARK)
                or view.settings().get(panel.NAV_MARK)):
            panel._start_poll()


class SettingsUiNewViewGuard(sublime_plugin.EventListener):
    """Discard any new regular view opened inside the settings window (e.g. Cmd+N)."""

    def on_new(self, view: sublime.View) -> None:
        win = view.window()
        if not win:
            return
        is_settings_win = any(
            v.settings().get(panel.CONTENT_MARK) or v.settings().get(panel.NAV_MARK)
            for v in win.views()
            if v.id() != view.id()
        )
        if is_settings_win:
            sublime.set_timeout(view.close, 0)


_closing_window_id = None


class SettingsUiCloseListener(sublime_plugin.EventListener):
    """Close the whole settings window when either pane is closed individually."""

    def on_pre_close(self, view: sublime.View) -> None:
        global _closing_window_id
        is_nav = view.settings().get(panel.NAV_MARK)
        is_content = view.settings().get(panel.CONTENT_MARK)
        if not (is_nav or is_content):
            return
        win = view.window()
        if not win:
            return
        if _closing_window_id == win.id():
            return
        _closing_window_id = win.id()
        win.run_command("close_window")

    def on_close(self, view: sublime.View) -> None:
        global _closing_window_id
        if (view.settings().get(panel.CONTENT_MARK)
                or view.settings().get(panel.NAV_MARK)):
            if panel.get_active_settings_window() is None:
                _closing_window_id = None
                panel.reset_module_state()


# ---------------------------------------------------------------------------
# Plugin lifecycle
# ---------------------------------------------------------------------------

def plugin_loaded() -> None:
    """
    Called by Sublime Text when the package is first loaded *and* every time
    a .py file in the package is saved (auto-reload).

    If the settings window is already open (from a previous session or from
    the current session before the save), re-render it in place so changes
    to the code / CSS are immediately visible without reopening the window.
    """
    schema_loader.register_listener()
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


def plugin_unloaded() -> None:
    """
    Called just before the package is unloaded (on save / disable / quit).

    Clears all listeners and resets every flag so plugin_loaded() can
    re-initialise from a clean slate after the hot-reload.
    """
    prefs.prefs().clear_on_change("settings_ui")
    schema_loader.unregister_listener()
    panel.reset_module_state()
    # Reset shared state so filter/category don't bleed across reloads.
    state._filter   = ""
    state._category = 0
    # Force schema re-parse so any new ST defaults are picked up.
    schema_loader._schema_loaded = False
