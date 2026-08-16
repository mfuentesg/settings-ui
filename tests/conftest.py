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
