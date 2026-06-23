"""
ST command: settings_ui_generate_schema

Usage (command palette): "Settings UI: Generate Schema"
Usage (console):         window.run_command("settings_ui_generate_schema")

Reads Default/Preferences.sublime-settings, merges with existing schema.KEY_INDEX,
and rewrites the SECTIONS block in schema.py. ST auto-reloads the plugin on save.
"""
import os
import json
import sublime
import sublime_plugin
from . import schema as _schema
from . import schema_gen

_TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.py")


def _load_prefs_data() -> list:
    """Return [(key, default, desc), ...] from Default/Preferences.sublime-settings."""
    plat = {"osx": "OSX", "windows": "Windows", "linux": "Linux"}.get(
        sublime.platform(), ""
    )
    paths = ["Packages/Default/Preferences.sublime-settings"]
    if plat:
        paths.append("Packages/Default/Preferences (%s).sublime-settings" % plat)

    merged_values = {}
    merged_descs = {}
    key_order = []

    for path in paths:
        try:
            text = sublime.load_resource(path)
        except Exception:
            continue
        try:
            values = sublime.decode_value(schema_gen.strip_jsonc_comments(text))
        except Exception:
            try:
                values = sublime.decode_value(text)
            except Exception:
                continue
        descs = schema_gen.parse_descriptions(text)
        for key, val in values.items():
            if key not in merged_values:
                key_order.append(key)
            merged_values[key] = val
            merged_descs.setdefault(key, descs.get(key, ""))

    return [(k, merged_values[k], merged_descs[k]) for k in key_order]


class SettingsUiGenerateSchemaCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        section_map_path = os.path.join(_TOOLS_DIR, "section_map.json")
        try:
            with open(section_map_path, encoding="utf-8") as f:
                section_map = json.load(f)
        except Exception as ex:
            sublime.error_message("Settings UI: Cannot load section_map.json\n%s" % ex)
            return

        prefs_data = _load_prefs_data()
        if not prefs_data:
            sublime.error_message(
                "Settings UI: Failed to load Default/Preferences.sublime-settings"
            )
            return

        sections = schema_gen.build_sections(prefs_data, _schema.SECTIONS, section_map)
        new_sections_code = schema_gen.sections_to_code(sections)

        try:
            with open(_SCHEMA_PATH, encoding="utf-8") as f:
                source = f.read()
        except Exception as ex:
            sublime.error_message("Settings UI: Cannot read schema.py\n%s" % ex)
            return

        try:
            new_source = schema_gen.replace_sections_block(source, new_sections_code)
        except ValueError as ex:
            sublime.error_message("Settings UI: %s" % ex)
            return

        with open(_SCHEMA_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_source)

        total_keys = sum(len(v) for v in sections.values())
        sublime.status_message(
            "Settings UI: schema.py regenerated — %d keys across %d sections"
            % (total_keys, len(sections))
        )
