import os
import tempfile

from unittesting import DeferrableTestCase
import sublime
import SettingsUI.SettingsUI as settings_ui
from SettingsUI.lib import panel


class TestNewViewGuard(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self._extra_windows = []
        self.guard = settings_ui.SettingsUiNewViewGuard()

    def tearDown(self):
        for v in list(self.window.views()):
            if v.settings().get(panel.NAV_MARK) or v.settings().get(panel.CONTENT_MARK):
                v.close()
        for w in self._extra_windows:
            if w.is_valid():
                w.run_command("close_window")

    def _settings_window(self):
        nav = self.window.new_file()
        nav.settings().set(panel.NAV_MARK, True)
        content = self.window.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        return nav, content

    def test_ignores_view_in_non_settings_window(self):
        v = self.window.new_file()
        self.guard.on_new(v)
        self.assertIn(v, self.window.views())
        v.close()

    def test_closes_stray_view_opened_in_settings_window(self):
        nav, content = self._settings_window()
        stray = self.window.new_file()

        self.guard.on_new(stray)
        # on_new schedules the close via sublime.set_timeout rather than
        # closing synchronously -- give it a tick to run.
        yield 300

        self.assertFalse(stray.is_valid())
        nav.close()
        content.close()

    def test_ignores_new_view_while_content_pane_not_yet_created(self):
        """Regression test for the first-run flash-then-crash: a settings
        window mid-setup only has its nav pane marked. Closing the content
        view while it's still being created is exactly the bug that
        _is_settings_window()'s both-marks requirement was added to fix."""
        nav = self.window.new_file()
        nav.settings().set(panel.NAV_MARK, True)
        content = self.window.new_file()

        self.guard.on_new(content)

        self.assertIn(content, self.window.views())
        nav.close()
        content.close()

    def test_redirects_loaded_file_out_of_settings_window(self):
        nav, content = self._settings_window()
        fd, path = tempfile.mkstemp(suffix=".py")
        os.close(fd)
        try:
            stray = self.window.open_file(path)
            yield lambda: not stray.is_loading()

            self.guard.on_load(stray)
            yield 300

            self.assertNotIn(stray, self.window.views())
            other_windows = [w for w in sublime.windows() if w.id() != self.window.id()]
            self.assertEqual(len(other_windows), 1)
            self._extra_windows.append(other_windows[0])
            redirected_views = other_windows[0].views()
            self.assertEqual(len(redirected_views), 1)
            self.assertEqual(redirected_views[0].file_name(), path)

            redirected_views[0].close()
            nav.close()
            content.close()
        finally:
            os.remove(path)
