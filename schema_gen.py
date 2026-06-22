"""
Pure schema generation logic. No Sublime Text imports — fully testable outside ST.
"""
import re
import json

_KEY_LINE = re.compile(r'^"([^"\\]+)"\s*:')


def strip_jsonc_comments(text: str) -> str:
    """Remove // line comments, preserving :// in URLs."""
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
