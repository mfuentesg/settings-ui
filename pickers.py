"""
Input panels, quick-panels, and dynamic list providers for the Settings UI.

Pickers modify preferences then need to trigger a re-render.  To break the
circular dependency with `panel`, render calls are done via a lazy import
inside callback closures – the import only happens after both modules are
fully loaded.
"""

import json
import os
import subprocess
import sys
import threading
import sublime
from . import schema, prefs, state


# ---------------------------------------------------------------------------
# Subprocess helper (used by font discovery)
# ---------------------------------------------------------------------------

def _run_cmd(args: list, timeout: int = 20) -> str | None:
    """Run a subprocess, return decoded stdout or None on failure."""
    try:
        p = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout
        )
        return p.stdout.decode("utf-8", "replace")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Font discovery
# ---------------------------------------------------------------------------

_font_cache = None


def _scan_font_files() -> set:
    """Fallback font discovery by scanning known font directories."""
    files: set = set()
    plat = sys.platform
    if plat.startswith("win"):
        d = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        if os.path.isdir(d):
            files.update(os.listdir(d))
    elif plat == "darwin":
        for d in ("/Library/Fonts", "/System/Library/Fonts",
                  os.path.expanduser("~/Library/Fonts")):
            if os.path.isdir(d):
                files.update(os.listdir(d))
    else:
        for d in ("/usr/share/fonts", "/usr/local/share/fonts",
                  os.path.expanduser("~/.local/share/fonts"),
                  os.path.expanduser("~/.fonts")):
            if os.path.isdir(d):
                for root_dir, _dirs, fs in os.walk(d):
                    files.update(fs)
    exts = (".ttf", ".otf", ".ttc", ".fon")
    return {os.path.splitext(f)[0].replace("_", " ").strip()
            for f in files if f.lower().endswith(exts)}


def list_system_fonts() -> list:
    """
    Return [(label, value), …] of installed font families.

    Results are cached after the first call (fonts don't change mid-session).
    """
    global _font_cache
    if _font_cache is not None:
        return _font_cache

    fams: set = set()

    # Try fc-list (Linux / macOS with fontconfig)
    out = _run_cmd(["fc-list", ":", "family"])
    if out:
        for line in out.splitlines():
            for fam in line.split(","):
                fam = fam.strip()
                if fam:
                    fams.add(fam)

    # macOS fallback via system_profiler
    if not fams and sys.platform == "darwin":
        out = _run_cmd(["system_profiler", "-json", "SPFontsDataType"])
        if out:
            try:
                data = json.loads(out)
                for entry in data.get("SPFontsDataType", []):
                    for tf in entry.get("typefaces", []):
                        fam = tf.get("family")
                        if fam:
                            fams.add(fam)
            except Exception:
                pass

    if not fams:
        fams.update(_scan_font_files())

    items = [("(default)", "")]
    items += [(f, f) for f in sorted(fams, key=lambda s: s.lower())]
    _font_cache = items
    return items


# Provider registry: provider name → callable returning [(label, value), …]
PROVIDERS: dict = {"fonts": list_system_fonts}


# ---------------------------------------------------------------------------
# Resource pickers (themes / color schemes)
# ---------------------------------------------------------------------------

def list_themes() -> list:
    seen: set = set()
    out = []
    for r in sublime.find_resources("*.sublime-theme"):
        name = r.rsplit("/", 1)[-1]
        if name not in seen:
            seen.add(name)
            out.append((name, name))
    out.sort(key=lambda x: x[0].lower())
    return out


def list_color_schemes() -> list:
    seen: set = set()
    out = []
    for r in sublime.find_resources("*.sublime-color-scheme"):
        name = r.rsplit("/", 1)[-1]
        if name not in seen:
            seen.add(name)
            out.append((name, name))
    for r in sublime.find_resources("*.tmTheme"):
        out.append((r.rsplit("/", 1)[-1], r))   # legacy: referenced by full path
    out.sort(key=lambda x: x[0].lower())
    return out


# ---------------------------------------------------------------------------
# Lazy render helpers (avoids circular import with panel)
# ---------------------------------------------------------------------------

def _refresh_content() -> None:
    """Re-render just the content pane (cheap, avoids full nav rebuild)."""
    from . import panel
    panel.render_content()


def _refresh_all() -> None:
    """Re-render both panes (needed when the filter / category changes)."""
    from . import panel
    panel.render_nav()
    panel.render_content()


# ---------------------------------------------------------------------------
# Free-form value editor (input panel)
# ---------------------------------------------------------------------------

def open_edit(key: str) -> None:
    """Open Sublime's input panel pre-filled with the current value of *key*."""
    en = schema.KEY_INDEX[key]
    val = prefs.cur(key, en["default"])
    initial = json.dumps(val) if en["type"] == "json" else str(val)

    def on_done(text: str) -> None:
        try:
            if en["type"] == "number":
                new = float(text) if en.get("is_float") else int(text)
            elif en["type"] == "json":
                new = json.loads(text)
            else:
                new = text
        except Exception as ex:
            sublime.status_message("Settings UI: invalid value (%s)" % ex)
            return
        prefs.set_pref(key, new)
        _refresh_content()

    sublime.active_window().show_input_panel(
        "Set %s" % key, initial, on_done, None, None
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def open_search() -> None:
    """Open Sublime's input panel for the settings search filter."""
    def on_done(text: str) -> None:
        state._filter = text.strip().lower()
        _refresh_all()

    sublime.active_window().show_input_panel(
        "Search settings", state._filter, on_done, None, None
    )


# ---------------------------------------------------------------------------
# Resource picker (theme / color scheme quick-panel)
# ---------------------------------------------------------------------------

def open_resource_picker(key: str) -> None:
    """Show a quick-panel of available theme or color-scheme resources."""
    en = schema.KEY_INDEX[key]
    items = list_themes() if en["kind"] == "theme" else list_color_schemes()
    if not items:
        sublime.status_message("Settings UI: no %s resources found" % en["kind"])
        return

    labels = [lab for lab, _v in items]
    cur_val = prefs.cur(key, en["default"])
    selected = next((i for i, (_l, v) in enumerate(items) if v == cur_val), -1)

    def on_done(idx: int) -> None:
        if idx == -1:
            return
        prefs.set_pref(key, items[idx][1])
        _refresh_content()

    sublime.active_window().show_quick_panel(labels, on_done, 0, selected, None)


# ---------------------------------------------------------------------------
# Dynamic list picker (e.g. fonts)
# ---------------------------------------------------------------------------

def open_list_picker(key: str) -> None:
    """
    Show a quick-panel backed by a named provider.

    The provider is called in a background thread so font enumeration doesn't
    block the UI.
    """
    en = schema.KEY_INDEX[key]
    provider = PROVIDERS.get(en.get("provider"))
    if provider is None:
        return
    sublime.status_message("Settings UI: loading %s\u2026" % en.get("provider"))

    def work() -> None:
        items = provider()
        sublime.set_timeout(lambda: _show_list_picker(key, items), 0)

    threading.Thread(target=work, daemon=True).start()


def _show_list_picker(key: str, items: list) -> None:
    if not items:
        sublime.status_message("Settings UI: no options found")
        return

    en = schema.KEY_INDEX[key]
    labels = [lab for lab, _v in items]
    cur_val = prefs.cur(key, en["default"])
    selected = next((i for i, (_l, v) in enumerate(items) if v == cur_val), -1)

    def on_done(idx: int) -> None:
        if idx == -1:
            return
        prefs.set_pref(key, items[idx][1])
        _refresh_content()

    sublime.active_window().show_quick_panel(labels, on_done, 0, selected, None)
