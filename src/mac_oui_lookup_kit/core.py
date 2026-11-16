"""Core lookup logic for mac_oui_lookup_kit.

The library keeps a single flat dictionary keyed by the 6-hex-digit OUI
(the first three octets of a MAC address, no separators). That is the
smallest representation we can store while still being fast to build from
a text table and fast to query. A trie would be faster for prefix walks,
but OUI lookups are exact 24-bit matches, so a dict is the right shape.

A deliberate decision: we do NOT validate that a MAC address is a
"real" unicast address. The table may legitimately contain multicast or
locally-administered OUIs (some vendors ship them), and rejecting them
would surprise callers who just want to map a prefix to a name. We only
require that the input contains at least six hex digits after stripping
separators.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, Iterator, Mapping, Optional, Tuple

__all__ = ["OuiTable", "normalize_mac"]

# Matches any run of hex digits. We use this to strip separators without
# enumerating every possible separator (':', '-', '.', whitespace, ...).
_HEX_RUN = re.compile(r"[0-9A-Fa-f]+")


def normalize_mac(value: str) -> str:
    """Return the canonical 12-hex-digit form of a MAC address.

    The function uppercases the result so that lookups against a table
    built from uppercase keys are case-insensitive. It strips every
    non-hex character, so ``"00:1A:2B:3C:4D:5E"``, ``"00-1a-2b-3c-4d-5e"``
    and ``"001a.2b3c.4d5e"`` all collapse to ``"001A2B3C4D5E"``.

    Raises ``ValueError`` if the input does not contain exactly twelve
    hex digits. We require exactly twelve because a MAC address is
    always six octets; accepting shorter strings would silently turn a
    user-supplied prefix like ``"00:1A"`` into a full MAC and produce a
    confusing lookup miss.
    """
    if not isinstance(value, str):
        raise TypeError("MAC address must be a string")
    hex_digits = "".join(_HEX_RUN.findall(value))
    if len(hex_digits) != 12:
        raise ValueError(
            f"expected 12 hex digits in MAC address, got {len(hex_digits)}"
        )
    return hex_digits.upper()


class OuiTable:
    """A lookup table mapping OUI prefixes to vendor names.

    The table is immutable from the caller's perspective: entries are
    added through the constructor or through :meth:`from_lines`, and
    there is no public mutation API. That keeps lookups thread-safe
    without locks, which matters because OUI lookups are often done
    from worker threads in network scanners.
    """

    __slots__ = ("_entries",)

    def __init__(self, entries: Optional[Mapping[str, str]] = None) -> None:
        """Build a table from a mapping of OUI prefix to vendor name.

        Keys may be given in any of the usual MAC forms; they are
        normalized with :func:`normalize_mac` and only the first six
        hex digits are kept. Values are stored verbatim.
        """
        table: Dict[str, str] = {}
        if entries:
            for prefix, vendor in entries.items():
                key = _oui_key(prefix)
                if key is None:
                    raise ValueError(f"invalid OUI prefix: {prefix!r}")
                table[key] = vendor
        self._entries = table

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> "OuiTable":
        """Build a table from an iterable of ``PREFIX<TAB>VENDOR`` lines.

        Blank lines and lines beginning with ``#`` are ignored. A line
        without a tab is treated as a prefix with an empty vendor name
        rather than an error, because the IEEE OUI file occasionally
        ships entries whose vendor field is empty and callers should not
        have to special-case that.
        """
        table: Dict[str, str] = {}
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" in line:
                prefix, vendor = line.split("\t", 1)
            else:
                prefix, vendor = line, ""
            key = _oui_key(prefix)
            if key is None:
                raise ValueError(f"invalid OUI prefix on line: {raw!r}")
            table[key] = vendor.strip()
        return cls(table)

    def lookup(self, mac: str) -> Optional[str]:
        """Return the vendor for ``mac``, or ``None`` if unknown.

        The argument may be a full MAC address in any common format.
        Only the first three octets are used.
        """
        key = _oui_key(mac)
        if key is None:
            return None
        return self._entries.get(key)

    def __contains__(self, mac: object) -> bool:
        if not isinstance(mac, str):
            return False
        key = _oui_key(mac)
        return key is not None and key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[Tuple[str, str]]:
        """Iterate over ``(oui, vendor)`` pairs in insertion order."""
        return iter(self._entries.items())

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"OuiTable({len(self._entries)} entries)"


def _oui_key(value: str) -> Optional[str]:
    """Extract the 6-hex-digit OUI key from a MAC-like string.

    Returns ``None`` when the input does not contain at least six hex
    digits. We accept strings longer than six digits because a full MAC
    address is the common input, and we accept shorter-than-six only
    when the caller is explicitly building a table from a prefix (which
    is why this helper does not enforce twelve digits the way
    :func:`normalize_mac` does).
    """
    if not isinstance(value, str):
        return None
    digits = "".join(_HEX_RUN.findall(value))
    if len(digits) < 6:
        return None
    return digits[:6].upper()
