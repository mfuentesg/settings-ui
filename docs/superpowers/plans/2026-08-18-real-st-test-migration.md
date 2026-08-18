# Real-ST Test Migration & Local Docker Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fake-`sublime`-backed pytest tests (Tier B) with real headless-Sublime-Text tests (Tier C), and give contributors a local Docker way to run Tier C, matching CI.

**Architecture:** Delete `tests/fakes/*` and its two consumer test files; port their exact test cases into `tests_st/` against the real `sublime`/`sublime_plugin` modules (already available inside the UnitTesting-run process). Add `tools/run-st-tests-docker.sh`, a thin wrapper that clones `SublimeText/UnitTesting` into a gitignored cache dir and execs its own `docker/ut-run-tests` launcher against this repo.

**Tech Stack:** pytest (Tier A only, unchanged), `unittesting`/`DeferrableTestCase` (Tier C), Docker (local Tier C runner via `SublimeText/UnitTesting`'s own `docker/` tooling), bash.

**Spec:** `docs/superpowers/specs/2026-08-18-real-st-test-migration-design.md`

## Global Constraints

- Tier A (`tests/test_schema.py`, `tests/test_state.py`, `tests/test_schema_gen.py`) must not change and must keep passing under `uv run pytest tests/ -v`.
- No new Dockerfile — `tools/run-st-tests-docker.sh` only clones/invokes `SublimeText/UnitTesting`'s existing `docker/ut-run-tests` launcher.
- Package name passed to the launcher must be `SettingsUI` (`--package-name SettingsUI`) — the repo directory is `settings-ui`, which does not match what `Main.sublime-menu`/`README.md`/Package Control expect.
- `.github/workflows/ci.yml` is not modified — CI keeps using `SublimeText/UnitTesting/actions/run-tests@v1` (see spec's "CI" section for why).
- Ported tests_st tests must use `tearDown`/cleanup to close every window/view they create, since real ST state persists across tests (no `sublime.reset()` equivalent).

---

### Task 1: Port `tests/test_panel.py` to `tests_st/test_panel.py`

**Files:**
- Create: `tests_st/test_panel.py`
- Reference (do not modify yet): `tests/test_panel.py`, `lib/panel.py`

**Interfaces:**
- Consumes: `lib.panel.get_active_settings_window()`, `lib.panel.get_nav_view(window)`, `lib.panel.get_content_view(window)`, `lib.panel.reset_module_state()`, `lib.panel.NAV_MARK`, `lib.panel.CONTENT_MARK`, `lib.panel._phantom_sets`, `lib.panel._polling`, `lib.panel._prefs_listener_on`, `lib.panel._render_scheduled` — all already exist in `lib/panel.py`, unchanged.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write `tests_st/test_panel.py`**

```python
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
```

- [ ] **Step 2: Run it against real ST via Docker**

Run: `./tools/run-st-tests-docker.sh --file tests_st/test_panel.py`
Expected: all tests in the file PASS.

- [ ] **Step 3: Commit**

```bash
git add tests_st/test_panel.py
git commit -m "test: port panel view-management tests to real-ST tests_st"
```

---

### Task 2: Port `TestNewViewGuard` to `tests_st/test_new_view_guard.py`

**Files:**
- Create: `tests_st/test_new_view_guard.py`
- Reference: `tests/test_settings_ui.py` (the `TestNewViewGuard` class), `SettingsUI.py`

**Interfaces:**
- Consumes: `SettingsUI.SettingsUiNewViewGuard` (a `sublime_plugin.EventListener` subclass with `on_new(view)`/`on_load(view)` methods), `lib.panel.NAV_MARK`, `lib.panel.CONTENT_MARK` — all exist unchanged in `SettingsUI.py`/`lib/panel.py`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write `tests_st/test_new_view_guard.py`**

```python
from unittesting import DeferrableTestCase
import sublime
import SettingsUI
from SettingsUI.lib import panel


class TestNewViewGuard(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self._extra_windows = []
        self.guard = SettingsUI.SettingsUiNewViewGuard()

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
        import tempfile, os
        nav, content = self._settings_window()
        fd, path = tempfile.mkstemp(suffix=".py")
        os.close(fd)
        try:
            stray = self.window.open_file(path)
            yield lambda: not stray.is_loading()

            self.guard.on_load(stray)
            yield 100

            self.assertNotIn(stray, self.window.views())
            other_windows = [w for w in sublime.windows() if w.id() != self.window.id()]
            self.assertEqual(len(other_windows), 1)
            redirected_views = other_windows[0].views()
            self.assertEqual(len(redirected_views), 1)
            self.assertEqual(redirected_views[0].file_name(), path)

            redirected_views[0].close()
            other_windows[0].run_command("close_window")
            nav.close()
            content.close()
        finally:
            os.remove(path)
```

- [ ] **Step 2: Run it against real ST via Docker**

Run: `./tools/run-st-tests-docker.sh --file tests_st/test_new_view_guard.py`
Expected: all tests PASS. If `test_redirects_loaded_file_out_of_settings_window` is flaky due to the `is_loading()` poll, increase the `yield 100` to `yield 300` (matches the delay already used in `tests_st/test_window_lifecycle.py`).

- [ ] **Step 3: Commit**

```bash
git add tests_st/test_new_view_guard.py
git commit -m "test: port new-view-guard tests to real-ST tests_st"
```

---

### Task 3: Port `TestCloseListenerDeadlockGuard` to `tests_st/test_close_listener_deadlock_guard.py`

**Files:**
- Create: `tests_st/test_close_listener_deadlock_guard.py`
- Reference: `tests/test_settings_ui.py` (the `TestCloseListenerDeadlockGuard` class), `SettingsUI.py`

**Interfaces:**
- Consumes: `SettingsUI.SettingsUiCloseListener` (`on_pre_close(view)`/`on_close(view)`), `SettingsUI._closing_window_id` (module-level global), `lib.panel.NAV_MARK`, `lib.panel.CONTENT_MARK`.
- Produces: nothing consumed by later tasks. This is the direct regression test for `settings-ui#3` — verify it in Step 2 the same way the original Tier B version was verified (spec's Testing section): confirm it fails on the pre-fix commit, passes on current code.

- [ ] **Step 1: Write `tests_st/test_close_listener_deadlock_guard.py`**

```python
from unittesting import DeferrableTestCase
import sublime
import SettingsUI
from SettingsUI.lib import panel


class TestCloseListenerDeadlockGuard(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self.listener = SettingsUI.SettingsUiCloseListener()
        SettingsUI._closing_window_id = None

    def tearDown(self):
        SettingsUI._closing_window_id = None
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
        SettingsUI._closing_window_id = self.window.id()
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
        SettingsUI._closing_window_id = None

        # on_pre_close fires while the closing view is still attached to the
        # window (that's what makes it "pre") -- don't close nav first, or
        # view.window() returns None and on_pre_close bails out early.
        self.listener.on_pre_close(nav)
        yield 300

        self.assertEqual(SettingsUI._closing_window_id, self.window.id())
        content.close()

    def test_on_close_resets_state_once_no_settings_window_remains(self):
        nav, content = self._settings_window()
        SettingsUI._closing_window_id = self.window.id()
        nav.close()
        content.close()

        self.listener.on_close(content)

        self.assertIsNone(SettingsUI._closing_window_id)
```

- [ ] **Step 2: Verify it's a real regression test, then run it**

Run: `git log --oneline -- SettingsUI.py | tail -20` to find the commit before the `settings-ui#3` close-deadlock fix, then:

```bash
git stash -u   # keep the new test files, if any uncommitted, out of the checkout below
git checkout <commit-before-fix>
./tools/run-st-tests-docker.sh --file tests_st/test_close_listener_deadlock_guard.py
```

Expected: `test_skips_scheduling_when_already_closing` FAILS on the pre-fix commit.

```bash
git checkout main
git stash pop   # if anything was stashed
./tools/run-st-tests-docker.sh --file tests_st/test_close_listener_deadlock_guard.py
```

Expected: all tests PASS on current `main`.

- [ ] **Step 3: Commit**

```bash
git add tests_st/test_close_listener_deadlock_guard.py
git commit -m "test: port close-listener deadlock-guard tests to real-ST tests_st"
```

---

### Task 4: Remove Tier B fakes and their consumer tests

**Files:**
- Delete: `tests/fakes/sublime.py`, `tests/fakes/sublime_plugin.py`, `tests/fakes/__init__.py` (whole `tests/fakes/` directory)
- Delete: `tests/test_panel.py`, `tests/test_settings_ui.py`, `tests/helpers.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: Tasks 1-3 must be committed first (coverage must exist in `tests_st/` before deleting the Tier B originals).
- Produces: `tests/conftest.py` retains only what Tier A needs.

- [ ] **Step 1: Confirm nothing else references the fakes or helpers**

Run: `grep -rln "fakes\|helpers" tests/*.py`
Expected: only `tests/conftest.py` (fakes registration), `tests/test_panel.py`, `tests/test_settings_ui.py` (about to be deleted) show up. If `test_schema.py`/`test_state.py`/`test_schema_gen.py` show up, stop and investigate before deleting anything.

- [ ] **Step 2: Delete the files**

```bash
git rm -r tests/fakes
git rm tests/test_panel.py tests/test_settings_ui.py tests/helpers.py
```

- [ ] **Step 3: Trim `tests/conftest.py`**

Replace its contents with:

```python
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "lib"))
```

(Drops the `tests/` sys.path entry and the `fakes.sublime`/`fakes.sublime_plugin`
`sys.modules` registration — both existed only for the code just deleted.)

- [ ] **Step 4: Run Tier A to confirm nothing broke**

Run: `uv run pytest tests/ -v`
Expected: all remaining tests in `tests/test_schema.py`, `tests/test_state.py`, `tests/test_schema_gen.py` PASS; no collection errors.

- [ ] **Step 5: Commit**

```bash
git commit -m "test: remove fake-sublime pytest tier, superseded by real-ST tests_st coverage"
```

---

### Task 5: Add the local Docker test runner

**Files:**
- Create: `tools/run-st-tests-docker.sh`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing from earlier tasks (usable standalone), but Tasks 1-3 already used it via its intended invocation `./tools/run-st-tests-docker.sh --file <path>`.
- Produces: `./tools/run-st-tests-docker.sh [extra ut-run-tests args...]` — runs the full `tests_st/` suite headlessly in Docker when called with no args.

- [ ] **Step 1: Write `tools/run-st-tests-docker.sh`**

```bash
#!/usr/bin/env bash
# Runs tests_st/ headlessly against real Sublime Text via Docker, using
# SublimeText/UnitTesting's own docker/ tooling (cloned on demand into a
# gitignored cache dir so this repo doesn't vendor it).
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="$REPO_ROOT/.cache/UnitTesting"

if [ ! -d "$CACHE_DIR/.git" ]; then
  mkdir -p "$(dirname "$CACHE_DIR")"
  git clone --depth 1 https://github.com/SublimeText/UnitTesting.git "$CACHE_DIR"
else
  git -C "$CACHE_DIR" pull --ff-only
fi

exec "$CACHE_DIR/docker/ut-run-tests" "$REPO_ROOT" --package-name SettingsUI "$@"
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x tools/run-st-tests-docker.sh`

- [ ] **Step 3: Add `.cache/` to `.gitignore`**

Check current contents first (`cat .gitignore`), then append a `.cache/` line if not already present.

- [ ] **Step 4: Run the full suite once to confirm the wrapper itself works end to end**

Run: `./tools/run-st-tests-docker.sh`
Expected: clones `UnitTesting` into `.cache/UnitTesting` on first run, builds the `unittesting-local` Docker image, and runs every file in `tests_st/` (including `test_window_lifecycle.py` and the three files from Tasks 1-3) — all PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/run-st-tests-docker.sh .gitignore
git commit -m "chore: add local Docker runner for tests_st, matching CI's headless ST tier"
```

---

### Task 6: Document the new local workflow and update CHANGELOG

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 5's `tools/run-st-tests-docker.sh` must exist.
- Produces: nothing consumed by later tasks (final task).

- [ ] **Step 1: Add a "Running tests" section to `README.md`**

Read the current `README.md` first to match its existing heading style, then add a
section (near any existing development/contributing content, or at the end if none
exists) covering:

```markdown
## Running tests

Pure-logic tests (`tests/`):

    uv run pytest tests/ -v

Real-Sublime-Text lifecycle tests (`tests_st/`) run headlessly via Docker — no local
Sublime Text install or license required:

    ./tools/run-st-tests-docker.sh

Run a single file: `./tools/run-st-tests-docker.sh --file tests_st/test_panel.py`.
First run clones `SublimeText/UnitTesting` into `.cache/` and builds a local Docker
image; subsequent runs reuse a cached Docker volume and are much faster. CI runs the
same `tests_st/` suite via `SublimeText/UnitTesting`'s official GitHub Action instead
of Docker — see `docs/superpowers/specs/2026-08-18-real-st-test-migration-design.md`
for why the two entry points differ while testing identical content.
```

- [ ] **Step 2: Add a CHANGELOG entry**

Read `CHANGELOG.md`'s existing `## [Unreleased]` section (or top entry) first to match
its format, then add bullets under it describing: removal of the fake-`sublime` pytest
tier in favor of real headless-ST tests in `tests_st/`, and the new
`tools/run-st-tests-docker.sh` local runner.

- [ ] **Step 3: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: document tests_st Docker runner and fake-tier removal"
```
