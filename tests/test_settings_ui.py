import pytest
import sublime
from tests.helpers import import_settings_ui


@pytest.fixture(autouse=True)
def _reset_fakes():
    # pytest's module-level setup_function() hook does NOT run before methods
    # of test classes (only before bare module-level test functions) — every
    # test class below needs this reset, so an autouse fixture is used
    # instead of setup_function().
    sublime.reset()


def _settings_window():
    """A window with both settings panes already present, like an open panel."""
    w = sublime.Window()
    nav = w.new_file()
    nav.settings().set("settings_ui_nav", True)
    content = w.new_file()
    content.settings().set("settings_ui_content", True)
    return w, nav, content


class TestNewViewGuard:
    def test_ignores_view_in_non_settings_window(self):
        su = import_settings_ui()
        w = sublime.Window()
        v = w.new_file()
        guard = su.SettingsUiNewViewGuard()

        guard.on_new(v)

        assert v in w.views()

    def test_closes_stray_view_opened_in_settings_window(self):
        su = import_settings_ui()
        w, _nav, _content = _settings_window()
        stray = w.new_file()
        guard = su.SettingsUiNewViewGuard()

        guard.on_new(stray)

        assert stray not in w.views()

    def test_redirects_loaded_file_out_of_settings_window(self):
        su = import_settings_ui()
        w, _nav, _content = _settings_window()
        stray = w.new_file()
        stray._file_name = "/tmp/some_file.py"
        guard = su.SettingsUiNewViewGuard()

        guard.on_load(stray)

        assert stray not in w.views()
        other_windows = [ow for ow in sublime.windows() if ow is not w]
        assert len(other_windows) == 1
        redirected = other_windows[0].views()
        assert len(redirected) == 1
        assert redirected[0].file_name() == "/tmp/some_file.py"


class TestCloseListenerDeadlockGuard:
    def test_skips_scheduling_when_already_closing(self):
        """Regression test for settings-ui#3: on_pre_close must not schedule
        another close_window while one is already in flight for this window,
        or Sublime deadlocks on the nested command."""
        su = import_settings_ui()
        w, nav, _content = _settings_window()
        su._closing_window_id = w.id()
        original_run_command = w.run_command
        calls = []
        w.run_command = lambda name, args=None: (calls.append(name), original_run_command(name, args))[-1]

        listener = su.SettingsUiCloseListener()
        listener.on_pre_close(nav)

        assert "close_window" not in calls
        assert w.is_valid()

    def test_closes_remaining_window_when_one_pane_still_open(self):
        su = import_settings_ui()
        w, nav, _content = _settings_window()
        su._closing_window_id = None

        # on_pre_close fires while the closing view is still attached to the
        # window (that's what makes it "pre") — don't call nav.close() first,
        # or view.window() returns None and on_pre_close bails out early.
        listener = su.SettingsUiCloseListener()
        listener.on_pre_close(nav)

        assert w.is_valid() is False
        assert su._closing_window_id == w.id()

    def test_on_close_resets_state_once_no_settings_window_remains(self):
        su = import_settings_ui()
        w, nav, content = _settings_window()
        su._closing_window_id = w.id()
        listener = su.SettingsUiCloseListener()
        nav.close()
        content.close()

        listener.on_close(content)

        assert su._closing_window_id is None
