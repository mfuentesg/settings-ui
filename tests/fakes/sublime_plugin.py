"""Minimal fake of the `sublime_plugin` module — base classes only."""


class WindowCommand:
    def __init__(self, window=None):
        self.window = window


class TextCommand:
    def __init__(self, view=None):
        self.view = view


class EventListener:
    pass
