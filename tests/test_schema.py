# tests/test_schema.py
import schema


class TestConstructors:
    def test_b_builds_bool_entry(self):
        e = schema.b("k", "K", "d", True)
        assert e == {"key": "k", "title": "K", "desc": "d", "type": "bool", "default": True}

    def test_e_builds_enum_entry(self):
        e = schema.e("k", "K", "d", "a", [("A", "a"), ("B", "b")])
        assert e["type"] == "enum"
        assert e["choices"] == [("A", "a"), ("B", "b")]

    def test_n_builds_number_entry_with_defaults(self):
        e = schema.n("k", "K", "d", 1)
        assert e == {"key": "k", "title": "K", "desc": "d", "type": "number",
                      "default": 1, "presets": None, "step": 1, "is_float": False}

    def test_n_builds_float_entry(self):
        e = schema.n("k", "K", "d", 1.0, step=0.5, is_float=True)
        assert e["step"] == 0.5
        assert e["is_float"] is True

    def test_s_builds_string_entry(self):
        e = schema.s("k", "K", "d", "x", presets=["a", "b"])
        assert e["type"] == "string"
        assert e["presets"] == ["a", "b"]

    def test_j_builds_json_entry(self):
        e = schema.j("k", "K", "d", {})
        assert e["type"] == "json"

    def test_pk_builds_picker_entry(self):
        e = schema.pk("k", "K", "d", "x", "select_color_scheme")
        assert e["type"] == "picker"
        assert e["cmd"] == "select_color_scheme"

    def test_rp_builds_respick_entry(self):
        e = schema.rp("k", "K", "d", "x", "theme")
        assert e["type"] == "respick"
        assert e["kind"] == "theme"

    def test_lp_builds_listpick_entry(self):
        e = schema.lp("k", "K", "d", "x", "fonts")
        assert e["type"] == "listpick"
        assert e["provider"] == "fonts"


class TestSections:
    def test_sections_is_nonempty_list_of_title_entries_pairs(self):
        assert len(schema.SECTIONS) > 0
        for title, entries in schema.SECTIONS:
            assert isinstance(title, str) and title
            assert isinstance(entries, list) and len(entries) > 0

    def test_every_entry_has_required_fields(self):
        for _title, entries in schema.SECTIONS:
            for e in entries:
                assert "key" in e and e["key"]
                assert "title" in e and e["title"]
                assert "type" in e
                assert "default" in e

    def test_no_duplicate_keys_across_sections(self):
        keys = [e["key"] for _title, entries in schema.SECTIONS for e in entries]
        assert len(keys) == len(set(keys))


class TestKeyIndex:
    def test_key_index_covers_every_section_entry(self):
        for _title, entries in schema.SECTIONS:
            for e in entries:
                assert schema.KEY_INDEX[e["key"]] is e

    def test_key_index_size_matches_total_entries(self):
        total = sum(len(entries) for _title, entries in schema.SECTIONS)
        assert len(schema.KEY_INDEX) == total
