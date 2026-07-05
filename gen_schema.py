"""
ST command: settings_ui_generate_schema

Usage (command palette): "Settings UI: Generate Schema"
Usage (console):         window.run_command("settings_ui_generate_schema")

Reads Default/Preferences.sublime-settings, merges with existing schema.KEY_INDEX,
and rewrites the SECTIONS block in schema.py. ST auto-reloads the plugin on save.

The installed package may be a read-only .sublime-package zip, so all package
files are read through the resource API (sublime.load_resource) and the
regenerated schema.py is written under sublime.packages_path(). For a zipped
install that loose file acts as a standard package override and shadows the
zipped copy.
"""
import os
import sublime
import sublime_plugin
from .lib import schema as _schema
from .lib import schema_gen

_PKG = __package__.split(".")[0]


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
        try:
            section_map = sublime.decode_value(
                sublime.load_resource("Packages/%s/tools/section_map.json" % _PKG)
            )
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
            # Resolves to the loose override if one exists, else the zipped copy.
            source = sublime.load_resource("Packages/%s/lib/schema.py" % _PKG)
        except Exception as ex:
            sublime.error_message("Settings UI: Cannot read schema.py\n%s" % ex)
            return

        try:
            new_source = schema_gen.replace_sections_block(source, new_sections_code)
        except ValueError as ex:
            sublime.error_message("Settings UI: %s" % ex)
            return

        schema_path = os.path.join(sublime.packages_path(), _PKG, "lib", "schema.py")
        try:
            os.makedirs(os.path.dirname(schema_path), exist_ok=True)
            with open(schema_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_source)
        except Exception as ex:
            sublime.error_message("Settings UI: Failed to write schema.py\n%s" % ex)
            return

        total_keys = sum(len(v) for v in sections.values())
        sublime.status_message(
            "Settings UI: schema.py regenerated — %d keys across %d sections"
            % (total_keys, len(sections))
        )
