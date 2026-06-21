import os

target = "/Users/mfuentesg/code/settings-ui/SettingsUI.py"
with open(target, "r") as f:
    content = f.read()

# Find the start of build_html
idx = content.find("def build_html():")
if idx == -1:
    print("Could not find build_html()")
    exit(1)

head = content[:idx]

tail = """def build_nav_html():
    nav = ['<div class="nav"><span class="navhead">SETTINGS</span>']
    for i, (title, _e) in enumerate(SECTIONS):
        active = (not _filter and i == _category)
        nav.append('<a class="navitem{a}" href="cat:{i}">{t}</a>'.format(
            a=" active" if active else "", i=i, t=esc(title)))
    nav.append('<a class="navreset" href="action:reset_all">Restore all defaults</a>')
    nav.append('</div>')
    return ('<body id="settings-ui"><style>' + CSS + '</style>'
            '<div class="shell" style="padding-bottom: 2000px;">' + "".join(nav) + '</div></body>')


def build_content_phantoms(view):
    phantoms = []
    
    # 1. Header and Search
    c = ['<div class="content">', '<span class="h1">Settings</span>']
    if _filter:
        c.append('<a class="search active" href="action:search">Search: {f}</a>'.format(f=esc(_filter)))
        c.append('<span class="subnote"><a href="action:clear_search">Clear search</a> '
                 '&#160;&#183;&#160; <a href="action:reset_all">Restore all defaults</a></span></div>')
    else:
        c.append('<a class="search" href="action:search">Search settings&#8230;</a>')
        c.append('<span class="subnote">Changes apply immediately. '
                 '&#160;&#183;&#160; <a href="action:reset_all">Restore all defaults</a></span></div>')
                 
    html = ('<body id="settings-ui"><style>' + CSS + '</style>'
            '<div class="shell" style="padding-bottom: 0;">' + "".join(c) + '</div></body>')
    phantoms.append(sublime.Phantom(sublime.Region(0, 0), html, sublime.LAYOUT_BLOCK, on_navigate=on_nav))

    # 2. Sections
    line_idx = 1
    for i, (title, entries) in enumerate(SECTIONS):
        if _filter:
            entries = [en for en in entries if matches(en)]
            if not entries:
                continue
                
        c = ['<div class="content" style="margin-top: 0;">']
        c.append('<span class="section">{s}</span>'.format(s=esc(title)))
        for en in entries:
            c.append(RENDERERS[en["type"]](en))
        c.append('</div>')
        html = ('<body id="settings-ui"><style>' + CSS + '</style>'
                '<div class="shell" style="padding-top: 0; padding-bottom: 0;">' + "".join(c) + '</div></body>')
        pt = view.text_point(line_idx, 0)
        phantoms.append(sublime.Phantom(sublime.Region(pt, pt), html, sublime.LAYOUT_BLOCK, on_navigate=on_nav))
        if not _filter:
            line_idx += 1

    # 3. Footer
    c = ['<div class="content" style="margin-top: 0;">']
    c.append('<div style="height: 80vh;"></div></div>')
    html = ('<body id="settings-ui"><style>' + CSS + '</style>'
            '<div class="shell" style="padding-top: 0;">' + "".join(c) + '</div></body>')
    pt = view.text_point(line_idx if not _filter else 1, 0)
    phantoms.append(sublime.Phantom(sublime.Region(pt, pt), html, sublime.LAYOUT_BLOCK, on_navigate=on_nav))

    return phantoms


# ---------------------------------------------------------------------------
# Two-panel hosting
# ---------------------------------------------------------------------------

PANEL_PHANTOM_NAV = "settings_ui_panel_nav"
PANEL_PHANTOM_CONTENT = "settings_ui_panel_content"
NAV_MARK = "settings_ui_nav"
CONTENT_MARK = "settings_ui_content"

_phantom_sets = {}
_prefs_listener_on = False
_render_scheduled = False
_polling = False


def _prep_view(view, mark):
    view.set_name("\u2699  Settings" if mark == CONTENT_MARK else "\u2699  Navigation")
    view.set_scratch(True)
    view.set_read_only(True)
    vs = view.settings()
    vs.set(mark, True)
    vs.set("line_numbers", False)
    vs.set("gutter", False)
    vs.set("draw_white_space", "none")
    vs.set("draw_indent_guides", False)
    vs.set("highlight_line", False)
    vs.set("rulers", [])
    vs.set("word_wrap", False)
    vs.set("scroll_past_end", False)
    vs.set("fold_buttons", False)
    vs.set("color_scheme", "Mariana.sublime-color-scheme") # Force a default or let it inherit


def get_active_settings_window():
    for w in sublime.windows():
        for v in w.views():
            if v.settings().get(CONTENT_MARK):
                return w
    return None


def get_nav_view(window):
    for v in window.views():
        if v.settings().get(NAV_MARK):
            return v
    v = window.new_file()
    window.set_view_index(v, 0, 0)
    _prep_view(v, NAV_MARK)
    return v


def get_content_view(window):
    for v in window.views():
        if v.settings().get(CONTENT_MARK):
            return v
    v = window.new_file()
    window.set_view_index(v, 1, 0)
    _prep_view(v, CONTENT_MARK)
    v.set_read_only(False)
    v.run_command("append", {"characters": "\\n" * (len(SECTIONS) + 5)})
    v.set_read_only(True)
    return v


def render_nav():
    win = get_active_settings_window()
    if not win: return
    view = get_nav_view(win)
    pset = _phantom_sets.get(view.id())
    if pset is None:
        view.erase_phantoms(PANEL_PHANTOM_NAV)
        pset = sublime.PhantomSet(view, PANEL_PHANTOM_NAV)
        _phantom_sets[view.id()] = pset
    vp = view.viewport_position()
    pset.update([sublime.Phantom(sublime.Region(0, 0), build_nav_html(),
                                 sublime.LAYOUT_BLOCK, on_navigate=on_nav)])
    sublime.set_timeout(lambda: view.set_viewport_position(vp, False), 0)


def render_content():
    win = get_active_settings_window()
    if not win: return
    view = get_content_view(win)
    pset = _phantom_sets.get(view.id())
    if pset is None:
        view.erase_phantoms(PANEL_PHANTOM_CONTENT)
        pset = sublime.PhantomSet(view, PANEL_PHANTOM_CONTENT)
        _phantom_sets[view.id()] = pset
    vp = view.viewport_position()
    pset.update(build_content_phantoms(view))
    sublime.set_timeout(lambda: view.set_viewport_position(vp, False), 0)


def render():
    ensure_schema_loaded()
    _ensure_prefs_listener()
    render_nav()
    render_content()


def scroll_to_category(cat_index):
    win = get_active_settings_window()
    if not win: return
    view = get_content_view(win)
    pt = view.text_point(cat_index + 1, 0)
    _, y = view.text_to_layout(pt)
    view.set_viewport_position((0, y), True)


def _start_poll():
    global _polling
    if _polling: return
    _polling = True
    def poll():
        win = get_active_settings_window()
        if not win:
            global _polling
            _polling = False
            return
            
        cv = get_content_view(win)
        vy = cv.viewport_position()[1]
        
        best_cat = 0
        if not _filter:
            for i in range(len(SECTIONS)):
                pt = cv.text_point(i + 1, 0)
                _, y = cv.text_to_layout(pt)
                if y - 50 <= vy:
                    best_cat = i
                else:
                    break
                    
            global _category
            if _category != best_cat:
                _category = best_cat
                render_nav()
            
        sublime.set_timeout(poll, 250)
    poll()


def _ensure_prefs_listener():
    global _prefs_listener_on
    if _prefs_listener_on:
        return
    prefs().add_on_change("settings_ui", _on_prefs_changed)
    _prefs_listener_on = True


def _on_prefs_changed():
    global _render_scheduled
    if _render_scheduled:
        return
    _render_scheduled = True
    sublime.set_timeout(_do_scheduled_render, 50)


def _do_scheduled_render():
    global _render_scheduled
    _render_scheduled = False
    if get_active_settings_window() is not None:
        render()


# ---------------------------------------------------------------------------
# Input panel (free-form values, since minihtml has no text inputs)
# ---------------------------------------------------------------------------

def open_edit(key):
    en = KEY_INDEX[key]
    window = sublime.active_window()
    val = cur(key, en["default"])
    initial = json.dumps(val) if en["type"] == "json" else str(val)

    def on_done(text):
        try:
            if en["type"] == "number":
                new = float(text) if en.get("is_float") else int(text)
            elif en["type"] == "json":
                new = json.loads(text)
            else:
                new = text
        except Exception as ex:
            sublime.status_message("Settings: invalid value (%s)" % ex)
            return
        set_pref(key, new)
        render_content()

    window.show_input_panel("Set %s" % key, initial, on_done, None, None)


def open_search():
    window = sublime.active_window()

    def on_done(text):
        global _filter
        _filter = text.strip().lower()
        render_nav()
        render_content()

    window.show_input_panel("Search settings", _filter, on_done, None, None)


def list_themes():
    seen, out = set(), []
    for r in sublime.find_resources("*.sublime-theme"):
        name = r.rsplit("/", 1)[-1]
        if name in seen:
            continue
        seen.add(name)
        out.append((name, name))
    out.sort(key=lambda x: x[0].lower())
    return out


def list_color_schemes():
    seen, out = set(), []
    for r in sublime.find_resources("*.sublime-color-scheme"):
        name = r.rsplit("/", 1)[-1]
        if name in seen:
            continue
        seen.add(name)
        out.append((name, name))
    for r in sublime.find_resources("*.tmTheme"):
        out.append((r.rsplit("/", 1)[-1], r))
    out.sort(key=lambda x: x[0].lower())
    return out


def open_resource_picker(key):
    en = KEY_INDEX[key]
    window = sublime.active_window()
    items = list_themes() if en["kind"] == "theme" else list_color_schemes()
    if not items:
        sublime.status_message("No %s resources found" % en["kind"])
        return
    labels = [lab for lab, _v in items]
    cur_val = cur(key, en["default"])
    selected = next((i for i, (_l, v) in enumerate(items) if v == cur_val), -1)

    def on_done(idx):
        if idx == -1:
            return
        set_pref(key, items[idx][1])
        render_content()

    window.show_quick_panel(labels, on_done, 0, selected, None)


def _run_cmd(args, timeout=20):
    try:
        import subprocess
        p = subprocess.run(args, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
        return p.stdout.decode("utf-8", "replace")
    except Exception:
        return None


def _scan_font_files():
    files = set()
    plat = sys.platform
    if plat.startswith("win"):
        d = os.path.join(os.environ.get("WINDIR", "C:\\\\Windows"), "Fonts")
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
    names = set()
    for f in files:
        if f.lower().endswith(exts):
            names.add(os.path.splitext(f)[0].replace("_", " ").strip())
    return names


_font_cache = None

def list_system_fonts():
    global _font_cache
    if _font_cache is not None:
        return _font_cache

    fams = set()
    out = _run_cmd(["fc-list", ":", "family"])
    if out:
        for line in out.splitlines():
            for fam in line.split(","):
                fam = fam.strip()
                if fam:
                    fams.add(fam)

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


PROVIDERS = {"fonts": list_system_fonts}

def open_list_picker(key):
    en = KEY_INDEX[key]
    provider = PROVIDERS.get(en.get("provider"))
    if provider is None:
        return
    sublime.status_message("Loading %s\u2026" % en.get("provider"))

    def work():
        items = provider()
        sublime.set_timeout(lambda: _show_list_picker(key, items), 0)

    threading.Thread(target=work, daemon=True).start()


def _show_list_picker(key, items):
    if not items:
        sublime.status_message("No options found")
        return
    en = KEY_INDEX[key]
    labels = [lab for lab, _v in items]
    cur_val = cur(key, en["default"])
    selected = next((i for i, (_l, v) in enumerate(items) if v == cur_val), -1)

    def on_done(idx):
        if idx == -1:
            return
        set_pref(key, items[idx][1])
        render_content()

    sublime.active_window().show_quick_panel(labels, on_done, 0, selected, None)


def on_nav(href):
    global _filter, _category
    if href == "action:reset_all":
        reset_all()
        render_content()
        return
    elif href == "action:search":
        open_search()
        return
    elif href == "action:clear_search":
        _filter = ""
        render_content()
        render_nav()
        return
    cmd, _sep, rest = href.partition(":")
    if cmd == "cat":
        was_filter = bool(_filter)
        _category = int(rest)
        _filter = ""
        render_nav()
        if was_filter:
            render_content()
        sublime.set_timeout(lambda: scroll_to_category(_category), 10)
        return
    elif cmd == "cmd":
        sublime.active_window().run_command(rest)
    elif cmd == "respick":
        open_resource_picker(rest)
        return
    elif cmd == "listpick":
        open_list_picker(rest)
        return
    elif cmd == "toggle":
        toggle_pref(rest, KEY_INDEX[rest]["default"])
    elif cmd == "edit":
        open_edit(rest)
        return
    elif cmd == "reset":
        erase_pref(rest)
    elif cmd == "enum":
        key, idx = rest.split(":")
        set_pref(key, norm_choices(KEY_INDEX[key])[int(idx)][0])
    elif cmd == "num":
        key, raw = rest.split(":")
        en = KEY_INDEX[key]
        set_pref(key, float(raw) if en.get("is_float") else int(raw))
    elif cmd == "step":
        key, delta = rest.split(":")
        en = KEY_INDEX[key]
        try:
            base = float(cur(key, en["default"]))
        except (TypeError, ValueError):
            base = float(en["default"])
        new = base + float(delta) * en.get("step", 1)
        new = round(new, 4) if en.get("is_float") else int(new)
        set_pref(key, new)
    render_content()


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

class SettingsUiOpenCommand(sublime_plugin.WindowCommand):
    def run(self):
        # Open in a dedicated 2-pane window
        sublime.run_command("new_window")
        win = sublime.active_window()
        win.set_layout({
            "cols": [0.0, 0.28, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
        })
        win.set_tabs_visible(False)
        win.set_status_bar_visible(False)
        win.set_sidebar_visible(False)
        win.set_minimap_visible(False)
        render()


class SettingsUiSyncListener(sublime_plugin.EventListener):
    def on_activated(self, view):
        if view.settings().get(CONTENT_MARK) or view.settings().get(NAV_MARK):
            _start_poll()

def plugin_loaded():
    pass
"""

with open(target, "w") as f:
    f.write(head + tail)
print("Updated successfully")
