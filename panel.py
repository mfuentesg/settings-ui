"""
Window / view management, rendering orchestration, scroll-sync polling,
preferences change listener, and the central navigation router.

This is the integration layer: it imports all other modules and wires them
together.  Nothing should import this module except SettingsUI.py (the entry
point) and lazy closures inside pickers.py.
"""

import os
import sublime
from . import schema, schema_loader, prefs, renderer, pickers, state

# ---------------------------------------------------------------------------
# View identity markers (stored in view.settings())
# ---------------------------------------------------------------------------

PANEL_PHANTOM_NAV     = "settings_ui_panel_nav"
PANEL_PHANTOM_CONTENT = "settings_ui_panel_content"
NAV_MARK              = "settings_ui_nav"      # left pane
CONTENT_MARK          = "settings_ui_content"  # right pane

# ---------------------------------------------------------------------------
# Module-level state (private to this module, not shared)
# ---------------------------------------------------------------------------

_phantom_sets: dict   = {}   # view.id() → sublime.PhantomSet
_prefs_listener_on    = False
_render_scheduled     = False
_polling              = False


# ---------------------------------------------------------------------------
# View / window helpers
# ---------------------------------------------------------------------------

def _prep_view(view: sublime.View, mark: str) -> None:
    """Configure a view to act as a chromeless settings pane."""
    is_content = mark == CONTENT_MARK
    view.set_name("\u2699  Settings" if is_content else "\u2699  Navigation")
    view.set_scratch(True)
    view.set_read_only(True)
    vs = view.settings()
    vs.set(mark, True)
    vs.set("line_numbers",       False)
    vs.set("gutter",             False)
    vs.set("draw_white_space",   "none")
    vs.set("draw_indent_guides", False)
    vs.set("highlight_line",     False)
    vs.set("rulers",             [])
    vs.set("word_wrap",          False)
    vs.set("scroll_past_end",    False)
    vs.set("fold_buttons",       False)


def get_active_settings_window() -> sublime.Window | None:
    """Return the window that hosts the settings panes, or None."""
    for w in sublime.windows():
        for v in w.views():
            if v.settings().get(CONTENT_MARK):
                return w
    return None


def get_nav_view(window: sublime.Window) -> sublime.View:
    """Return the existing nav view or create a new one in group 0."""
    for v in window.views():
        if v.settings().get(NAV_MARK):
            return v
    v = window.new_file()
    window.set_view_index(v, 0, 0)
    _prep_view(v, NAV_MARK)
    return v


def get_content_view(window: sublime.Window) -> sublime.View:
    """Return the existing content view or create a new one in group 1."""
    for v in window.views():
        if v.settings().get(CONTENT_MARK):
            return v
    v = window.new_file()
    window.set_view_index(v, 1, 0)
    _prep_view(v, CONTENT_MARK)
    # Pre-populate with enough lines for all phantom anchor points.
    v.set_read_only(False)
    v.run_command("append", {"characters": "\n" * 200})
    v.set_read_only(True)
    return v


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------

def render_nav() -> None:
    """Rebuild the navigation sidebar phantom."""
    win = get_active_settings_window()
    if not win:
        return
    view = get_nav_view(win)
    pset = _phantom_sets.get(view.id())
    if pset is None:
        view.erase_phantoms(PANEL_PHANTOM_NAV)
        pset = sublime.PhantomSet(view, PANEL_PHANTOM_NAV)
        _phantom_sets[view.id()] = pset

    vp = view.viewport_position()
    html = renderer.build_nav_html(schema.SECTIONS, state._filter, state._category)
    pset.update([
        sublime.Phantom(
            sublime.Region(0, 0), html,
            sublime.LAYOUT_BLOCK, on_navigate=on_nav,
        )
    ])
    sublime.set_timeout(lambda: view.set_viewport_position(vp, False), 0)


def render_content() -> None:
    """Rebuild all content-pane phantoms."""
    win = get_active_settings_window()
    if not win:
        return
    view = get_content_view(win)
    pset = _phantom_sets.get(view.id())
    if pset is None:
        view.erase_phantoms(PANEL_PHANTOM_CONTENT)
        pset = sublime.PhantomSet(view, PANEL_PHANTOM_CONTENT)
        _phantom_sets[view.id()] = pset

    vp = view.viewport_position()
    phantoms = renderer.build_content_phantoms(
        view, schema.SECTIONS, state._filter, on_nav
    )
    pset.update(phantoms)
    sublime.set_timeout(lambda: view.set_viewport_position(vp, False), 0)


def render() -> None:
    """Full render: schema, prefs listener, both panes."""
    schema_loader.ensure_schema_loaded()
    _ensure_prefs_listener()
    render_nav()
    render_content()


# ---------------------------------------------------------------------------
# Scroll-sync: keep the nav highlight in sync with the content scroll position
# ---------------------------------------------------------------------------

def scroll_to_category(cat_index: int) -> None:
    """Scroll the content pane to the top of section *cat_index*."""
    win = get_active_settings_window()
    if not win:
        return
    view = get_content_view(win)
    # +1 because line 0 is the header phantom
    pt = view.text_point(cat_index + 1, 0)
    _, y = view.text_to_layout(pt)
    view.set_viewport_position((0, y), True)


def _start_poll() -> None:
    """
    Start the 250 ms polling loop that updates the nav highlight as the
    user scrolls the content pane.  Safe to call multiple times – the loop
    is only started once.
    """
    global _polling
    if _polling:
        return
    _polling = True

    def poll() -> None:
        global _polling
        win = get_active_settings_window()
        if not win:
            _polling = False
            return

        cv = get_content_view(win)
        vy = cv.viewport_position()[1]

        # Only sync highlight when not in search mode
        if not state._filter:
            best_cat = 0
            for i in range(len(schema.SECTIONS)):
                pt = cv.text_point(i + 1, 0)
                _, y = cv.text_to_layout(pt)
                # 50 px look-ahead so the nav item activates before the
                # section header fully scrolls out of view
                if y - 50 <= vy:
                    best_cat = i
                else:
                    break
            if state._category != best_cat:
                state._category = best_cat
                render_nav()

        sublime.set_timeout(poll, 250)

    poll()


# ---------------------------------------------------------------------------
# Preferences change listener (re-render when prefs change outside our UI)
# ---------------------------------------------------------------------------

def _ensure_prefs_listener() -> None:
    """Register a one-shot listener on Preferences to keep the panel fresh."""
    global _prefs_listener_on
    if _prefs_listener_on:
        return
    prefs.prefs().add_on_change("settings_ui", _on_prefs_changed)
    _prefs_listener_on = True


def _on_prefs_changed() -> None:
    global _render_scheduled
    if _render_scheduled:
        return
    _render_scheduled = True
    sublime.set_timeout(_do_scheduled_render, 50)


def _do_scheduled_render() -> None:
    global _render_scheduled
    _render_scheduled = False
    if get_active_settings_window() is not None:
        render_content()


# ---------------------------------------------------------------------------
# Navigation router  (href → action)
# ---------------------------------------------------------------------------

def on_nav(href: str) -> None:
    """
    Central click handler for all minihtml links in both panes.

    href formats
    ------------
    action:reset_all        – erase all user prefs
    action:search           – open the search input panel
    action:clear_search     – clear the search filter
    cat:<index>             – jump to a category by index
    cmd:<command_name>      – run a Sublime command (e.g. select_color_scheme)
    respick:<key>           – open resource picker for <key>
    listpick:<key>          – open dynamic list picker for <key>
    edit:<key>              – open input panel to edit <key>
    toggle:<key>            – flip a boolean setting
    reset:<key>             – erase a setting (restore default)
    enum:<key>:<choice_idx> – select an enum value by index
    step:<key>:<delta>      – increment/decrement a numeric setting
    """
    # ---- Global actions --------------------------------------------------
    if href == "action:reset_all":
        prefs.reset_all()
        render_content()
        return
    if href == "action:search":
        pickers.open_search()
        return
    if href == "action:clear_search":
        state._filter = ""
        render_nav()
        render_content()
        return
    if href == "action:raw_config":
        _open_raw_config()
        return

    cmd, _sep, rest = href.partition(":")

    # ---- Category navigation --------------------------------------------
    if cmd == "cat":
        was_filter = bool(state._filter)
        state._category = int(rest)
        state._filter = ""
        render_nav()
        if was_filter:
            render_content()
        # Small delay lets the nav phantom finish painting before scrolling
        sublime.set_timeout(lambda: scroll_to_category(state._category), 10)
        return

    # ---- Delegated to pickers -------------------------------------------
    if cmd == "cmd":
        sublime.active_window().run_command(rest)
        return
    if cmd == "respick":
        pickers.open_resource_picker(rest)
        return
    if cmd == "listpick":
        pickers.open_list_picker(rest)
        return
    if cmd == "edit":
        pickers.open_edit(rest)
        return

    # ---- Preference mutations (synchronous, followed by content re-render)
    if cmd == "toggle":
        prefs.toggle_pref(rest, schema.KEY_INDEX[rest]["default"])
    elif cmd == "reset":
        prefs.erase_pref(rest)
    elif cmd == "enum":
        key, idx_str = rest.split(":", 1)
        value = schema.norm_choices(schema.KEY_INDEX[key])[int(idx_str)][0]
        prefs.set_pref(key, value)
    elif cmd == "step":
        key, delta_str = rest.split(":", 1)
        en = schema.KEY_INDEX[key]
        try:
            base = float(prefs.cur(key, en["default"]))
        except (TypeError, ValueError):
            base = float(en["default"])
        new = base + float(delta_str) * en.get("step", 1)
        new = round(new, 4) if en.get("is_float") else int(new)
        prefs.set_pref(key, new)

    render_content()


# ---------------------------------------------------------------------------
# Module reset (called from plugin_unloaded to clean up before hot-reload)
# ---------------------------------------------------------------------------

def reset_module_state() -> None:
    """Reset all flags so plugin_loaded() re-initialises everything cleanly."""
    global _prefs_listener_on, _render_scheduled, _polling, _phantom_sets
    _prefs_listener_on = False
    _render_scheduled  = False
    _polling           = False
    _phantom_sets      = {}


def _open_raw_config() -> None:
    """Open Preferences.sublime-settings as an editable tab in group 1."""
    win = get_active_settings_window()
    if not win:
        return
    path = os.path.join(sublime.packages_path(), "User", "Preferences.sublime-settings")
    for v in win.views():
        if v.file_name() == path:
            win.focus_view(v)
            return
    v = win.open_file(path)
    win.set_view_index(v, 1, 0)
    v.assign_syntax("Packages/JavaScript/JSON.sublime-syntax")
