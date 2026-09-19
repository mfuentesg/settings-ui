# Real-ST Regression Smoke Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small, separate real-Sublime-Text test tier that exercises only the two window-lifecycle regressions (`settings-ui#3`'s close-deadlock, and the first-run flash-then-crash) that the existing `tests/` fake-`sublime` suite structurally cannot validate — without touching or replacing the existing fast pytest suite.

**Architecture:** Two independent test tiers stay independent. `tests/` (pytest + `tests/fakes/`) remains the primary, fast, deterministic CI gate for pure logic (schema/prefs/state/panel helpers) — untouched by this plan. A new `tests_st/` tier, run via [SublimeText/UnitTesting](https://github.com/SublimeText/UnitTesting), covers only real window/view lifecycle behavior that a hand-rolled `sublime` model can't faithfully reproduce. It runs as its own CI job (`st-headless`), separate from and not blocking on the `pytest` job, and can be reproduced locally via Docker with no local Sublime Text install or license.

**Tech Stack:** pytest (existing tier, unchanged), SublimeText/UnitTesting (headless real-ST test runner + GitHub Action), Docker (local reproduction of the CI runner).

**Spec:** This plan supersedes the reverted `docs/superpowers/plans/2026-08-18-real-st-test-migration.md` / `docs/superpowers/specs/2026-08-18-real-st-test-migration-design.md` (deleted by the `af89b23`→`v0.5.1` revert). Those docs targeted a full swap (delete `tests/fakes/*`, port everything to `tests_st/`); this plan deliberately narrows scope to the two regression tests that justified the effort, based on two known failure modes from that attempt (see Global Constraints).

## Global Constraints

- Do **not** delete or modify `tests/fakes/`, `tests/test_panel.py`, or `tests/test_settings_ui.py`. The pytest tier stays exactly as it is today (v0.5.1 baseline) — this plan only adds files, it doesn't remove any.
- `tests_st/` files must import the package as `SettingsUI.SettingsUI` / `SettingsUI.lib` (real ST loads packages by their `Packages/<Name>/` folder name), not by relative repo-root imports the way `tests/` does.
- The `st-headless` CI job **must** pass `package-name: SettingsUI` to both `SublimeText/UnitTesting/actions/setup@v1` and `.../run-tests@v1` from the first commit that adds it. (Known failure mode: without this, UnitTesting's setup action derives the package folder name from the GitHub repo name — `mfuentesg/settings-ui` → `settings-ui` — which doesn't match `SettingsUI`, the name `Main.sublime-menu`/README/Package Control actually use, causing `ModuleNotFoundError` on `import SettingsUI.SettingsUI`.)
- Any test that closes a real `sublime.Window` must never close the test harness's own (only) window — headless CI has exactly one window at start, and closing it hangs the entire run with no error, just a timeout. Tests needing to close a window must open a dedicated second window in `setUp` (`sublime.active_window().run_command("new_window")`, then `yield 300` to let it become active) and close only that one in `tearDown`.
- `tests_st/` test methods that trigger async Sublime commands must `yield <milliseconds>` (a `DeferrableTestCase` idiom) after triggering them, before asserting on the result — Sublime's command queue is not synchronous.
- No version bump / no `pyproject.toml` version change and no new git tag for this plan — this is dev/CI tooling only, it doesn't change the shipped package's runtime behavior. Record it under a `## [Unreleased]` / `### Development` heading in `CHANGELOG.md`, matching the precedent already in this file's git history (`v0.5.1..af89b23`).

---

### Task 1: Local Docker runner for `tests_st/`

**Files:**
- Create: `tools/run-st-tests-docker.sh`
- Modify: `.gitignore`

**Interfaces:**
- Produces: an executable script at `tools/run-st-tests-docker.sh` that later tasks' "run it locally" verification steps invoke as `./tools/run-st-tests-docker.sh` (whole suite) or `./tools/run-st-tests-docker.sh --file tests_st/<name>.py` (single file).

- [ ] **Step 1: Add `.cache/` to `.gitignore`**

The script below clones `SublimeText/UnitTesting` into `.cache/UnitTesting/` on first run — that directory must never be committed.

```
__pycache__/
*.pyc
*.pyo
.python-version
.cache/
```

- [ ] **Step 2: Create the runner script**

```bash
#!/usr/bin/env bash
# Runs tests_st/ headlessly against real Sublime Text via Docker, using
# SublimeText/UnitTesting's own docker/ tooling (cloned on demand into a
# gitignored cache dir so this repo doesn't vendor it).
#
# Usage:
#   ./tools/run-st-tests-docker.sh                          # run all of tests_st/
#   ./tools/run-st-tests-docker.sh --file tests_st/test_panel.py
#   ./tools/run-st-tests-docker.sh --refresh-image           # rebuild the docker image
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="$REPO_ROOT/.cache/UnitTesting"

if [ ! -d "$CACHE_DIR/.git" ]; then
  mkdir -p "$(dirname "$CACHE_DIR")"
  git clone --depth 1 https://github.com/SublimeText/UnitTesting.git "$CACHE_DIR"
else
  git -C "$CACHE_DIR" pull --ff-only
fi

PYTHON="$(command -v python3 || command -v python)"
if [ -z "$PYTHON" ]; then
  echo "error: no python3/python interpreter found on PATH" >&2
  exit 1
fi

exec "$PYTHON" "$CACHE_DIR/docker/run_tests.py" "$REPO_ROOT" --package-name SettingsUI "$@"
```

- [ ] **Step 3: Make it executable**

Run: `chmod +x tools/run-st-tests-docker.sh`

- [ ] **Step 4: Verify it clones and reaches the runner (Docker not required to pass this step)**

Run: `./tools/run-st-tests-docker.sh --file tests_st/test_does_not_exist.py`
Expected: it clones `.cache/UnitTesting/` (or pulls if already present), then either runs and fails cleanly because `tests_st/` doesn't exist yet (created in Task 2), or fails with a Docker-daemon-not-found error — either is fine at this step; a `git clone` failure or a Python interpreter error is not.

- [ ] **Step 5: Commit**

```bash
git add tools/run-st-tests-docker.sh .gitignore
git commit -m "chore: add local Docker runner for tests_st"
```

---

### Task 2: Close-listener deadlock regression test (`tests_st/`)

**Files:**
- Create: `tests_st/test_close_listener_deadlock_guard.py`

**Interfaces:**
- Consumes: `SettingsUI.SettingsUI.SettingsUiCloseListener`, `SettingsUI.SettingsUI._closing_window_id` (module-level global), `SettingsUI.lib.panel.NAV_MARK`, `SettingsUI.lib.panel.CONTENT_MARK` — all already exist in the shipped package; this task only adds a test file, no production code changes.

- [ ] **Step 1: Create the test file**

```python
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
```

- [ ] **Step 2: Verify locally (requires Docker)**

Run: `./tools/run-st-tests-docker.sh --file tests_st/test_close_listener_deadlock_guard.py`
Expected: 3 tests pass. If the run hangs instead of completing, re-check the `setUp`/`tearDown` dedicated-second-window pattern above — that exact hang is the Global Constraints failure mode this task exists to avoid.

- [ ] **Step 3: Commit**

```bash
git add tests_st/test_close_listener_deadlock_guard.py
git commit -m "test: add real-ST regression test for settings-ui#3 close deadlock"
```

---

### Task 3: First-run flash-then-crash regression test (`tests_st/`)

**Files:**
- Create: `tests_st/test_new_view_guard.py`

**Interfaces:**
- Consumes: `SettingsUI.SettingsUI.SettingsUiNewViewGuard`, `SettingsUI.lib.panel.NAV_MARK`, `SettingsUI.lib.panel.CONTENT_MARK` — existing production code, unchanged.

- [ ] **Step 1: Create the test file**

```python
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
```

- [ ] **Step 2: Verify locally (requires Docker)**

Run: `./tools/run-st-tests-docker.sh --file tests_st/test_new_view_guard.py`
Expected: 4 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests_st/test_new_view_guard.py
git commit -m "test: add real-ST regression test for first-run flash-then-crash"
```

---

### Task 4: Wire `st-headless` into CI

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: a second, independent CI job `st-headless` alongside the existing `pytest` job. Neither job depends on the other (no `needs:`); both run on every push and pull request.

- [ ] **Step 1: Read the current file to confirm the exact `pytest` job content before editing**

Run: `cat .github/workflows/ci.yml`

- [ ] **Step 2: Add the `st-headless` job**

Append this job alongside the existing `pytest` job (same `jobs:` key, sibling indentation), with `package-name: SettingsUI` on **both** actions from this first commit — this is the Global Constraints failure mode, not something to discover later:

```yaml
  st-headless:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: SublimeText/UnitTesting/actions/setup@v1
        with:
          sublime-text-version: 4
          package-name: SettingsUI
      - uses: SublimeText/UnitTesting/actions/run-tests@v1
        with:
          package-name: SettingsUI
```

- [ ] **Step 3: Validate the YAML parses**

Run: `python3 -c "import yaml, sys; yaml.safe_load(open('.github/workflows/ci.yml'))" 2>&1 || python3 -c "import json,sys; print('yaml module unavailable, skipping local validation')"`
Expected: no exception, or the fallback message if PyYAML isn't installed (fine — the workflow syntax will still be checked by GitHub itself on push).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add st-headless job for the real-ST regression smoke suite"
```

- [ ] **Step 5: Push and watch the Actions run for this branch/PR before merging**

This step can't be verified locally — it needs the actual GitHub Actions environment. Push the branch, open (or update) a PR, and confirm the `st-headless` check goes green. If it hangs, re-check Task 2's `setUp`/`tearDown` window handling first — that was the exact failure mode last time.

---

### Task 5: Document the new tier

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- None (documentation only).

- [ ] **Step 1: Add a "Development" section to `README.md`**

Insert before the `## License` heading:

```markdown
## Development

### Running tests

Pure-logic tests (`tests/`) — no Sublime Text dependency:

```
uv run pytest tests/ -v
```

Real-ST regression tests (`tests_st/`) run against real, headless Sublime Text via
Docker — no local Sublime Text install or license required. This tier only covers
window-lifecycle regressions (open/close crashes) that a hand-rolled `sublime` model
can't faithfully reproduce; it's a smoke suite, not a replacement for `tests/`:

```
./tools/run-st-tests-docker.sh
```

Run a single file with `./tools/run-st-tests-docker.sh --file tests_st/<name>.py`.
The first run clones [`SublimeText/UnitTesting`](https://github.com/SublimeText/UnitTesting)
into a gitignored `.cache/` directory and builds a local Docker image; later runs reuse
a cached Docker volume and are much faster. CI runs the same `tests_st/` suite via
UnitTesting's official GitHub Action instead of Docker — both are entry points to
identical test content.
```

- [ ] **Step 2: Add a CHANGELOG entry**

Insert at the top of `CHANGELOG.md`, above the most recent version heading:

```markdown
## [Unreleased]

### Development
- Added `tests_st/test_close_listener_deadlock_guard.py` and
  `tests_st/test_new_view_guard.py`, a small real-Sublime-Text regression suite
  (via SublimeText/UnitTesting) covering the two window-lifecycle crashes fixed in
  settings-ui#3 and the first-run flash-then-crash — behavior a hand-rolled `sublime`
  fake can't faithfully validate. Runs as its own `st-headless` CI job, separate from
  and not replacing the existing `tests/` pytest suite.
- Added `tools/run-st-tests-docker.sh` so `tests_st/` can be run locally via Docker,
  without a local Sublime Text install or license, matching what CI runs headlessly.
```

- [ ] **Step 3: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: document the real-ST regression smoke suite and Docker runner"
```

---

## Explicitly Out of Scope

- Porting `tests_st/test_panel.py` (pure `panel.get_active_settings_window`/`get_nav_view` logic) — this behavior is adequately covered by `tests/test_panel.py`'s fakes today; a real-ST version would duplicate coverage without validating anything the fakes can't.
- Removing `tests/fakes/`, `tests/test_panel.py`, or `tests/test_settings_ui.py` — explicitly against kaste's literal ask, but this plan trades full compliance for lower risk per the hybrid strategy decision (see Global Constraints and the plan's Architecture section).
- A response comment on `sublimehq/package_control_channel#9459` explaining this hybrid tradeoff to reviewers — draft that separately once this lands and CI is green, not as part of this plan.
