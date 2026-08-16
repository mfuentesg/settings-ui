from unittesting import DeferrableTestCase
import sublime


class TestSettingsWindowLifecycle(DeferrableTestCase):
    def setUp(self):
        self.window = None

    def tearDown(self):
        if self.window is not None and self.window.is_valid():
            self.window.run_command("close_window")

    def test_open_creates_two_pane_window_without_crashing(self):
        before_ids = set(w.id() for w in sublime.windows())

        sublime.active_window().run_command("settings_ui_open")
        yield 300

        new_windows = [w for w in sublime.windows() if w.id() not in before_ids]
        self.assertEqual(len(new_windows), 1)
        self.window = new_windows[0]

        marked = [
            v for v in self.window.views()
            if v.settings().get("settings_ui_content") or v.settings().get("settings_ui_nav")
        ]
        self.assertEqual(len(marked), 2)

    def test_close_does_not_deadlock_or_crash(self):
        before_ids = set(w.id() for w in sublime.windows())

        sublime.active_window().run_command("settings_ui_open")
        yield 300

        new_windows = [w for w in sublime.windows() if w.id() not in before_ids]
        self.assertEqual(len(new_windows), 1)
        self.window = new_windows[0]

        marked = [
            v for v in self.window.views()
            if v.settings().get("settings_ui_content") or v.settings().get("settings_ui_nav")
        ]
        self.assertEqual(len(marked), 2)

        self.window.run_command("close_window")
        yield 300

        self.assertFalse(self.window.is_valid())

    def test_reopen_while_open_replaces_window_without_deadlock(self):
        before_ids = set(w.id() for w in sublime.windows())

        sublime.active_window().run_command("settings_ui_open")
        yield 300

        first_new = [w for w in sublime.windows() if w.id() not in before_ids]
        self.assertEqual(len(first_new), 1)
        first = first_new[0]

        sublime.active_window().run_command("settings_ui_open")
        yield 500

        self.assertFalse(first.is_valid())
        self.window = sublime.active_window()
        self.assertTrue(self.window.is_valid())
        marked = [
            v for v in self.window.views()
            if v.settings().get("settings_ui_content") or v.settings().get("settings_ui_nav")
        ]
        self.assertEqual(len(marked), 2)
