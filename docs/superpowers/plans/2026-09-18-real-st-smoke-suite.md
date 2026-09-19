# Real-ST Regression Smoke Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-Sublime-Text regression coverage for the one window-lifecycle crash (`settings-ui#3`'s close-deadlock is already covered — the first-run flash-then-crash is not) that the existing `tests/` fake-`sublime` suite structurally cannot validate — without touching the existing fast pytest suite, and without repeating the specific test-design bug that broke the reverted attempt.

**Architecture:** Two independent test tiers stay independent. `tests/` (pytest + `tests/fakes/`) remains the primary, fast, deterministic CI gate for pure logic (schema/prefs/state/panel helpers) — untouched by this plan. `tests_st/`, run via [SublimeText/UnitTesting](https://github.com/SublimeText/UnitTesting), already exists (`test_window_lifecycle.py`, predates `v0.5.1`, currently green in CI) and covers open/close/reopen lifecycle by driving the plugin through its real commands. This plan adds exactly one more file to that tier, `test_new_view_guard.py`, using the same real-dispatch style — no test in either file instantiates an `EventListener` subclass directly.

**Tech Stack:** pytest (existing tier, unchanged), SublimeText/UnitTesting (headless real-ST test runner + GitHub Action, already wired into CI), Docker (local reproduction of the CI runner).

**Spec:** This plan supersedes the reverted `docs/superpowers/plans/2026-08-18-real-st-test-migration.md` / `docs/superpowers/specs/2026-08-18-real-st-test-migration-design.md` (deleted by the `af89b23`→`v0.5.1` revert). That attempt's final commit never actually passed CI (verified: run `32196255209`, 5 failures) — this plan diagnoses those specific failures and designs around their root causes instead of re-attempting the same code (see Global Constraints and Explicitly Out of Scope).

## Global Constraints

- Do **not** delete or modify `tests/fakes/`, `tests/test_panel.py`, `tests/test_settings_ui.py`, or `tests_st/test_window_lifecycle.py`. This plan only adds one new file.
- **Never instantiate `SettingsUiCloseListener` or `SettingsUiNewViewGuard` directly inside a `tests_st/` test and call its methods.** Sublime's real plugin host already runs its own live instance of every registered `EventListener` for the package under test. A second, test-created instance calling the same methods races against that live instance over shared module state (`SettingsUiCloseListener._closing_window_id` is the concrete case that broke the reverted attempt: `AssertionError: None != 3`, because the live instance's real `on_close` reset the global out from under the test's manually-driven instance mid-assertion-wait). Always drive behavior through real commands and real view/window mutations (`window.new_file()`, `view.close()`, `window.run_command(...)`), and assert only on observable outcomes (`view.is_valid()`, `view in window.views()`, mark settings) — exactly what `tests_st/test_window_lifecycle.py` already does successfully.
- Any assertion on the result of an action that the plugin performs asynchronously (`sublime.set_timeout(fn, 0)` is used throughout `SettingsUI.py` for exactly this reason — to avoid nesting commands inside their own event callbacks) must `yield <milliseconds>` first. `DeferrableTestCase` also accepts `yield <predicate-callable>` to poll until a condition is true instead of a fixed delay. Missing this yield was the *only* defect in the reverted attempt's `test_new_view_guard.py` (verified in CI log: `AssertionError: True is not false` on an assertion made immediately after the triggering action, no wait).
- `tests_st/` files should use the literal setting-key strings (`"settings_ui_nav"`, `"settings_ui_content"`) the way `test_window_lifecycle.py` already does, rather than `from SettingsUI.lib import panel` — this keeps the new test decoupled from the package-name/import-path concern entirely (see Task 2).
- No version bump / no `pyproject.toml` version change and no new git tag for this plan — dev/CI tooling only. Record it under a `## [Unreleased]` / `### Development` heading in `CHANGELOG.md`, matching the precedent in this file's git history (`v0.5.1..af89b23`).

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
#   ./tools/run-st-tests-docker.sh --file tests_st/test_window_lifecycle.py
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

Run: `./tools/run-st-tests-docker.sh --file tests_st/test_window_lifecycle.py`
Expected: it clones `.cache/UnitTesting/` (or pulls if already present), then either runs the 3 existing `test_window_lifecycle.py` tests (if Docker is available) or fails with a Docker-daemon-not-found error — either is fine at this step; a `git clone` failure or a Python interpreter error is not. If Docker is available, this also re-confirms the existing suite still passes before Task 2 adds to it.

- [ ] **Step 5: Commit**

```bash
git add tools/run-st-tests-docker.sh .gitignore
git commit -m "chore: add local Docker runner for tests_st"
```

---

### Task 2: First-run flash-then-crash regression test (`tests_st/`)

**Files:**
- Create: `tests_st/test_new_view_guard.py`

**Ground truth this task's design is based on:** the reverted attempt had this exact scenario, and it failed in CI with `AssertionError: True is not false` on `test_closes_stray_view_opened_in_settings_window` — because `SettingsUiNewViewGuard.on_new()` schedules its close via `sublime.set_timeout(view.close, 0)` (async) and the test asserted `stray.is_valid()` immediately after triggering it. This version fixes that missing `yield`, and additionally never instantiates `SettingsUiNewViewGuard` directly — it relies entirely on the live instance Sublime's plugin host already runs for this package, driven through real `window.new_file()`/`.close()`/`.open_file()` calls, matching `tests_st/test_window_lifecycle.py`'s proven style. This also means it needs no `import SettingsUI.SettingsUI` and is unaffected by whether Task 3's `package-name` fix has landed yet.

**Interfaces:**
- None consumed directly — this test observes the real, already-registered `SettingsUiNewViewGuard` listener's effect on real views, using the literal setting keys `"settings_ui_nav"` / `"settings_ui_content"` (same values as `SettingsUI/lib/panel.py`'s `NAV_MARK`/`CONTENT_MARK`, and the same strings `test_window_lifecycle.py` already uses).

- [ ] **Step 1: Create the test file**

```python
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
    live one over shared state in the sibling close-listener case)."""

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
Expected: 4 tests pass. If `test_closes_stray_view_opened_in_settings_window` fails with `stray.is_valid()` still `True`, the `yield 300` isn't giving the async close enough time — this is the exact failure mode this task exists to fix, don't remove the yield, increase it instead.

- [ ] **Step 3: Run the full `tests_st/` suite together to confirm no interaction with `test_window_lifecycle.py`**

Run: `./tools/run-st-tests-docker.sh`
Expected: 7 tests pass (3 from `test_window_lifecycle.py`, 4 from this file).

- [ ] **Step 4: Commit**

```bash
git add tests_st/test_new_view_guard.py
git commit -m "test: add real-ST regression test for first-run flash-then-crash"
```

---

### Task 3: Pin `package-name` on the existing `st-headless` CI job

**Files:**
- Modify: `.github/workflows/ci.yml`

**Ground truth (verified against the live repo, not assumed):** the `st-headless` job already exists in `.github/workflows/ci.yml` and is currently green (confirmed via `gh run view` on the latest `main` push: `test_window_lifecycle.py`'s 3 tests run and pass today). It has no `package-name` input, so UnitTesting derives the package folder name from the GitHub repo (`settings-ui`) rather than `SettingsUI`. This doesn't currently break anything — `test_window_lifecycle.py` and Task 2's new file both use command names and setting-key strings, never `import SettingsUI.*` — but it's a latent bug for any future test that does, since that import will `ModuleNotFoundError` in exactly that case. This task is a hygiene fix, not a fix for a currently-broken thing, and is independent of Task 2 (order doesn't matter). Do **not** add a new `st-headless:` job block; the job already exists — this only edits its two `with:` blocks.

**Interfaces:**
- Modifies the existing `st-headless` job's two `SublimeText/UnitTesting/actions/*` steps in place. `pytest` job untouched.

- [ ] **Step 1: Read the current file to confirm the exact `st-headless` job content before editing**

Run: `cat .github/workflows/ci.yml`
Expected: a `jobs:` block with two existing jobs, `pytest` and `st-headless`; the `st-headless` job's two `SublimeText/UnitTesting/actions/*` steps currently have no `with: package-name:` at all.

- [ ] **Step 2: Add `package-name: SettingsUI` to both `st-headless` steps**

Edit the existing `st-headless` job (do not duplicate it) so it reads:

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

Run: `python3 -c "import yaml, sys; yaml.safe_load(open('.github/workflows/ci.yml'))" 2>&1 || echo "yaml module unavailable, skipping local validation (GitHub will still validate on push)"`
Expected: no exception, or the fallback message.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: pin st-headless job's package-name to SettingsUI"
```

- [ ] **Step 5: Push and watch the Actions run before merging**

This step can't be verified locally — it needs the actual GitHub Actions environment. Push the branch, open (or update) a PR, and confirm both `pytest` and `st-headless` checks go green (7 tests in `st-headless`, per Task 2 Step 3).

---

### Task 4: Document the new test and its history

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
can't faithfully reproduce; it's a smoke suite, not a replacement for `tests/`, and
every test in it drives the plugin through real commands and real view/window
mutations rather than calling listener classes directly:

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
- Added `tests_st/test_new_view_guard.py`, a real-Sublime-Text regression test (via
  SublimeText/UnitTesting) for the first-run flash-then-crash — behavior a hand-rolled
  `sublime` fake can't faithfully validate. It drives the plugin's real, already-registered
  event listener through real view/window operations rather than instantiating the
  listener class directly (the settings-ui#3 close-deadlock regression already has this
  kind of coverage via the existing `tests_st/test_window_lifecycle.py`)
- Added `tools/run-st-tests-docker.sh` so `tests_st/` can be run locally via Docker,
  without a local Sublime Text install or license, matching what CI runs headlessly
- Pinned the `st-headless` CI job's `package-name` to `SettingsUI`, matching the actual
  package name (`Main.sublime-menu`/README/Package Control), instead of the name
  UnitTesting would otherwise derive from the GitHub repo name (`settings-ui`)
```

- [ ] **Step 3: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: document the real-ST regression smoke suite and Docker runner"
```

---

## Explicitly Out of Scope

- **Re-adding `tests_st/test_close_listener_deadlock_guard.py`.** The reverted attempt's version of this file failed in CI (`AssertionError: None != 3`) because it instantiated a second `SettingsUiCloseListener` that raced the real, live-registered one over the shared `_closing_window_id` module global. The regression it targeted (settings-ui#3) is already covered by the existing, currently-passing `tests_st/test_window_lifecycle.py::test_close_does_not_deadlock_or_crash`, which drives the same scenario through real commands instead. No replacement test is needed.
- **Re-adding a real-ST port of `tests_st/test_panel.py`.** The reverted attempt's version also failed in CI (3 failures, all `assertIs` identity checks on `sublime.Window(id)`/`sublime.View(id)` wrapper objects — real ST constructs a new wrapper per call even for the same underlying window/view, so `is` comparisons that work against fakes don't hold against the real API). `panel.get_active_settings_window()`/`get_nav_view()`'s pure logic is already covered by `tests/test_panel.py`'s fakes; a real-ST version would need redesigning around value-based comparison (`.id()` equality, not `is`) to be worth adding, and doesn't validate anything the fakes structurally can't — same reasoning as the original hybrid-strategy decision.
- Removing `tests/fakes/`, `tests/test_panel.py`, or `tests/test_settings_ui.py` — explicitly against kaste's literal ask on package_control_channel#9459, but this plan trades full compliance for lower risk per the hybrid strategy decision.
- A response comment on `sublimehq/package_control_channel#9459` explaining this hybrid tradeoff to reviewers — draft that separately once this lands and CI is green, not as part of this plan.
