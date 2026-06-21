"""
HTML renderers for the Settings UI panel.

This module is intentionally stateless: every function that needs the current
filter or category index receives them as parameters.  That keeps this module
free of imports from `panel` or `state`, preventing circular dependencies.

Public API
----------
CSS                  – the full minihtml stylesheet
RENDERERS            – {type_name: render_fn} dispatch table
matches(en, flt)     – True if entry matches the filter string
build_nav_html(...)  – HTML string for the navigation sidebar
build_content_phantoms(...)  – list of sublime.Phantom for the content pane
"""

import json
import sublime
from . import schema, prefs

# ---------------------------------------------------------------------------
# Stylesheet
# All colors derive from the active color scheme, so the panel always matches.
# ---------------------------------------------------------------------------

CSS = """
    body { background-color: var(--background); }

    .shell { background-color: var(--background); padding: 20px 24px 50px 24px; }
    .nav { display: inline-block; width: 196px; vertical-align: top; }
    .navhead { display: block; color: color(var(--foreground) alpha(0.45));
               font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
               margin: 4px 0 12px 8px; }
    .navitem { display: block; text-decoration: none; font-size: 12px;
               color: color(var(--foreground) alpha(0.72)); padding: 6px 10px;
               border-radius: 5px; margin-bottom: 1px; }
    .navitem.active { background-color: color(var(--bluish) alpha(0.20));
                      color: var(--foreground); }
    .navreset { display: block; text-decoration: none; color: var(--bluish);
                font-size: 12px; padding: 6px 10px; margin-top: 16px;
                border-top: 1px solid color(var(--foreground) alpha(0.12)); }

    .content { display: inline-block; width: 700px; vertical-align: top;
               margin-left: 26px; }
    .h1 { display: block; color: var(--foreground); font-size: 24px; margin-bottom: 12px; }
    .search { display: block; background-color: color(var(--foreground) alpha(0.06));
              border: 1px solid color(var(--foreground) alpha(0.15)); border-radius: 5px;
              padding: 7px 12px; color: color(var(--foreground) alpha(0.55));
              font-size: 13px; text-decoration: none; margin-bottom: 6px; }
    .search.active { color: var(--foreground); border-color: var(--bluish); }
    .subnote { display: block; color: color(var(--foreground) alpha(0.5));
               font-size: 12px; margin-bottom: 4px; }
    .subnote a { color: var(--bluish); text-decoration: none; }

    .section { display: block; color: color(var(--foreground) alpha(0.55));
               font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
               margin: 22px 0 2px 0; }
    .item { display: block; text-decoration: none; border-left: 2px solid transparent;
            padding: 11px 0 11px 14px; }
    .item.modified { border-left: 2px solid var(--bluish); }
    .title { display: block; color: var(--foreground); font-size: 14px;
             font-weight: 600; margin-bottom: 3px; }
    .desc { display: block; color: color(var(--foreground) alpha(0.55));
            font-size: 12px; line-height: 17px; }
    .desc.indent { padding-left: 25px; margin-top: 6px; }
    .empty { display: block; color: color(var(--foreground) alpha(0.55));
             font-size: 13px; padding: 22px 0; }

    .cb { display: inline-block; width: 16px; height: 16px; border-radius: 3px;
          vertical-align: middle; margin-right: 9px; text-align: center; }
    .cb.on  { background-color: var(--bluish); border: 1px solid var(--bluish); }
    .cb.off { background-color: color(var(--foreground) alpha(0.05));
              border: 1px solid color(var(--foreground) alpha(0.4)); }
    .ck { color: var(--background); font-size: 11px; font-weight: 700; line-height: 16px; }
    .cbtitle { display: inline-block; vertical-align: middle; color: var(--foreground);
               font-size: 14px; font-weight: 600; }

    .controls { display: block; margin-top: 8px; }
    .radios { margin-top: 6px; }
    .radio { display: block; text-decoration: none; padding: 5px 0; }
    .rdot { display: inline-block; width: 16px; height: 16px; border-radius: 8px;
            border: 2px solid color(var(--foreground) alpha(0.35));
            vertical-align: middle; margin-right: 10px; text-align: center;
            line-height: 16px; }
    .rdot.on { border-color: var(--bluish); }
    .rin { display: inline-block; width: 8px; height: 8px; border-radius: 4px;
           background-color: var(--bluish); vertical-align: middle; }
    .rlabel { display: inline-block; vertical-align: middle; color: var(--foreground);
              font-size: 13px; }
    .nstep { display: inline-block; height: 30px; line-height: 30px; padding: 0 13px;
             text-align: center; background-color: color(var(--foreground) alpha(0.07));
             border: 1px solid color(var(--foreground) alpha(0.15)); border-radius: 5px;
             color: var(--foreground); text-decoration: none; font-size: 13px;
             font-weight: 600; margin-right: 6px; vertical-align: middle; }
    .ninput { display: inline-block; height: 30px; line-height: 30px; padding: 0 16px;
              text-align: center; background-color: color(var(--foreground) alpha(0.04));
              border: 1px solid color(var(--foreground) alpha(0.22)); border-radius: 5px;
              color: var(--yellowish); text-decoration: none; font-size: 13px;
              margin-right: 6px; vertical-align: middle; }
    .val { display: inline-block; background-color: color(var(--foreground) alpha(0.05));
           border: 1px solid color(var(--foreground) alpha(0.15)); border-radius: 4px;
           padding: 4px 9px; color: var(--yellowish); font-size: 12px;
           margin-right: 8px; vertical-align: middle; }
    .editlink, .selectlink { color: var(--bluish); text-decoration: none;
                             font-size: 12px; vertical-align: middle; }
    .resetlink { color: color(var(--foreground) alpha(0.5)); text-decoration: none;
                 font-size: 12px; vertical-align: middle; }
    .footer { display: block; color: color(var(--foreground) alpha(0.4)); font-size: 12px;
              margin-top: 26px; border-top: 1px solid color(var(--foreground) alpha(0.12));
              padding-top: 12px; }
"""

# ---------------------------------------------------------------------------
# Per-type renderers  (return HTML fragment strings)
# ---------------------------------------------------------------------------

def _reset_link(key: str) -> str:
    return '&#160;&#160;<a class="resetlink" href="reset:{k}">Reset</a>'.format(k=key)


def r_bool(en: dict) -> str:
    key, default = en["key"], en["default"]
    val = bool(prefs.cur(key, default))
    cb = ('<div class="cb on"><span class="ck">&#10003;</span></div>'
          if val else '<div class="cb off"></div>')
    return (
        '<a class="item{m}" href="toggle:{k}">'
        '{cb}<span class="cbtitle">{t}</span>'
        '<span class="desc indent">{d}</span></a>'
    ).format(
        m=" modified" if val != default else "", k=key, cb=cb,
        t=schema.esc(en["title"]), d=schema.esc(en["desc"]),
    )


def r_enum(en: dict) -> str:
    key = en["key"]
    val = prefs.cur(key, en["default"])
    rows = ""
    for i, (cv, lab) in enumerate(schema.norm_choices(en)):
        dot = (
            '<span class="rdot on"><span class="rin"></span></span>'
            if cv == val else '<span class="rdot"></span>'
        )
        rows += (
            '<a class="radio" href="enum:{k}:{i}">'
            '{dot}<span class="rlabel">{l}</span></a>'
        ).format(k=key, i=i, dot=dot, l=schema.esc(lab))
    return (
        '<div class="item{m}"><span class="title">{t}</span>'
        '<span class="desc">{d}</span>'
        '<div class="controls radios">{r}</div></div>'
    ).format(
        m=" modified" if prefs.is_modified(en) else "",
        t=schema.esc(en["title"]), d=schema.esc(en["desc"]), r=rows,
    )


def r_number(en: dict) -> str:
    key = en["key"]
    val = prefs.cur(key, en["default"])
    mod = prefs.is_modified(en)
    step = en.get("step", 1)
    dec, inc = ("&#8722;1", "+1") if step == 1 else ("&#8722;", "+")
    reset = _reset_link(key) if mod else ""
    return (
        '<div class="item{m}"><span class="title">{t}</span>'
        '<span class="desc">{d}</span><div class="controls">'
        '<a class="nstep" href="step:{k}:-1">{dec}</a>'
        '<a class="ninput" href="edit:{k}">{v}</a>'
        '<a class="nstep" href="step:{k}:1">{inc}</a>'
        '{r}</div></div>'
    ).format(
        m=" modified" if mod else "",
        t=schema.esc(en["title"]), d=schema.esc(en["desc"]),
        k=key, v=schema.esc(val), dec=dec, inc=inc, r=reset,
    )


def r_string(en: dict) -> str:
    key = en["key"]
    val = prefs.cur(key, en["default"])
    mod = prefs.is_modified(en)
    disp = schema.esc(schema.short(val if val != "" else '""', 56))
    reset = _reset_link(key) if mod else ""
    return (
        '<div class="item{m}"><span class="title">{t}</span>'
        '<span class="desc">{d}</span><div class="controls">'
        '<span class="val">{v}</span>'
        '<a class="editlink" href="edit:{k}">Edit&#8230;</a>'
        '{r}</div></div>'
    ).format(
        m=" modified" if mod else "",
        t=schema.esc(en["title"]), d=schema.esc(en["desc"]),
        v=disp, k=key, r=reset,
    )


def r_json(en: dict) -> str:
    key = en["key"]
    val = prefs.cur(key, en["default"])
    mod = prefs.is_modified(en)
    disp = schema.esc(schema.short(json.dumps(val), 60))
    reset = _reset_link(key) if mod else ""
    return (
        '<div class="item{m}"><span class="title">{t}</span>'
        '<span class="desc">{d}</span><div class="controls">'
        '<span class="val">{v}</span>'
        '<a class="editlink" href="edit:{k}">Edit&#8230;</a>'
        '{r}</div></div>'
    ).format(
        m=" modified" if mod else "",
        t=schema.esc(en["title"]), d=schema.esc(en["desc"]),
        v=disp, k=key, r=reset,
    )


def r_picker(en: dict) -> str:
    key = en["key"]
    val = prefs.cur(key, en["default"])
    mod = prefs.is_modified(en)
    reset = _reset_link(key) if mod else ""
    return (
        '<div class="item{m}"><span class="title">{t}</span>'
        '<span class="desc">{d}</span><div class="controls">'
        '<span class="val">{v}</span>'
        '<a class="selectlink" href="cmd:{c}">Select&#8230;</a>'
        '{r}</div></div>'
    ).format(
        m=" modified" if mod else "",
        t=schema.esc(en["title"]), d=schema.esc(en["desc"]),
        v=schema.esc(schema.short(val, 56)), c=en["cmd"], r=reset,
    )


def r_respick(en: dict) -> str:
    key = en["key"]
    val = prefs.cur(key, en["default"])
    mod = prefs.is_modified(en)
    reset = _reset_link(key) if mod else ""
    return (
        '<div class="item{m}"><span class="title">{t}</span>'
        '<span class="desc">{d}</span><div class="controls">'
        '<span class="val">{v}</span>'
        '<a class="selectlink" href="respick:{k}">Select&#8230;</a>'
        '{r}</div></div>'
    ).format(
        m=" modified" if mod else "",
        t=schema.esc(en["title"]), d=schema.esc(en["desc"]),
        v=schema.esc(schema.short(val, 56)), k=key, r=reset,
    )


def r_listpick(en: dict) -> str:
    key = en["key"]
    val = prefs.cur(key, en["default"])
    mod = prefs.is_modified(en)
    disp = schema.esc(schema.short(val if val != "" else "(default)", 44))
    reset = _reset_link(key) if mod else ""
    return (
        '<div class="item{m}"><span class="title">{t}</span>'
        '<span class="desc">{d}</span><div class="controls">'
        '<span class="val">{v}</span>'
        '<a class="selectlink" href="listpick:{k}">Select&#8230;</a>'
        '&#160;&#160;<a class="editlink" href="edit:{k}">Edit&#8230;</a>'
        '{r}</div></div>'
    ).format(
        m=" modified" if mod else "",
        t=schema.esc(en["title"]), d=schema.esc(en["desc"]),
        v=disp, k=key, r=reset,
    )


# Dispatch table: entry type → render function
RENDERERS: dict = {
    "bool":     r_bool,
    "enum":     r_enum,
    "number":   r_number,
    "string":   r_string,
    "json":     r_json,
    "picker":   r_picker,
    "respick":  r_respick,
    "listpick": r_listpick,
}

# ---------------------------------------------------------------------------
# Filter helper
# ---------------------------------------------------------------------------

def matches(en: dict, filter_text: str) -> bool:
    """Return True if *en* matches the active search *filter_text*."""
    if not filter_text:
        return True
    return (
        filter_text in en["key"].lower()
        or filter_text in en["title"].lower()
        or filter_text in en["desc"].lower()
    )


# ---------------------------------------------------------------------------
# HTML / Phantom builders
# ---------------------------------------------------------------------------

def _wrap(inner: str, extra_style: str = "") -> str:
    """Wrap *inner* in the standard body+style shell."""
    style_attr = ' style="%s"' % extra_style if extra_style else ""
    return (
        '<body id="settings-ui"><style>' + CSS + '</style>'
        '<div class="shell"%s>' % style_attr + inner + '</div></body>'
    )


def build_nav_html(sections: list, filter_text: str, category_index: int) -> str:
    """Build the full HTML string for the navigation sidebar."""
    parts = ['<div class="nav"><span class="navhead">SETTINGS</span>']
    for i, (title, _entries) in enumerate(sections):
        active = not filter_text and i == category_index
        parts.append(
            '<a class="navitem{a}" href="cat:{i}">{t}</a>'.format(
                a=" active" if active else "", i=i, t=schema.esc(title)
            )
        )
    parts.append(
        '<a class="navreset" href="action:reset_all">Restore all defaults</a>'
    )
    parts.append('</div>')
    return _wrap("".join(parts), "padding-bottom: 2000px;")


def build_content_phantoms(
    view: sublime.View,
    sections: list,
    filter_text: str,
    on_nav_callback,
) -> list:
    """
    Build the list of sublime.Phantom objects for the content pane.

    Phantoms are spread across consecutive lines of *view* so each section
    scrolls independently and the nav highlight can track the scroll position.
    Each phantom includes the full CSS to avoid style bleed between phantoms.
    """
    phantoms = []

    # -- Header / search bar (line 0) ------------------------------------
    header = ['<div class="content"><span class="h1">Settings</span>']
    if filter_text:
        header.append(
            '<a class="search active" href="action:search">Search: {f}</a>'
            '<span class="subnote">'
            '<a href="action:clear_search">Clear search</a> '
            '&#160;&#183;&#160; '
            '<a href="action:reset_all">Restore all defaults</a>'
            '</span>'.format(f=schema.esc(filter_text))
        )
    else:
        header.append(
            '<a class="search" href="action:search">Search settings&#8230;</a>'
            '<span class="subnote">Changes apply immediately. '
            '&#160;&#183;&#160; '
            '<a href="action:reset_all">Restore all defaults</a>'
            '</span>'
        )
    header.append('</div>')
    phantoms.append(sublime.Phantom(
        sublime.Region(0, 0),
        _wrap("".join(header), "padding-bottom: 0;"),
        sublime.LAYOUT_BLOCK,
        on_navigate=on_nav_callback,
    ))

    # -- One phantom per section (lines 1 … N) ---------------------------
    line_idx = 1
    total_shown = 0
    for _title, entries in sections:
        visible = [en for en in entries if matches(en, filter_text)]
        if filter_text and not visible:
            continue

        section_title = _title
        parts = ['<div class="content" style="margin-top:0;">']
        parts.append(
            '<span class="section">{s}</span>'.format(s=schema.esc(section_title))
        )
        for en in visible:
            parts.append(RENDERERS[en["type"]](en))
            total_shown += 1
        parts.append('</div>')

        pt = view.text_point(line_idx, 0)
        phantoms.append(sublime.Phantom(
            sublime.Region(pt, pt),
            _wrap("".join(parts), "padding-top: 0; padding-bottom: 0;"),
            sublime.LAYOUT_BLOCK,
            on_navigate=on_nav_callback,
        ))
        line_idx += 1

    # -- Empty-state message when nothing matches ------------------------
    if filter_text and total_shown == 0:
        msg = '<span class="empty">No settings match \u201c{f}\u201d.</span>'.format(
            f=schema.esc(filter_text)
        )
        pt = view.text_point(line_idx, 0)
        phantoms.append(sublime.Phantom(
            sublime.Region(pt, pt),
            _wrap(msg, "padding-top: 0;"),
            sublime.LAYOUT_BLOCK,
            on_navigate=on_nav_callback,
        ))

    # -- Footer spacer (ensures the last section can scroll to top) ------
    footer = '<div style="height: 80vh;"></div>'
    pt = view.text_point(line_idx + (1 if filter_text and total_shown == 0 else 0), 0)
    phantoms.append(sublime.Phantom(
        sublime.Region(pt, pt),
        _wrap(footer, "padding-top: 0;"),
        sublime.LAYOUT_BLOCK,
        on_navigate=on_nav_callback,
    ))

    return phantoms
