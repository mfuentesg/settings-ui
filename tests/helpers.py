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
