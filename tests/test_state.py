# tests/test_state.py
import state


def setup_function():
    state._filter = ""
    state._category = 0


def test_filter_defaults_to_empty_string():
    assert state._filter == ""


def test_category_defaults_to_zero():
    assert state._category == 0


def test_filter_is_mutable_module_state():
    state._filter = "font"
    assert state._filter == "font"


def test_category_is_mutable_module_state():
    state._category = 3
    assert state._category == 3
