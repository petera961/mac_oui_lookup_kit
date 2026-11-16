"""Public API for mac_oui_lookup_kit.

Only `OuiTable` and `normalize_mac` are exported. Everything else is an
implementation detail and may change without notice.
"""

from .core import OuiTable, normalize_mac

__all__ = ["OuiTable", "normalize_mac"]
