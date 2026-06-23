"""
Dynamic schema loader.

Augments the curated SECTIONS catalogue in schema.py with:
  1. Real defaults from Sublime's own Default/Preferences.sublime-settings
     (overrides our guessed defaults while keeping our richer descriptions).
  2. Auto-generated entries for any setting not yet in the catalogue
     (so new ST settings appear without any code change).

Call ensure_schema_loaded() once before first render.
"""

import re
import sublime
from . import schema

_KEY_LINE = re.compile(r'^"([^"\\]+)"\s*:')

# Guards against re-loading on every render.
_schema_loaded = False


def _parse_descriptions(text: str) -> dict:
    """Extract the comment above each JSON key as its description."""
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


def _load_default_prefs() -> tuple:
    """
    Load and merge Sublime's Default/Preferences files.

    Returns (defaults_dict, descriptions_dict).  The platform-specific file
    is loaded last so its values take precedence.
    """
    plat = {"osx": "OSX", "windows": "Windows", "linux": "Linux"}.get(
        sublime.platform(), ""
    )
    paths = ["Packages/Default/Preferences.sublime-settings"]
    if plat:
        paths.append("Packages/Default/Preferences (%s).sublime-settings" % plat)

    defaults, descs = {}, {}
    for p in paths:
        try:
            text = sublime.load_resource(p)
        except Exception:
            continue
        try:
            d = sublime.decode_value(text)
            if isinstance(d, dict):
                defaults.update(d)
        except Exception:
            pass
        descs.update(_parse_descriptions(text))
    return defaults, descs


def _auto_entry(key: str, default, desc: str) -> dict:
    """Create a schema entry for a setting not in the curated catalogue."""
    title = key.replace("_", " ").title()
    if isinstance(default, bool):
        return schema.b(key, title, desc, default)
    if isinstance(default, int):
        return schema.n(key, title, desc, default, step=1)
    if isinstance(default, float):
        return schema.n(key, title, desc, default, step=0.5, is_float=True)
    if isinstance(default, str):
        return schema.s(key, title, desc, default)
    return schema.j(key, title, desc, default)


def ensure_schema_loaded() -> None:
    """
    One-shot enrichment of the schema.  Safe to call multiple times.

    Mutates schema.SECTIONS and schema.KEY_INDEX in place.
    """
    global _schema_loaded
    if _schema_loaded:
        return
    _schema_loaded = True
    try:
        defaults, descs = _load_default_prefs()
        if not defaults:
            return
        # Patch real defaults into every curated entry (keep our descriptions).
        for entry in schema.KEY_INDEX.values():
            if entry["key"] in defaults:
                entry["default"] = defaults[entry["key"]]
        # Discover settings not covered by the catalogue.
        extra = [
            _auto_entry(k, defaults[k], descs.get(k, ""))
            for k in defaults
            if k not in schema.KEY_INDEX
        ]
        if extra:
            schema.SECTIONS.append(("OTHER", extra))
            for e in extra:
                schema.KEY_INDEX[e["key"]] = e
    except Exception as ex:
        sublime.status_message("Settings UI: dynamic schema load failed (%s)" % ex)


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
