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


class TestOnNav:
    def setup_method(self):
        _reset()

    def test_runs_native_picker_in_settings_window(self):
        normal_window = _fresh_window()
        settings_window = _fresh_window()
        content = settings_window.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        normal_calls = []
        settings_calls = []
        normal_window.run_command = lambda name: normal_calls.append(name)
        settings_window.run_command = lambda name: settings_calls.append(name)

        panel.on_nav("cmd:select_color_scheme")

        assert settings_calls == ["hide_overlay", "select_color_scheme"]
        assert normal_calls == []

    def test_hides_existing_overlay_before_resource_picker(self, monkeypatch):
        settings_window = _fresh_window()
        content = settings_window.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        events = []
        settings_window.run_command = lambda name: events.append(name)
        monkeypatch.setattr(
            panel.pickers,
            "open_resource_picker",
            lambda key: events.append("picker:" + key),
        )

        panel.on_nav("respick:dark_color_scheme")

        assert events == ["hide_overlay", "picker:dark_color_scheme"]

    def test_reset_all_rerenders_both_panes(self, monkeypatch):
        # Regression: reset_all used to only re-render the content pane,
        # leaving the nav sidebar showing stale colors (settings-ui#7).
        w = _fresh_window()
        content = w.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        calls = []
        monkeypatch.setattr(panel, "render_nav", lambda: calls.append("nav"))
        monkeypatch.setattr(panel, "render_content", lambda: calls.append("content"))
        monkeypatch.setattr(panel.prefs, "reset_all", lambda: None)

        panel.on_nav("action:reset_all")

        assert calls == ["nav", "content"]

    def test_pref_mutation_rerenders_both_panes(self, monkeypatch):
        # Regression: toggling/resetting/stepping a setting used to only
        # re-render the content pane (settings-ui#7).
        w = _fresh_window()
        content = w.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        calls = []
        monkeypatch.setattr(panel, "render_nav", lambda: calls.append("nav"))
        monkeypatch.setattr(panel, "render_content", lambda: calls.append("content"))

        panel.on_nav("reset:some_setting_key")

        assert calls == ["nav", "content"]


class TestScheduledRender:
    def setup_method(self):
        _reset()

    def test_rerenders_both_panes(self, monkeypatch):
        # Regression: a prefs change from outside the UI (e.g. editing the
        # raw JSON file) used to only re-render the content pane, leaving
        # the nav sidebar stale (settings-ui#7).
        w = _fresh_window()
        content = w.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        calls = []
        monkeypatch.setattr(panel, "render_nav", lambda: calls.append("nav"))
        monkeypatch.setattr(panel, "render_content", lambda: calls.append("content"))

        panel._do_scheduled_render()

        assert calls == ["nav", "content"]

    def test_does_nothing_without_a_settings_window(self, monkeypatch):
        calls = []
        monkeypatch.setattr(panel, "render_nav", lambda: calls.append("nav"))
        monkeypatch.setattr(panel, "render_content", lambda: calls.append("content"))

        panel._do_scheduled_render()

        assert calls == []


class TestPhantomSetRecreatedEveryRender:
    """
    Regression coverage for settings-ui#7: sublime.PhantomSet.update() skips
    repainting any phantom whose HTML text is byte-identical to what's
    already displayed, which left most rows showing colors resolved from a
    stale color scheme/theme after a setting change. render_nav()/
    render_content() must build a brand new PhantomSet every call (never
    reuse the previous one) so every phantom is always forced to repaint.
    """
    def setup_method(self):
        _reset()

    def test_render_nav_recreates_phantom_set_every_call(self, monkeypatch):
        w = _fresh_window()
        content = w.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        monkeypatch.setattr(panel.renderer, "build_nav_html", lambda *a, **k: "<div/>")

        panel.render_nav()
        nav_view = panel.get_nav_view(w)
        first = panel._phantom_sets[nav_view.id()]

        panel.render_nav()
        second = panel._phantom_sets[nav_view.id()]

        assert first is not second

    def test_render_content_recreates_phantom_set_every_call(self, monkeypatch):
        w = _fresh_window()
        content = w.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        monkeypatch.setattr(panel.renderer, "build_content_phantoms", lambda *a, **k: [])

        panel.render_content()
        first = panel._phantom_sets[content.id()]

        panel.render_content()
        second = panel._phantom_sets[content.id()]

        assert first is not second

    def test_render_nav_erases_phantoms_every_call(self, monkeypatch):
        w = _fresh_window()
        content = w.new_file()
        content.settings().set(panel.CONTENT_MARK, True)
        monkeypatch.setattr(panel.renderer, "build_nav_html", lambda *a, **k: "<div/>")
        erase_calls = []
        nav_view = panel.get_nav_view(w)
        monkeypatch.setattr(nav_view, "erase_phantoms", lambda key: erase_calls.append(key))

        panel.render_nav()
        panel.render_nav()

        assert erase_calls == [panel.PANEL_PHANTOM_NAV, panel.PANEL_PHANTOM_NAV]


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
