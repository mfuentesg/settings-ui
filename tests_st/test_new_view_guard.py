import os
import tempfile

from unittesting import DeferrableTestCase
import sublime

NAV_MARK = "settings_ui_nav"
CONTENT_MARK = "settings_ui_content"


class TestNewViewGuard(DeferrableTestCase):
    """Exercises the real SettingsUiNewViewGuard listener that Sublime's
    plugin host already runs for this package, via real event dispatch --
    never by instantiating the listener class directly (see this plan's
    Global Constraints for why: a second manually-driven instance races the
    live one over shared state in the sibling close-listener case).

    Note: wherever a test does nav.close() immediately followed by
    content.close() with no yield between them, that ordering is only safe
    because both closes land in the same synchronous tick. SettingsUiCloseListener
    .on_pre_close schedules a deferred _close_remaining_window(window_id) call;
    inserting a yield between the two close() calls could let that callback
    fire while content is still marked, running close_window on the wrong
    window (potentially the main ST window running this whole test suite)."""

    def setUp(self):
        self.window = sublime.active_window()
        self._extra_windows = []

    def tearDown(self):
        for v in list(self.window.views()):
            if v.settings().get(NAV_MARK) or v.settings().get(CONTENT_MARK):
                v.close()
        for w in self._extra_windows:
            if w.is_valid():
                w.run_command("close_window")

    def _settings_window(self):
        nav = self.window.new_file()
        nav.settings().set(NAV_MARK, True)
        content = self.window.new_file()
        content.settings().set(CONTENT_MARK, True)
        return nav, content

    def test_ignores_view_in_non_settings_window(self):
        v = self.window.new_file()
        yield 300
        self.assertIn(v, self.window.views())
        v.close()

    def test_closes_stray_view_opened_in_settings_window(self):
        nav, content = self._settings_window()
        stray = self.window.new_file()
        yield 300

        self.assertFalse(stray.is_valid())
        nav.close()
        content.close()

    def test_ignores_new_view_while_content_pane_not_yet_created(self):
        """Regression test for the first-run flash-then-crash: a settings
        window mid-setup only has its nav pane marked. Closing the content
        view while it's still being created is exactly the bug that
        SettingsUiNewViewGuard's both-marks requirement was added to fix."""
        nav = self.window.new_file()
        nav.settings().set(NAV_MARK, True)
        content = self.window.new_file()
        yield 300

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
            yield 300  # let the guard's async redirect (set_timeout 0) run

            self.assertNotIn(stray, self.window.views())
            hosting = [w for w in sublime.windows()
                       if w.id() != self.window.id()
                       and any(v.file_name() == path for v in w.views())]
            self.assertEqual(len(hosting), 1)
            self._extra_windows.append(hosting[0])
            redirected_views = hosting[0].views()
            self.assertEqual(len(redirected_views), 1)
            self.assertEqual(redirected_views[0].file_name(), path)

            redirected_views[0].close()
            nav.close()
            content.close()
        finally:
            os.remove(path)
