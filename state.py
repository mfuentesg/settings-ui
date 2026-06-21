"""
Shared mutable UI state.

Kept in its own module so both `renderer` (which reads these to build HTML)
and `panel` (which writes them on user interactions) can import it without
creating a circular dependency.
"""

# Active search filter string, lower-cased.  Empty string means "no filter".
_filter: str = ""

# Index into SECTIONS of the currently highlighted nav item.
_category: int = 0
