from unittesting import DeferrableTestCase
import sublime
import SettingsUI.SettingsUI as settings_ui
from SettingsUI.lib import panel


class TestCloseListenerDeadlockGuard(DeferrableTestCase):
    def setUp(self):
        # _close_remaining_window() below runs a real close_window command on
        # self.window -- if that were the harness's sole window, closing it
        # would hang the whole headless run (confirmed in CI). Run these
        # tests in a dedicated second window instead, so the harness's own
        # window is never touched.
        sublime.active_window().run_command("new_window")
        yield 300
        self.window = sublime.active_window()
        self.listener = settings_ui.SettingsUiCloseListener()
        settings_ui._closing_window_id = None

    def tearDown(self):
        settings_ui._closing_window_id = None
        if self.window.is_valid():
            self.window.run_command("close_window")

    def _settings_window(self):
        nav = self.window.new_file()
        nav.settings().set(panel.NAV_MARK, True)
        content = self.window.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        return nav, content

    def test_skips_scheduling_when_already_closing(self):
        """Regression test for settings-ui#3: on_pre_close must not schedule
        another close_window while one is already in flight for this window,
        or Sublime deadlocks on the nested command."""
        nav, content = self._settings_window()
        settings_ui._closing_window_id = self.window.id()

        self.listener.on_pre_close(nav)
        yield 300

        self.assertTrue(self.window.is_valid())
        nav.close()
        content.close()

    def test_closes_remaining_window_when_one_pane_still_open(self):
        nav, content = self._settings_window()
        settings_ui._closing_window_id = None

        # on_pre_close fires while the closing view is still attached to the
        # window (that's what makes it "pre") -- don't close nav first, or
        # view.window() returns None and on_pre_close bails out early.
        self.listener.on_pre_close(nav)
        yield 300

        self.assertEqual(settings_ui._closing_window_id, self.window.id())
        self.assertFalse(self.window.is_valid())

    def test_on_close_resets_state_once_no_settings_window_remains(self):
        nav, content = self._settings_window()
        settings_ui._closing_window_id = self.window.id()
        nav.close()
        content.close()

        self.listener.on_close(content)

        self.assertIsNone(settings_ui._closing_window_id)
