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
