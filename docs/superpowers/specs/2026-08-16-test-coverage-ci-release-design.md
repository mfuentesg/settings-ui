# Test Coverage, CI Pipeline & 0.5.1 Release Design

**Date:** 2026-08-16
**Status:** Approved

## Problem

`sublimehq/package_control_channel#9459` (the Package Control submission) has two
independent reviewer-reported crashes against the settings window (open-crash, then a
close-deadlock) plus explicit reviewer feedback (kaste) that:

1. Only `schema_gen.py`/`schema_loader.py`-adjacent pure logic has test coverage —
   `SettingsUI.py`, `lib/panel.py`, `lib/prefs.py`, `lib/pickers.py`, `lib/renderer.py`
   (all of which import `sublime`/`sublime_plugin` directly and own window/view
   lifecycle) have none.
2. `v0.5.0` is behind `main`'s tip, and CHANGELOG.md documents an `0.5.1` release that
   has no corresponding git tag — Package Control resolves releases from tags
   (`"tags": true` in the channel entry), so this is not just cosmetic.

The close-deadlock was already fixed and merged (`settings-ui#3`, confirmed working by
deathaxe on the channel PR). This spec covers closing the remaining two gaps — test
coverage and versioning — so the fix is both regression-tested and actually installable,
then notifying reviewers.

## Goal

- Real test coverage for the modules that own window/view lifecycle, specifically able
  to catch the class of bug already seen twice (event-listener ordering races, timing
  around `set_timeout`, window close deadlocks).
- CI that runs that coverage on every push/PR so this doesn't regress silently again.
- A tagged `v0.5.1` that matches what CHANGELOG.md already claims, installable via
  Package Control.
- A status update on the channel PR once the above is live.

## Architecture

```
tests/
  fakes/
    sublime.py          ← stateful fake: Window, View, Region, settings(), set_timeout
    sublime_plugin.py    ← fake WindowCommand / EventListener base classes + dispatch
  test_schema_gen.py     ← existing, unchanged
  test_schema.py         ← new (Tier A)
  test_state.py          ← new (Tier A)
  test_panel.py          ← new (Tier B)
  test_settings_ui.py    ← new (Tier B) — command + event-listener orchestration
  conftest.py            ← extended to register fakes in sys.modules before lib import

tests_st/
  test_window_lifecycle.py  ← new (Tier C), runs under SublimeText/UnitTesting

.github/workflows/
  ci.yml                 ← new
```

### Tier A — pure-logic pytest (extends existing suite)

No new infrastructure. Adds coverage for `lib/schema.py` (SECTIONS catalogue shape,
`b/e/n/s/j/pk/rp/lp` constructors) and `lib/state.py` (filter/category get/set), which
have zero external dependencies today and are simply untested by omission.

### Tier B — pytest against fake `sublime`/`sublime_plugin`

`tests/fakes/sublime.py` and `tests/fakes/sublime_plugin.py` are minimal, stateful
stand-ins — not full API surfaces. They model only what `lib/*` and `SettingsUI.py`
actually touch:

- `Window`: `views()`, `id()`, `run_command()` (records calls), `active_view()`.
- `View`: `id()`, `settings()` (a plain dict), `close()`, `file_name()`, `window()`.
- `set_timeout(fn, delay)`: invokes `fn` synchronously by default, so tests can assert
  on ordering; tests that need to assert *deferred* behavior can capture the callback
  instead of auto-invoking.
- `sublime_plugin.WindowCommand` / `EventListener`: plain base classes so the real
  command/listener classes in `SettingsUI.py` and `lib/panel.py` can be imported and
  instantiated directly.
- Event dispatch: tests manually construct the sequence (e.g. call `on_new`, then
  `on_load`, then `on_pre_close` on a listener instance with fake views), which is what
  makes this tier able to reproduce the exact race fixed in `settings-ui#3`
  (`SettingsUiNewViewGuard.on_new`/`on_load` vs `SettingsUiCloseListener.on_pre_close`
  and the `_closing_window_id` global) as a regression test.

`tests/conftest.py` inserts the fakes into `sys.modules['sublime']` /
`sys.modules['sublime_plugin']` before any `lib.*` or `SettingsUI` import happens, so
existing production code needs no test-only branches.

This tier is fast and deterministic but is a model of ST, not ST itself — it can't prove
the absence of real deadlocks, timing bugs, or ST-version-specific behavior.

### Tier C — headless integration via SublimeText/UnitTesting

`tests_st/test_window_lifecycle.py`, written against the
[SublimeText/UnitTesting](https://github.com/SublimeText/UnitTesting) framework (as
kaste suggested): runs inside a real (headless, `xvfb`) Sublime Text 4 instance.

- Runs `settings_ui_open`, asserts the two-pane window and its phantoms exist.
- Closes the window, asserts no exception/deadlock and that both panes and their
  phantoms are gone.
- This is the direct regression test for the two reviewer-reported crashes — it is the
  only tier that exercises the real ST event loop and `set_timeout` scheduler.

## CI pipeline

`.github/workflows/ci.yml`, triggered on `push` and `pull_request`:

- **`pytest` job**: `ubuntu-latest`, Python 3.8 (matches ST4's bundled interpreter),
  installs dev deps (`uv sync` — already used locally per `uv.lock`), runs
  `pytest tests/` (Tiers A+B).
- **`st-headless` job**: `ubuntu-latest` + `xvfb`, sets up ST4 stable via
  SublimeText/UnitTesting's documented GitHub Actions pattern, runs `tests_st/`
  (Tier C).

Both jobs must pass before the PR can be considered ready to merge/tag.

## Versioning

1. Confirm/fill in the existing `## [0.5.1]` CHANGELOG.md entry so it accurately
   describes the `settings-ui#3` fix (close-deadlock / `on_new`/`on_load` race) in
   addition to whatever it already lists.
2. Bump `pyproject.toml` `version` from the stale `0.1.0` to `0.5.1` (dev-only metadata,
   unused by Package Control, but currently inconsistent with CHANGELOG/tags — a one-line
   fix bundled with this work rather than a separate effort).
3. Once the CI workflow above is green on `main`, tag `v0.5.1` and push the tag.

## Channel PR follow-up

After `v0.5.1` is tagged and pushed, post one comment on
`sublimehq/package_control_channel#9459` summarizing: the close-deadlock fix is merged,
test coverage now exists for the window/view lifecycle code (unit-level via fakes +
integration-level via headless ST), CI runs both on every push, and `v0.5.1` is tagged
and installable. Invite braver/kaste/deathaxe to re-verify.

## Testing

This spec's own deliverable *is* the test suite; there's no separate testing section
beyond what's described above. The one meta-check: after Tier B/C are written, verify
they actually fail against the pre-`settings-ui#3` code (e.g. by checking out `main`
before that merge) to confirm they're not vacuously passing — then confirm they pass on
current `main`.

## Out of scope

- Rewriting `tests/fakes/*` into a general-purpose ST mocking library for other
  projects — it stays minimal and scoped to what this plugin uses.
- Broader lint/type-checking CI jobs — not requested, not blocking the channel PR.
- Any change to the `package_control_channel` repo itself — the `s.json` entry
  (`"tags": true`) is already correct; only a comment is needed there.
