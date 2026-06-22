"""
Pure schema generation logic. No Sublime Text imports — fully testable outside ST.
"""
import re

_KEY_LINE = re.compile(r'^"([^"\\]+)"\s*:')


def strip_jsonc_comments(text: str) -> str:
    """Remove // line comments, preserving :// in URLs.

    Heuristic: protects '://' patterns but will incorrectly strip '//'
    inside string values (e.g. {"note": "see // this"}). Safe for
    Sublime Text's Default/Preferences.sublime-settings which contains
    no double-slash inside string values.
    """
    lines = []
    for line in text.splitlines():
        lines.append(re.sub(r'(?<!:)//.*$', '', line))
    return '\n'.join(lines)


def parse_descriptions(text: str) -> dict:
    """Return {key: description} extracted from // comments above each JSON key."""
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


_ENUM_RE = re.compile(r'"([^"]{1,40})"')

_EXACT_MAP = {
    "color_scheme":       {"type": "picker",   "cmd": "select_color_scheme"},
    "light_color_scheme": {"type": "respick",  "kind": "color_scheme"},
    "dark_color_scheme":  {"type": "respick",  "kind": "color_scheme"},
    "theme":              {"type": "picker",   "cmd": "select_theme"},
    "light_theme":        {"type": "respick",  "kind": "theme"},
    "dark_theme":         {"type": "respick",  "kind": "theme"},
    "font_face":          {"type": "listpick", "provider": "fonts"},
}


def infer_entry(key: str, default, desc: str) -> dict:
    """Return a schema entry dict for (key, default, desc).

    Priority:
    1. Exact key-name match (_EXACT_MAP) -> rich widget type
    2. Enum detection from quoted tokens in desc (2-6 tokens)
    3. Value-type fallback (bool/int/float/str -> specific type, else json)
    """
    title = key.replace("_", " ").title()
    base = {"key": key, "title": title, "desc": desc, "default": default}

    if key in _EXACT_MAP:
        return dict(base, **_EXACT_MAP[key])

    quoted = list(dict.fromkeys(_ENUM_RE.findall(desc)))
    if 2 <= len(quoted) <= 6:
        df = default if default in quoted else quoted[0]
        return dict(base, type="enum", default=df, choices=quoted)

    if isinstance(default, bool):
        return dict(base, type="bool")
    if isinstance(default, int):
        return dict(base, type="number", presets=None, step=1, is_float=False)
    if isinstance(default, float):
        return dict(base, type="number", presets=None, step=0.5, is_float=True)
    if isinstance(default, str):
        return dict(base, type="string", presets=None)
    return dict(base, type="json")


_PREFIX_RULES = [
    ("auto_complete_",     "EDITOR › COMPLETION"),
    ("line_padding_",      "EDITOR › CARET & LINE"),
    ("control_character_", "EDITOR › WHITE SPACE"),
    ("ensure_newline_",    "FILES › SAVE"),
    ("auto_hide_",         "UI › AUTO HIDE"),
    ("hide_pointer_",      "UI › AUTO HIDE"),
    ("auto_indent",        "EDITOR › INDENTATION"),
    ("smart_indent",       "EDITOR › INDENTATION"),
    ("indent_",            "EDITOR › INDENTATION"),
    ("shift_tab_",         "EDITOR › INDENTATION"),
    ("translate_",         "EDITOR › INDENTATION"),
    ("detect_",            "EDITOR › INDENTATION"),
    ("tab_size",           "EDITOR › INDENTATION"),
    ("find_",              "EDITOR › FIND"),
    ("font_",              "APPEARANCE › FONT"),
    ("scroll_",            "EDITOR › SCROLLING"),
    ("match_",             "EDITOR › BRACKETS & TAGS"),
    ("caret_",             "EDITOR › CARET & LINE"),
    ("ruler_",             "EDITOR › RULERS"),
    ("index_",             "FILES › INDEXING & SIDEBAR"),
    ("goto_",              "FILES › INDEXING & SIDEBAR"),
    ("folder_",            "FILES › INDEXING & SIDEBAR"),
    ("file_",              "FILES › INDEXING & SIDEBAR"),
    ("binary_",            "FILES › INDEXING & SIDEBAR"),
    ("image_",             "FILES › INDEXING & SIDEBAR"),
    ("trim_",              "FILES › SAVE"),
    ("save_",              "FILES › SAVE"),
    ("vintage_",           "PACKAGES › VINTAGE"),
    ("word_",              "EDITOR › WORD WRAP"),
    ("wrap_",              "EDITOR › WORD WRAP"),
    ("draw_",              "EDITOR › WHITE SPACE"),
    ("spell_check",        "EDITOR › SPELL CHECK"),
    ("spelling_",          "EDITOR › SPELL CHECK"),
    ("dictionary",         "EDITOR › SPELL CHECK"),
    ("reveal_",            "UI › AUTO HIDE"),
    ("show_",              "STATUS BAR"),
]


def assign_section(key: str, section_map: dict, prefix_rules: list) -> str:
    """Return the section title for key.

    Priority: section_map exact match > prefix_rules (first match wins) > 'OTHER'.
    """
    if key in section_map:
        return section_map[key]
    for prefix, section in prefix_rules:
        if key == prefix or key.startswith(prefix):
            return section
    return "OTHER"
