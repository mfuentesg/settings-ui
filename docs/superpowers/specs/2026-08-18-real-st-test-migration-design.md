# Real-ST Test Migration & Local Docker Runner Design

**Date:** 2026-08-18
**Status:** Approved

## Problem

`docs/superpowers/specs/2026-08-16-test-coverage-ci-release-design.md` introduced a
three-tier test suite: Tier A (pure-logic pytest), Tier B (pytest against a hand-rolled
fake `sublime`/`sublime_plugin`, `tests/fakes/*`, ~293 lines), and Tier C (real headless
Sublime Text via `SublimeText/UnitTesting`, `tests_st/`, CI-only).

Tier B's fakes reimplement `Window`/`View`/`set_timeout` scheduling by hand. That is
exactly the surface where the project has already been bitten twice by real,
reviewer-caught crashes (`settings-ui#3` and its predecessor) that zero tests caught —
and a hand-rolled model of Sublime Text's behavior can drift from the real thing in the
same way. Tier B and Tier C also duplicate intent: both exercise
`SettingsUiNewViewGuard`/`SettingsUiCloseListener` and `lib/panel.py`'s
view-management functions, one against a fake, one against the real thing.

Separately, Tier C only ever runs in CI (`SublimeText/UnitTesting/actions`) — there is
no documented, reproducible way to run it locally, so a contributor can't verify a
lifecycle-affecting change before pushing.

## Goal

- Remove `tests/fakes/*` and the Tier B tests built on it; re-home their coverage as
  real Tier C tests so lifecycle/event-ordering behavior is verified against actual
  Sublime Text, not a model of it.
- Leave Tier A (`test_schema.py`, `test_state.py`, `test_schema_gen.py`) untouched —
  these have zero `sublime` dependency and gain nothing from running inside ST.
- Give contributors a local, reproducible way to run Tier C headlessly via Docker,
  matching what CI already exercises, without requiring a local Sublime Text license/
  GUI/UnitTesting install.

## Architecture

```
tests/
  conftest.py             ← trimmed: sys.path setup only, no fake registration
  helpers.py               ← removed (only consumer was test_settings_ui.py)
  test_schema_gen.py       ← unchanged (Tier A)
  test_schema.py           ← unchanged (Tier A)
  test_state.py            ← unchanged (Tier A)
  fakes/                   ← removed entirely
  test_panel.py            ← removed (moved to tests_st/)
  test_settings_ui.py      ← removed (moved to tests_st/)

tests_st/
  test_window_lifecycle.py         ← unchanged (existing Tier C)
  test_panel.py                    ← new: real-ST port of the old tests/test_panel.py
  test_new_view_guard.py           ← new: real-ST port of TestNewViewGuard
  test_close_listener_deadlock_guard.py ← new: real-ST port of TestCloseListenerDeadlockGuard

tools/
  run-st-tests-docker.sh   ← new: clones/updates SublimeText/UnitTesting into a
                              gitignored cache dir, then runs its docker/ut-run-tests
                              launcher against this repo with --package-name SettingsUI
```

### Porting Tier B → Tier C

The ported tests keep the same test names, structure, and assertions as their Tier B
originals — only the substrate changes:

- `sublime.Window()` (fake constructor) → `sublime.active_window()` plus
  `window.new_file()` for additional views (real ST always has an active window, even
  headless).
- `sublime.reset()` (fake global-state wipe) → explicit `tearDown()`/`addCleanup` that
  closes every view/window the test created, since real ST state persists across tests.
- Everything else — calling `guard.on_new(v)` / `listener.on_pre_close(nav)` directly,
  asserting on `su._closing_window_id` / `panel._phantom_sets` — works unchanged: these
  are white-box tests calling module functions/methods directly in-process, not
  exercising the async event-dispatch loop, so they need no `yield` delays (unlike
  `test_window_lifecycle.py`, which drives real user-facing commands and therefore does).
- Real `SettingsUI`/`lib.panel` modules are imported the normal way UnitTesting expects
  (the package is already loaded as `SettingsUI` by Sublime Text) rather than through
  `tests/helpers.py`'s synthetic-package shim, which existed only to work around
  pytest's lack of ST's plugin-loader package context.

### Local Docker runner

`tools/run-st-tests-docker.sh`:

1. Clones `SublimeText/UnitTesting` (shallow, pinned to `master`) into
   `.cache/UnitTesting` if not already present there; `git -C .cache/UnitTesting pull`
   otherwise. `.cache/` is added to `.gitignore`.
2. Execs `.cache/UnitTesting/docker/ut-run-tests "$REPO_ROOT" --package-name SettingsUI "$@"`,
   forwarding any extra args (e.g. `--refresh-image`, `--file tests_st/test_panel.py`).
3. `--package-name SettingsUI` is required because the launcher otherwise derives the
   package name from the checkout directory's basename (`settings-ui`), which doesn't
   match the name Sublime Text/Package Control expects (`SettingsUI`, per
   `Main.sublime-menu` and `README.md`).

This uses the `docker/` tooling documented in the `SublimeText/UnitTesting` repo itself
(builds a local `unittesting-local` image, mounts the repo at `/project`, keeps a
`unittesting-home` cache volume so repeat runs skip re-downloading Sublime Text/Package
Control). No new Dockerfile is authored here — this project only adds the thin wrapper
that clones and invokes UnitTesting's own launcher, per the reviewer's suggestion
("install UT via Package Control or clone it to any place").

## CI

**Unchanged.** `.github/workflows/ci.yml`'s `st-headless` job keeps using
`SublimeText/UnitTesting/actions/run-tests@v1` rather than switching to the Docker
launcher. Both run the exact same `tests_st/` suite — the CI action and the local
Docker launcher are two entry points to identical test content, not two different
things being tested. Reasons for not also moving CI onto Docker:

- The official action is already headless real-ST-in-CI (today's ask is "run it
  locally too," which the action alone can't provide).
- The Docker path's main advantage — a persistent `unittesting-home` cache volume that
  skips re-bootstrapping Sublime Text — doesn't carry over to CI's fresh-runner-per-run
  model without extra cache-restore plumbing, so switching would likely make CI slower,
  not faster, for no correctness gain.
- `pytest` job is unaffected either way (Tier A only, no `sublime` dependency).

If CI's action-based approach ever becomes a maintenance problem, switching it to the
same Docker launcher is a small, isolated follow-up — the launcher already exists after
this change.

## Testing

- After the port, run `tools/run-st-tests-docker.sh` and confirm all of
  `tests_st/*.py` passes, including the new files.
- Run `uv run pytest tests/ -v` and confirm Tier A still passes untouched, and that
  removing `tests/fakes/*`/`helpers.py`/`test_panel.py`/`test_settings_ui.py` doesn't
  break any remaining Tier A test's imports (it shouldn't — grep confirms Tier A never
  imports `sublime`, `fakes`, or `helpers`).
- Confirm the ported tests still catch what they were written to catch: check out the
  commit before `settings-ui#3`'s fix and confirm
  `test_close_listener_deadlock_guard.py`'s deadlock-guard test fails there, then
  confirm it passes on current `main` (same meta-check the original spec required for
  the Tier B version, now re-verified against the real thing).

## Out of scope

- Migrating CI itself to the Docker launcher (see above).
- Any change to `tests_st/test_window_lifecycle.py` (already real, already correct).
- Vendoring a copy of `SublimeText/UnitTesting` into this repo — `tools/run-st-tests-docker.sh`
  clones it to a gitignored cache dir on demand instead, so it stays up to date with
  upstream without bloating this repo.
