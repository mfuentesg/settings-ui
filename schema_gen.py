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
