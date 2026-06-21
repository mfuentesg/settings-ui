"""
Preference I/O helpers.

All reads and writes to Preferences.sublime-settings go through this module
so the rest of the codebase never touches the raw sublime.Settings object directly.
"""

import sublime
from . import schema

PREFS_FILE = "Preferences.sublime-settings"


# ---------------------------------------------------------------------------
# Low-level accessors
# ---------------------------------------------------------------------------

def prefs() -> sublime.Settings:
    """Return the live Preferences settings object."""
    return sublime.load_settings(PREFS_FILE)


def cur(key: str, default):
    """Return the current value of *key*, or *default* if unset."""
    val = prefs().get(key)
    return default if val is None else val


def is_modified(entry: dict) -> bool:
    """Return True if the setting differs from its schema default."""
    return cur(entry["key"], entry["default"]) != entry["default"]


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

def set_pref(key: str, value) -> None:
    """Persist *value* for *key* immediately."""
    s = prefs()
    s.set(key, value)
    sublime.save_settings(PREFS_FILE)


def erase_pref(key: str) -> None:
    """Remove *key* from user prefs (resets to default)."""
    s = prefs()
    s.erase(key)
    sublime.save_settings(PREFS_FILE)


def toggle_pref(key: str, default) -> None:
    """Flip a boolean preference."""
    set_pref(key, not bool(cur(key, default)))


def reset_all() -> None:
    """Erase every setting tracked in the schema (restore all defaults)."""
    s = prefs()
    for k in schema.KEY_INDEX:
        s.erase(k)
    sublime.save_settings(PREFS_FILE)
