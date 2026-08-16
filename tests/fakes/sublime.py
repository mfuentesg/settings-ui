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
