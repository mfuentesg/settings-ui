# tests/test_panel.py
import sublime
from lib import panel


def _reset():
    sublime.reset()
    panel.reset_module_state()


def _fresh_window():
    return sublime.Window()


class TestGetActiveSettingsWindow:
    def setup_method(self):
        _reset()
    def test_returns_none_without_marked_view(self):
        w = _fresh_window()
        w.new_file()
        assert panel.get_active_settings_window() is None

    def test_finds_window_with_content_mark(self):
        w = _fresh_window()
        v = w.new_file()
        v.settings().set(panel.CONTENT_MARK, True)
        assert panel.get_active_settings_window() is w

    def test_finds_window_with_nav_mark_only_returns_none(self):
        # get_active_settings_window() keys off CONTENT_MARK specifically.
        w = _fresh_window()
        v = w.new_file()
        v.settings().set(panel.NAV_MARK, True)
        assert panel.get_active_settings_window() is None


class TestGetNavView:
    def setup_method(self):
        _reset()

    def test_creates_and_marks_new_nav_view(self):
        w = _fresh_window()
        v = panel.get_nav_view(w)
        assert v.settings().get(panel.NAV_MARK) is True
        assert v in w.views()

    def test_returns_existing_nav_view_without_duplicating(self):
        w = _fresh_window()
        first = panel.get_nav_view(w)
        second = panel.get_nav_view(w)
        assert first is second
        assert len(w.views()) == 1


class TestGetContentView:
    def setup_method(self):
        _reset()

    def test_creates_and_marks_new_content_view(self):
        w = _fresh_window()
        v = panel.get_content_view(w)
        assert v.settings().get(panel.CONTENT_MARK) is True

    def test_prepopulates_two_hundred_lines_and_locks_view(self):
        w = _fresh_window()
        v = panel.get_content_view(w)
        assert v._content.count("\n") == 200
        assert v._read_only is True

    def test_returns_existing_content_view_without_duplicating(self):
        w = _fresh_window()
        first = panel.get_content_view(w)
        second = panel.get_content_view(w)
        assert first is second
        assert len(w.views()) == 1


class TestResetModuleState:
    def setup_method(self):
        _reset()

    def test_clears_phantom_sets_and_flags(self):
        panel._phantom_sets[1] = object()
        panel._polling = True
        panel._prefs_listener_on = True
        panel._render_scheduled = True

        panel.reset_module_state()

        assert panel._phantom_sets == {}
        assert panel._polling is False
        assert panel._prefs_listener_on is False
        assert panel._render_scheduled is False
