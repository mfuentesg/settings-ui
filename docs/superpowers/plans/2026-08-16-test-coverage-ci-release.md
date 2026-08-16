# Test Coverage, CI Pipeline & 0.5.1 Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real regression coverage for the settings-window lifecycle code that has crashed twice on the Package Control review (`sublimehq/package_control_channel#9459`), wire up CI to run it on every push/PR, cut the `v0.5.1` tag that CHANGELOG.md already documents, and notify reviewers.

**Architecture:** Three test tiers — (A) existing pure-logic pytest, extended to `schema.py`/`state.py`; (B) new pytest tier against hand-rolled fake `sublime`/`sublime_plugin` modules, covering `panel.py`'s window/view helpers and `SettingsUI.py`'s event-listener race that PR #3 fixed; (C) a headless SublimeText/UnitTesting suite that runs inside a real ST4 instance in CI and exercises the actual open/close window lifecycle. A new GitHub Actions workflow runs Tier A+B and Tier C as separate jobs on every push/PR.

**Tech Stack:** Python 3.8, pytest 8.x, `uv` (dependency management, already in use via `uv.lock`), [SublimeText/UnitTesting](https://github.com/SublimeText/UnitTesting) framework, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-16-test-coverage-ci-release-design.md`

## Global Constraints

- Fakes model only what `lib/*.py` and `SettingsUI.py` actually call — no general-purpose ST mock library (spec "Out of scope").
- Tier A/B tests live under `tests/` (existing pytest suite); Tier C lives under `tests_st/` (a separate directory so UnitTesting's default `tests_dir` doesn't collide with the pytest suite already in `tests/`).
- No changes to `sublimehq/package_control_channel` itself — its `s.json` entry (`"tags": true`) is already correct.
- Existing `tests/test_schema_gen.py` and `tests/conftest.py`'s current two `sys.path.insert` lines are unchanged in behavior, only extended.

---

### Task 1: Fake `sublime`/`sublime_plugin` modules + test wiring

**Files:**
- Create: `tests/fakes/__init__.py`
- Create: `tests/fakes/sublime.py`
- Create: `tests/fakes/sublime_plugin.py`
- Create: `tests/helpers.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Produces (used by Tasks 3–4): `fakes.sublime` module importable as `sys.modules["sublime"]`, exposing `Region`, `Phantom`, `PhantomSet`, `Settings`, `View`, `Window`, `LAYOUT_BLOCK`, `windows()`, `active_window()`, `run_command(name, args=None)`, `load_settings(name)`, `save_settings(name)`, `set_timeout(callback, delay=0)`, `status_message(msg)`, `platform()`, `find_resources(pattern)`, `load_resource(path)`, `decode_value(text)`, `packages_path()`.
- Produces: `fakes.sublime_plugin` module importable as `sys.modules["sublime_plugin"]`, exposing `WindowCommand`, `EventListener`.
- Produces: `tests.helpers.import_settings_ui()` — returns a freshly executed `SettingsUI` module object each call, with `.lib` relative imports resolved.
- Consumes: nothing (first task).

- [ ] **Step 1: Create the fakes package**

```python
# tests/fakes/__init__.py
```

`tests/fakes/__init__.py` is intentionally empty — it just marks `fakes` as a package.

- [ ] **Step 2: Write the fake `sublime` module**

```python
# tests/fakes/sublime.py
"""
Minimal, stateful fake of the `sublime` module surface used by lib/*.py and
SettingsUI.py. Not a full API — only what this plugin actually calls.
"""
import json as _json

LAYOUT_BLOCK = 2


class Region:
    def __init__(self, a, b=None):
        self.a = a
        self.b = a if b is None else b

    def __eq__(self, other):
        return isinstance(other, Region) and (self.a, self.b) == (other.a, other.b)

    def __repr__(self):
        return "Region(%r, %r)" % (self.a, self.b)


class Phantom:
    def __init__(self, region, content, layout, on_navigate=None):
        self.region = region
        self.content = content
        self.layout = layout
        self.on_navigate = on_navigate


class PhantomSet:
    def __init__(self, view, key):
        self.view = view
        self.key = key
        self.phantoms = []

    def update(self, phantoms):
        self.phantoms = list(phantoms)


class Settings:
    def __init__(self):
        self._data = {}
        self._listeners = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def erase(self, key):
        self._data.pop(key, None)

    def add_on_change(self, tag, callback):
        self._listeners[tag] = callback

    def clear_on_change(self, tag):
        self._listeners.pop(tag, None)

    def trigger_change(self):
        """Test helper — not part of the real sublime API."""
        for cb in list(self._listeners.values()):
            cb()


class View:
    _next_id = [1]

    def __init__(self, window):
        self._id = View._next_id[0]
        View._next_id[0] += 1
        self._window = window
        self._settings = Settings()
        self._name = ""
        self._read_only = False
        self._file_name = None
        self._closed = False
        self._content = ""
        self._viewport = (0, 0)

    def id(self):
        return self._id

    def window(self):
        return None if self._closed else self._window

    def settings(self):
        return self._settings

    def set_name(self, name):
        self._name = name

    def set_scratch(self, scratch):
        pass

    def set_read_only(self, ro):
        self._read_only = ro

    def file_name(self):
        return self._file_name

    def run_command(self, name, args=None):
        if name == "append" and args:
            self._content += args.get("characters", "")

    def erase_phantoms(self, key):
        pass

    def viewport_position(self):
        return self._viewport

    def set_viewport_position(self, vp, animate=True):
        self._viewport = vp

    def text_point(self, row, col):
        return row * 100000 + col

    def text_to_layout(self, pt):
        return (0, pt)

    def close(self):
        self._closed = True
        if self._window is not None:
            self._window._remove_view(self)


class Window:
    _registry = {}
    _next_id = [1]

    def __new__(cls, window_id=None):
        if window_id is not None:
            existing = Window._registry.get(window_id)
            if existing is not None:
                return existing
            obj = object.__new__(cls)
            obj._id = window_id
            obj._views = []
            obj._valid = False
            Window._registry[window_id] = obj
            return obj
        obj = object.__new__(cls)
        obj._id = Window._next_id[0]
        Window._next_id[0] += 1
        obj._views = []
        obj._valid = True
        Window._registry[obj._id] = obj
        return obj

    def id(self):
        return self._id

    def is_valid(self):
        return self._valid

    def views(self):
        return list(self._views)

    def new_file(self):
        v = View(self)
        self._views.append(v)
        return v

    def open_file(self, fname):
        v = self.new_file()
        v._file_name = fname
        return v

    def set_view_index(self, view, group, index):
        pass

    def set_layout(self, layout):
        pass

    def set_tabs_visible(self, value):
        pass

    def set_status_bar_visible(self, value):
        pass

    def set_sidebar_visible(self, value):
        pass

    def set_minimap_visible(self, value):
        pass

    def active_view(self):
        return self._views[-1] if self._views else None

    def run_command(self, name, args=None):
        if name == "close_window":
            self._valid = False
            for v in list(self._views):
                self._remove_view(v)
            global _active_window
            if _active_window is self:
                _active_window = None

    def _remove_view(self, view):
        if view in self._views:
            self._views.remove(view)


_active_window = None
_settings_store = {}


def windows():
    return [w for w in Window._registry.values() if w.is_valid()]


def active_window():
    return _active_window


def run_command(name, args=None):
    global _active_window
    if name == "new_window":
        w = Window()
        _active_window = w


def load_settings(name):
    if name not in _settings_store:
        _settings_store[name] = Settings()
    return _settings_store[name]


def save_settings(name):
    pass


def set_timeout(callback, delay=0):
    callback()


def set_timeout_async(callback, delay=0):
    callback()


def status_message(msg):
    pass


def platform():
    return "linux"


def find_resources(pattern):
    return []


def load_resource(path):
    raise FileNotFoundError(path)


def decode_value(text):
    return _json.loads(text)


def packages_path():
    return "/fake/packages"


def reset():
    """Test helper — not part of the real sublime API. Call from test setup
    to reset all module-level fake state between tests."""
    global _active_window
    Window._registry = {}
    Window._next_id = [1]
    View._next_id = [1]
    _settings_store.clear()
    _active_window = None
```

- [ ] **Step 3: Write the fake `sublime_plugin` module**

```python
# tests/fakes/sublime_plugin.py
"""Minimal fake of the `sublime_plugin` module — base classes only."""


class WindowCommand:
    def __init__(self, window=None):
        self.window = window


class TextCommand:
    def __init__(self, view=None):
        self.view = view


class EventListener:
    pass
```

- [ ] **Step 4: Wire the fakes into conftest.py**

```python
# tests/conftest.py
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "lib"))
sys.path.insert(0, os.path.join(_root, "tests"))

import fakes.sublime as _fake_sublime
import fakes.sublime_plugin as _fake_sublime_plugin

sys.modules.setdefault("sublime", _fake_sublime)
sys.modules.setdefault("sublime_plugin", _fake_sublime_plugin)
```

- [ ] **Step 5: Write the SettingsUI.py import helper**

```python
# tests/helpers.py
"""
Test helper: import SettingsUI.py as part of a synthetic package so its
`from .lib import ...` relative imports resolve under plain pytest (Sublime
Text's own plugin loader provides that package context at runtime; pytest
does not).
"""
import importlib.util
import os
import sys
import types

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PKG_NAME = "settingsui_pkg"


def import_settings_ui():
    """Return a freshly executed SettingsUI module.

    Re-executes SettingsUI.py on every call so module-level globals (e.g.
    `_closing_window_id`) don't leak between tests. The `lib` subpackage
    it imports is cached normally across calls within a test session.
    """
    if _PKG_NAME not in sys.modules:
        pkg = types.ModuleType(_PKG_NAME)
        pkg.__path__ = [_ROOT]
        sys.modules[_PKG_NAME] = pkg

    module_name = _PKG_NAME + ".SettingsUI"
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(_ROOT, "SettingsUI.py")
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = _PKG_NAME
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 6: Verify the existing suite still passes with the new conftest**

Run: `pytest tests/ -v`
Expected: all 55 existing tests in `tests/test_schema_gen.py` still PASS (same count as before this change), confirming the fake-module injection didn't break anything since nothing yet imports `sublime`.

- [ ] **Step 7: Commit**

```bash
git add tests/fakes/__init__.py tests/fakes/sublime.py tests/fakes/sublime_plugin.py tests/helpers.py tests/conftest.py
git commit -m "test: add fake sublime/sublime_plugin modules and SettingsUI import helper"
```

---

### Task 2: Tier A — `schema.py` and `state.py` coverage

**Files:**
- Create: `tests/test_schema.py`
- Create: `tests/test_state.py`

**Interfaces:**
- Consumes: nothing new (imports `schema` and `state` directly via the existing `lib`-dir `sys.path` entry from `tests/conftest.py`, same pattern as `test_schema_gen.py`).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the failing tests for `schema.py`**

```python
# tests/test_schema.py
import schema


class TestConstructors:
    def test_b_builds_bool_entry(self):
        e = schema.b("k", "K", "d", True)
        assert e == {"key": "k", "title": "K", "desc": "d", "type": "bool", "default": True}

    def test_e_builds_enum_entry(self):
        e = schema.e("k", "K", "d", "a", [("A", "a"), ("B", "b")])
        assert e["type"] == "enum"
        assert e["choices"] == [("A", "a"), ("B", "b")]

    def test_n_builds_number_entry_with_defaults(self):
        e = schema.n("k", "K", "d", 1)
        assert e == {"key": "k", "title": "K", "desc": "d", "type": "number",
                      "default": 1, "presets": None, "step": 1, "is_float": False}

    def test_n_builds_float_entry(self):
        e = schema.n("k", "K", "d", 1.0, step=0.5, is_float=True)
        assert e["step"] == 0.5
        assert e["is_float"] is True

    def test_s_builds_string_entry(self):
        e = schema.s("k", "K", "d", "x", presets=["a", "b"])
        assert e["type"] == "string"
        assert e["presets"] == ["a", "b"]

    def test_j_builds_json_entry(self):
        e = schema.j("k", "K", "d", {})
        assert e["type"] == "json"

    def test_pk_builds_picker_entry(self):
        e = schema.pk("k", "K", "d", "x", "select_color_scheme")
        assert e["type"] == "picker"
        assert e["cmd"] == "select_color_scheme"

    def test_rp_builds_respick_entry(self):
        e = schema.rp("k", "K", "d", "x", "theme")
        assert e["type"] == "respick"
        assert e["kind"] == "theme"

    def test_lp_builds_listpick_entry(self):
        e = schema.lp("k", "K", "d", "x", "fonts")
        assert e["type"] == "listpick"
        assert e["provider"] == "fonts"


class TestSections:
    def test_sections_is_nonempty_list_of_title_entries_pairs(self):
        assert len(schema.SECTIONS) > 0
        for title, entries in schema.SECTIONS:
            assert isinstance(title, str) and title
            assert isinstance(entries, list) and len(entries) > 0

    def test_every_entry_has_required_fields(self):
        for _title, entries in schema.SECTIONS:
            for e in entries:
                assert "key" in e and e["key"]
                assert "title" in e and e["title"]
                assert "type" in e
                assert "default" in e

    def test_no_duplicate_keys_across_sections(self):
        keys = [e["key"] for _title, entries in schema.SECTIONS for e in entries]
        assert len(keys) == len(set(keys))


class TestKeyIndex:
    def test_key_index_covers_every_section_entry(self):
        for _title, entries in schema.SECTIONS:
            for e in entries:
                assert schema.KEY_INDEX[e["key"]] is e

    def test_key_index_size_matches_total_entries(self):
        total = sum(len(entries) for _title, entries in schema.SECTIONS)
        assert len(schema.KEY_INDEX) == total
```

- [ ] **Step 2: Run to verify it fails or passes as expected**

Run: `pytest tests/test_schema.py -v`
Expected: PASS — these assert existing, already-correct behavior of `schema.py` (a regression suite, not new implementation). If any test fails, it means `schema.py`'s actual `SECTIONS`/`KEY_INDEX` violates an invariant this test assumed — inspect the failure and fix the test's assumption to match real data, not the other way around (do not modify `schema.py` as part of this task).

- [ ] **Step 3: Write the tests for `state.py`**

```python
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
```

- [ ] **Step 4: Run both new test files**

Run: `pytest tests/test_schema.py tests/test_state.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_schema.py tests/test_state.py
git commit -m "test: add coverage for schema.py catalogue and state.py"
```

---

### Task 3: Tier B — `panel.py` window/view helper coverage

**Files:**
- Create: `tests/test_panel.py`

**Interfaces:**
- Consumes: `fakes.sublime.Window` (Task 1) — instantiate via `sublime.Window()` (no id) for a fresh, valid, empty window registered in `sublime.windows()`. `from lib import panel` — requires `tests/conftest.py`'s `sys.path` entry for the repo root (Task 1, Step 4) and the `sublime`/`sublime_plugin` fakes already injected into `sys.modules` (also Task 1) so `import sublime` inside `lib/panel.py` resolves.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_panel.py
import sublime
from lib import panel


def setup_function():
    sublime.reset()
    panel.reset_module_state()


def _fresh_window():
    return sublime.Window()


class TestGetActiveSettingsWindow:
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
    def test_clears_phantom_sets_and_flags(self):
        panel._phantom_sets[1] = object()
        panel._polling = True
        panel._prefs_listener_on = True
        panel._render_scheduled = True

        panel.reset_module_state()

        assert panel._phantom_sets == {}
        assert panel._polling is False
        assert panel._prefs_listener_on is False
```

- [ ] **Step 2: Run to verify it fails first (sanity check on the fakes)**

Run: `pytest tests/test_panel.py -v`
Expected: PASS on first run, since `panel.py` already implements this behavior — this task is regression coverage, not new implementation. If `ImportError: attempted relative import with no known parent package` appears, it means Task 1 Step 4's `sys.path`/`sys.modules` wiring is missing or ran after this import — fix `conftest.py`, don't work around it in this test file.

- [ ] **Step 3: Run full suite to confirm no regressions**

Run: `pytest tests/ -v`
Expected: all tests (55 pre-existing + Task 2's 18 + this task's 9 = 82) PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_panel.py
git commit -m "test: add coverage for panel.py window/view helpers"
```

---

### Task 4: Tier B — `SettingsUI.py` event-listener regression coverage (PR #3)

**Files:**
- Create: `tests/test_settings_ui.py`

**Interfaces:**
- Consumes: `tests.helpers.import_settings_ui()` (Task 1) — returns a fresh `SettingsUI` module with `.NAV_MARK`/`.CONTENT_MARK` accessible via `su.panel.NAV_MARK`/`su.panel.CONTENT_MARK` (the `panel` name bound inside the loaded module). `fakes.sublime.Window`/`sublime.reset()` (Task 1).
- Produces: nothing consumed by later tasks.

This task directly regression-tests the race `settings-ui#3` fixed: `SettingsUiNewViewGuard.on_new`/`on_load` discarding stray views opened inside the settings window, and `SettingsUiCloseListener`'s `_closing_window_id` guard that prevents the nested `close_window` deadlock.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_settings_ui.py
import sublime
from tests.helpers import import_settings_ui


def setup_function():
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
```

- [ ] **Step 2: Run to verify the tests pass against current `main`**

Run: `pytest tests/test_settings_ui.py -v`
Expected: all PASS against the current (post-PR #3) `SettingsUI.py` on `main`.

- [ ] **Step 3: Confirm the tests actually catch the regression**

Run: `git stash && git checkout 4f57a5d -- SettingsUI.py && pytest tests/test_settings_ui.py -v; git checkout HEAD -- SettingsUI.py && git stash pop`

`4f57a5d` is the commit immediately before the `settings-ui#3` deadlock fix (`ff2b9e2`). Expected: `test_skips_scheduling_when_already_closing` and/or `test_on_close_resets_state_once_no_settings_window_remains` FAIL against that older version — this proves the suite is not vacuously passing. If everything still passes against the pre-fix version, the tests aren't actually exercising the fixed code path; revisit Step 1 before continuing. After this check, `SettingsUI.py` must be back to its current `main` content (the `git checkout HEAD --` above restores it) — confirm with `git status` before proceeding.

- [ ] **Step 4: Run full suite**

Run: `pytest tests/ -v`
Expected: all tests (82 from Task 3 + this task's 6 = 88) PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_settings_ui.py
git commit -m "test: add regression coverage for the close-deadlock fix (settings-ui#3)"
```

---

### Task 5: Tier C — headless ST integration test (SublimeText/UnitTesting)

**Files:**
- Create: `.no-sublime-package`
- Create: `unittesting.json`
- Create: `tests_st/test_window_lifecycle.py`

**Interfaces:**
- Consumes: the real `settings_ui_open` command registered by `SettingsUI.py` (runs inside actual Sublime Text, not the fakes).
- Produces: `tests_st/` directory, referenced by Task 6's CI workflow as the directory the `SublimeText/UnitTesting/actions/run-tests@v1` action tests.

This tier cannot be run locally without a Sublime Text 4 install and the UnitTesting package; it is verified in Task 6 via CI. Write it now so Task 6 has something to run.

- [ ] **Step 1: Add the UnitTesting marker and config files**

```
# .no-sublime-package
```

```json
// unittesting.json
{
    "tests_dir": "tests_st",
    "pattern": "test_*.py",
    "verbosity": 2,
    "failfast": false
}
```

- [ ] **Step 2: Write the headless lifecycle test**

```python
# tests_st/test_window_lifecycle.py
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
        sublime.active_window().run_command("settings_ui_open")
        yield 300
        self.window = sublime.active_window()

        self.window.run_command("close_window")
        yield 300

        self.assertFalse(self.window.is_valid())

    def test_reopen_while_open_replaces_window_without_deadlock(self):
        sublime.active_window().run_command("settings_ui_open")
        yield 300
        first = sublime.active_window()

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
```

- [ ] **Step 3: Commit**

```bash
git add .no-sublime-package unittesting.json tests_st/test_window_lifecycle.py
git commit -m "test: add headless ST window-lifecycle suite via SublimeText/UnitTesting"
```

---

### Task 6: CI pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: Task 1–4's `tests/` suite (run via `pytest`), Task 5's `tests_st/` suite and `unittesting.json` (run via the UnitTesting GitHub Action).
- Produces: nothing consumed by later tasks — this is the terminal automation deliverable for the testing work.

- [ ] **Step 1: Write the workflow**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
  pull_request:

jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.8"
      - run: uv sync
      - run: uv run pytest tests/ -v

  st-headless:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: SublimeText/UnitTesting/actions/setup@v1
        with:
          sublime-text-version: 4
      - uses: SublimeText/UnitTesting/actions/run-tests@v1
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run pytest and headless ST tests on push and pull request"
```

- [ ] **Step 3: Push the branch and confirm both jobs go green**

```bash
git push -u origin HEAD
```

Then check the run: `gh run watch $(gh run list --branch $(git branch --show-current) --limit 1 --json databaseId -q '.[0].databaseId')`

Expected: both `pytest` and `st-headless` jobs report success. If `st-headless` fails, read its log via `gh run view --log-failed` before changing anything — do not delete or skip the job to make CI green.

---

### Task 7: Versioning — CHANGELOG and pyproject bump

**Files:**
- Modify: `CHANGELOG.md:3-13` (the `## [0.5.1]` entry)
- Modify: `pyproject.toml:3`

**Interfaces:**
- Consumes: nothing (independent of the test/CI tasks; can run any time after Task 6's CI is green on `main`, since Task 8 tags off of a green `main`).
- Produces: the exact CHANGELOG wording Task 9's PR comment references.

- [ ] **Step 1: Add the close-deadlock fix to the 0.5.1 CHANGELOG entry**

Current `CHANGELOG.md:3-13`:
```markdown
## [0.5.1] - 2026-07-05

### Fixed
- Removed the top-level `__init__.py` — Sublime Text loads every top-level `.py`
  file in a package as a plugin, and the docs advise against shipping an
  `__init__` file there
- `Settings UI: Generate Schema` no longer reads or writes files inside the
  package directory (which is read-only when installed as a `.sublime-package`
  zip). Package files are now read through `sublime.load_resource()`, and the
  regenerated `schema.py` is written under `sublime.packages_path()`, where it
  acts as a standard package override for zipped installs
```

Replace with:
```markdown
## [0.5.1] - 2026-08-16

### Fixed
- Removed the top-level `__init__.py` — Sublime Text loads every top-level `.py`
  file in a package as a plugin, and the docs advise against shipping an
  `__init__` file there
- `Settings UI: Generate Schema` no longer reads or writes files inside the
  package directory (which is read-only when installed as a `.sublime-package`
  zip). Package files are now read through `sublime.load_resource()`, and the
  regenerated `schema.py` is written under `sublime.packages_path()`, where it
  acts as a standard package override for zipped installs
- Fixed a deadlock when closing the settings window: `on_pre_close` no longer
  schedules a redundant `close_window` while one is already in flight for that
  window, and reopening the panel while it's already open no longer races with
  the in-progress close
```

(The date changes to match when this release is actually cut — see Task 8.)

- [ ] **Step 2: Bump the pyproject version**

Current `pyproject.toml:3`:
```toml
version = "0.1.0"
```

Replace with:
```toml
version = "0.5.1"
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "chore: document close-deadlock fix in 0.5.1 changelog, bump pyproject version"
```

---

### Task 8: Tag and push `v0.5.1`

**Files:** none (git tag operation).

**Interfaces:**
- Consumes: Task 6's green CI on `main`, Task 7's finalized CHANGELOG/pyproject.
- Produces: the `v0.5.1` git tag that Task 9's PR comment references and that Package Control's `"tags": true` release resolution depends on.

This pushes a tag to the public `mfuentesg/settings-ui` repository — visible to anyone watching the repo and immediately resolvable by Package Control. Confirm Tasks 1–7 are merged into `main` and CI is green on `main` before running this.

- [ ] **Step 1: Confirm `main` is clean and CI is green**

```bash
git checkout main && git pull && git status
gh run list --branch main --limit 1
```

Expected: `git status` shows a clean tree; the latest run on `main` shows `completed success`.

- [ ] **Step 2: Tag and push**

```bash
git tag -a v0.5.1 -m "v0.5.1: fix settings window close deadlock; add lifecycle test coverage and CI"
git push origin v0.5.1
```

- [ ] **Step 3: Verify Package Control can see the release**

```bash
gh api repos/mfuentesg/settings-ui/tags -q '.[].name'
```

Expected: `v0.5.1` appears at the top of the list.

---

### Task 9: Post status comment on the channel PR

**Files:** none (GitHub comment).

**Interfaces:**
- Consumes: Task 8's pushed `v0.5.1` tag.
- Produces: nothing (terminal task).

- [ ] **Step 1: Post the comment**

```bash
gh pr comment 9459 --repo sublimehq/package_control_channel --body "$(cat <<'EOF'
Update for @braver @kaste @deathaxe: the close-deadlock is fixed (settings-ui#3, merged), and I've since added regression coverage for it plus CI:

- Unit tests against a fake `sublime`/`sublime_plugin` layer covering the window/view helpers and the exact event-listener race that caused the deadlock (`tests/test_panel.py`, `tests/test_settings_ui.py`)
- A headless Sublime Text 4 integration suite (via SublimeText/UnitTesting) that opens and closes the real settings window in CI (`tests_st/`)
- Both run on every push/PR via GitHub Actions

Tagged `v0.5.1` so it's installable via Package Control (previously `0.5.0` was behind `main` and the CHANGELOG's `0.5.1` entry had no matching tag — that's fixed now too). Would appreciate a re-verify when you get a chance.
EOF
)"
```

- [ ] **Step 2: Confirm the comment posted**

```bash
gh pr view 9459 --repo sublimehq/package_control_channel --comments | tail -20
```

Expected: the comment from Step 1 appears as the most recent entry.

---

## Self-Review Notes

- **Spec coverage:** Tier A → Task 2; Tier B → Tasks 3–4; Tier C → Task 5; CI → Task 6; versioning → Tasks 7–8; channel PR → Task 9. All spec sections have a task.
- **Type/name consistency:** `panel.CONTENT_MARK`/`panel.NAV_MARK` (string constants `"settings_ui_content"`/`"settings_ui_nav"`) used identically across Task 3 (via `lib.panel`) and Task 5 (hardcoded to match, since the headless test can't import `lib.panel` — it imports the real `sublime` module ST provides, not `lib.panel`, so the two string literals in `tests_st/test_window_lifecycle.py` are intentionally not references to the constant). `import_settings_ui()` (Task 1) is consumed with the exact same call signature in Task 4.
- **No placeholders:** every step above has literal file content or literal shell output expectations to check against.
