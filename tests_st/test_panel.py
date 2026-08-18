from unittesting import DeferrableTestCase
import sublime
from SettingsUI.lib import panel


class TestGetActiveSettingsWindow(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self._created_views = []
        panel.reset_module_state()

    def tearDown(self):
        for v in self._created_views:
            if v.is_valid():
                v.close()
        panel.reset_module_state()

    def test_returns_none_without_marked_view(self):
        v = self.window.new_file()
        self._created_views.append(v)
        self.assertIsNone(panel.get_active_settings_window())

    def test_finds_window_with_content_mark(self):
        v = self.window.new_file()
        self._created_views.append(v)
        v.settings().set(panel.CONTENT_MARK, True)
        self.assertIs(panel.get_active_settings_window(), self.window)

    def test_finds_window_with_nav_mark_only_returns_none(self):
        v = self.window.new_file()
        self._created_views.append(v)
        v.settings().set(panel.NAV_MARK, True)
        self.assertIsNone(panel.get_active_settings_window())


class TestGetNavView(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        panel.reset_module_state()

    def tearDown(self):
        for v in list(self.window.views()):
            if v.settings().get(panel.NAV_MARK) or v.settings().get(panel.CONTENT_MARK):
                v.close()
        panel.reset_module_state()

    def test_creates_and_marks_new_nav_view(self):
        v = panel.get_nav_view(self.window)
        self.assertIs(v.settings().get(panel.NAV_MARK), True)
        self.assertIn(v, self.window.views())

    def test_returns_existing_nav_view_without_duplicating(self):
        first = panel.get_nav_view(self.window)
        second = panel.get_nav_view(self.window)
        self.assertIs(first, second)


class TestGetContentView(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        panel.reset_module_state()

    def tearDown(self):
        for v in list(self.window.views()):
            if v.settings().get(panel.NAV_MARK) or v.settings().get(panel.CONTENT_MARK):
                v.close()
        panel.reset_module_state()

    def test_creates_and_marks_new_content_view(self):
        v = panel.get_content_view(self.window)
        self.assertIs(v.settings().get(panel.CONTENT_MARK), True)

    def test_prepopulates_two_hundred_lines_and_locks_view(self):
        v = panel.get_content_view(self.window)
        text = v.substr(sublime.Region(0, v.size()))
        self.assertEqual(text.count("\n"), 200)
        self.assertTrue(v.is_read_only())

    def test_returns_existing_content_view_without_duplicating(self):
        first = panel.get_content_view(self.window)
        second = panel.get_content_view(self.window)
        self.assertIs(first, second)


class TestResetModuleState(DeferrableTestCase):
    def test_clears_phantom_sets_and_flags(self):
        panel._phantom_sets[1] = object()
        panel._polling = True
        panel._prefs_listener_on = True
        panel._render_scheduled = True

        panel.reset_module_state()

        self.assertEqual(panel._phantom_sets, {})
        self.assertFalse(panel._polling)
        self.assertFalse(panel._prefs_listener_on)
        self.assertFalse(panel._render_scheduled)
