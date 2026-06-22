import json
import pytest
import schema_gen


class TestStripJsoncComments:
    def test_removes_line_comment(self):
        text = '{"key": "value" // comment\n}'
        assert json.loads(schema_gen.strip_jsonc_comments(text)) == {"key": "value"}

    def test_removes_full_line_comment(self):
        text = '{\n// full line comment\n"key": true\n}'
        assert json.loads(schema_gen.strip_jsonc_comments(text)) == {"key": True}

    def test_preserves_url_double_slash(self):
        text = '{"url": "http://example.com"}'
        assert json.loads(schema_gen.strip_jsonc_comments(text)) == {"url": "http://example.com"}

    def test_empty_string(self):
        assert schema_gen.strip_jsonc_comments("") == ""

    def test_strips_double_slash_in_string_value(self):
        # Known limitation: // inside strings is treated as a comment.
        # This is acceptable for ST prefs files which don't embed // in values.
        text = '{"note": "see foo // bar"}'
        result = schema_gen.strip_jsonc_comments(text)
        assert "// bar" not in result


class TestParseDescriptions:
    def test_extracts_single_comment(self):
        text = '// The font size.\n"font_size": 10\n'
        result = schema_gen.parse_descriptions(text)
        assert result["font_size"] == "The font size."

    def test_joins_multiline_comment(self):
        text = '// Line one.\n// Line two.\n"key": ""\n'
        result = schema_gen.parse_descriptions(text)
        assert result["key"] == "Line one. Line two."

    def test_blank_line_clears_buffer(self):
        text = '// Old comment.\n\n"key": ""\n'
        result = schema_gen.parse_descriptions(text)
        assert "key" not in result

    def test_no_comment_no_entry(self):
        text = '"key": true\n'
        result = schema_gen.parse_descriptions(text)
        assert "key" not in result

    def test_does_not_overwrite_first_description(self):
        text = '// First.\n"key": ""\n// Second.\n"key": ""\n'
        result = schema_gen.parse_descriptions(text)
        assert result["key"] == "First."


class TestInferEntry:
    def test_bool_default(self):
        e = schema_gen.infer_entry("auto_indent", True, "")
        assert e == {"key": "auto_indent", "title": "Auto Indent",
                     "desc": "", "type": "bool", "default": True}

    def test_int_default(self):
        e = schema_gen.infer_entry("tab_size", 4, "")
        assert e["type"] == "number"
        assert e["step"] == 1
        assert e["is_float"] is False

    def test_float_default(self):
        e = schema_gen.infer_entry("scroll_speed", 1.0, "")
        assert e["type"] == "number"
        assert e["is_float"] is True
        assert e["step"] == 0.5

    def test_str_default(self):
        e = schema_gen.infer_entry("dictionary", "en_US.dic", "")
        assert e["type"] == "string"
        assert e["default"] == "en_US.dic"

    def test_list_default(self):
        e = schema_gen.infer_entry("rulers", [], "")
        assert e["type"] == "json"

    def test_none_default(self):
        e = schema_gen.infer_entry("some_key", None, "")
        assert e["type"] == "json"

    def test_enum_from_comment(self):
        desc = 'Valid values are "word", "line", "character"'
        e = schema_gen.infer_entry("word_wrap", "word", desc)
        assert e["type"] == "enum"
        assert e["choices"] == ["word", "line", "character"]
        assert e["default"] == "word"

    def test_enum_default_not_in_choices_uses_first(self):
        desc = 'Options: "a", "b", "c"'
        e = schema_gen.infer_entry("key", "z", desc)
        assert e["default"] == "a"

    def test_enum_requires_at_least_two_choices(self):
        desc = 'Only "one" option'
        e = schema_gen.infer_entry("key", "one", desc)
        assert e["type"] == "string"

    def test_enum_ignores_more_than_six(self):
        desc = '"a", "b", "c", "d", "e", "f", "g"'
        e = schema_gen.infer_entry("key", "a", desc)
        assert e["type"] == "string"

    def test_exact_color_scheme(self):
        e = schema_gen.infer_entry("color_scheme", "Mariana", "")
        assert e["type"] == "picker"
        assert e["cmd"] == "select_color_scheme"

    def test_exact_light_color_scheme(self):
        e = schema_gen.infer_entry("light_color_scheme", "", "")
        assert e["type"] == "respick"
        assert e["kind"] == "color_scheme"

    def test_exact_theme(self):
        e = schema_gen.infer_entry("theme", "auto", "")
        assert e["type"] == "picker"
        assert e["cmd"] == "select_theme"

    def test_exact_dark_theme(self):
        e = schema_gen.infer_entry("dark_theme", "", "")
        assert e["type"] == "respick"
        assert e["kind"] == "theme"

    def test_exact_font_face(self):
        e = schema_gen.infer_entry("font_face", "", "")
        assert e["type"] == "listpick"
        assert e["provider"] == "fonts"

    def test_title_derived_from_key(self):
        e = schema_gen.infer_entry("some_setting_key", True, "")
        assert e["title"] == "Some Setting Key"


class TestAssignSection:
    def test_section_map_overrides_prefix(self):
        assert schema_gen.assign_section("file_tab_style",
                                         {"file_tab_style": "APPEARANCE › THEME"},
                                         schema_gen._PREFIX_RULES) == "APPEARANCE › THEME"

    def test_prefix_auto_complete(self):
        assert schema_gen.assign_section("auto_complete_delay", {},
                                         schema_gen._PREFIX_RULES) == "EDITOR › COMPLETION"

    def test_prefix_find(self):
        assert schema_gen.assign_section("find_selected_text", {},
                                         schema_gen._PREFIX_RULES) == "EDITOR › FIND"

    def test_prefix_show_falls_back_to_status_bar(self):
        assert schema_gen.assign_section("show_encoding", {},
                                         schema_gen._PREFIX_RULES) == "STATUS BAR"

    def test_unmapped_goes_to_other(self):
        assert schema_gen.assign_section("unknown_setting", {},
                                         schema_gen._PREFIX_RULES) == "OTHER"

    def test_prefix_vintage(self):
        assert schema_gen.assign_section("vintage_start_in_command_mode", {},
                                         schema_gen._PREFIX_RULES) == "PACKAGES › VINTAGE"

    def test_prefix_font(self):
        assert schema_gen.assign_section("font_size", {},
                                         schema_gen._PREFIX_RULES) == "APPEARANCE › FONT"

    def test_prefix_index(self):
        assert schema_gen.assign_section("index_files", {},
                                         schema_gen._PREFIX_RULES) == "FILES › INDEXING & SIDEBAR"


class TestBuildSections:
    def _existing(self):
        return [
            ("APPEARANCE › FONT", [
                {"key": "font_size", "title": "Font Size", "desc": "Curated.",
                 "type": "number", "default": 10, "presets": [10, 12], "step": 1, "is_float": False},
            ]),
        ]

    def test_existing_entry_preserved(self):
        prefs = [("font_size", 12, "From prefs.")]
        result = schema_gen.build_sections(prefs, self._existing(), {})
        assert result["APPEARANCE › FONT"][0]["desc"] == "Curated."

    def test_existing_entry_in_existing_section(self):
        prefs = [("font_size", 12, "")]
        result = schema_gen.build_sections(prefs, self._existing(), {})
        assert "APPEARANCE › FONT" in result

    def test_new_key_inferred_and_assigned(self):
        prefs = [("font_size", 12, ""), ("brand_new_key", True, "A new bool.")]
        result = schema_gen.build_sections(prefs, self._existing(), {})
        new_key_sections = [s for s, entries in result.items()
                            if any(e["key"] == "brand_new_key" for e in entries)]
        assert new_key_sections == ["OTHER"]
        entry = next(e for e in result["OTHER"] if e["key"] == "brand_new_key")
        assert entry["type"] == "bool"

    def test_section_map_routes_new_key(self):
        prefs = [("hot_exit", "always", "")]
        section_map = {"hot_exit": "APPLICATION › BEHAVIOR"}
        result = schema_gen.build_sections(prefs, [], section_map)
        assert "APPLICATION › BEHAVIOR" in result
        assert result["APPLICATION › BEHAVIOR"][0]["key"] == "hot_exit"

    def test_existing_sections_appear_before_new(self):
        prefs = [("font_size", 10, ""), ("unknown_key", True, "")]
        result = schema_gen.build_sections(prefs, self._existing(), {})
        keys = list(result.keys())
        assert keys[0] == "APPEARANCE › FONT"
