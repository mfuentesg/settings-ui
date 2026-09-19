import sys
import os

# Note: putting both _root and _root/lib on sys.path means `lib.state`/
# `lib.panel` (imported via `from lib import panel`) and
# `settingsui_pkg.lib.state`/`settingsui_pkg.lib.panel` (imported via
# tests/helpers.py's import_settings_ui(), which loads SettingsUI.py under a
# synthetic package root) are different module objects with independent
# state. Harmless today since nothing relies on shared identity across that
# boundary, but a test mixing both import styles would not see shared state.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "lib"))
sys.path.insert(0, os.path.join(_root, "tests"))

import fakes.sublime as _fake_sublime
import fakes.sublime_plugin as _fake_sublime_plugin

sys.modules.setdefault("sublime", _fake_sublime)
sys.modules.setdefault("sublime_plugin", _fake_sublime_plugin)
