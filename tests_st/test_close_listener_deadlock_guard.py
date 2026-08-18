from unittesting import DeferrableTestCase
import sublime
import SettingsUI.SettingsUI as settings_ui
from SettingsUI.lib import panel


class TestCloseListenerDeadlockGuard(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self.listener = settings_ui.SettingsUiCloseListener()
        settings_ui._closing_window_id = None

    def tearDown(self):
        settings_ui._closing_window_id = None
        for v in list(self.window.views()):
            if v.settings().get(panel.NAV_MARK) or v.settings().get(panel.CONTENT_MARK):
                v.close()

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
        calls = []
        original_run_command = self.window.run_command
        self.window.run_command = lambda name, args=None: (
            calls.append(name),
            original_run_command(name, args),
        )[-1]

        try:
            self.listener.on_pre_close(nav)
            self.assertNotIn("close_window", calls)
        finally:
            self.window.run_command = original_run_command
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
        content.close()

    def test_on_close_resets_state_once_no_settings_window_remains(self):
        nav, content = self._settings_window()
        settings_ui._closing_window_id = self.window.id()
        nav.close()
        content.close()

        self.listener.on_close(content)

        self.assertIsNone(settings_ui._closing_window_id)
