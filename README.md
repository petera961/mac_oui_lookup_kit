# mac_oui_lookup_kit

Match MAC address prefixes against an embedded or user-supplied OUI vendor mapping table.

```python
from mac_oui_lookup_kit import OuiTable, normalize_mac

# Build a table from an iterable of "PREFIX<TAB>VENDOR" lines.
table = OuiTable.from_lines([
    "00:1A:2B\tAcme Networks",
    "00-1A-2C\tBeta Corp",
])

assert table.lookup("00:1a:2b:3c:4d:5e") == "Acme Networks"
assert table.lookup("00:1a:2c:00:00:00") == "Beta Corp"
assert table.lookup("ff:ff:ff:ff:ff:ff") is None

# Or build one directly from a mapping.
table = OuiTable({"001A2D": "Gamma LLC"})
assert table.lookup("00:1A:2D:00:00:00") == "Gamma LLC"

# normalize_mac is exported so callers can canonicalise input themselves.
assert normalize_mac("001a.2b3c.4d5e") == "001A2B3C4D5E"
```

## Why this exists

The IEEE publishes an OUI file that is large, tab-separated, and full of
entries whose vendor field is empty. Network scanners usually need only
the first three octets of a MAC address, and they need that lookup to be
fast and thread-safe. This library stores the table as a single flat
dictionary keyed by the six-hex-digit OUI, so a lookup is one hash and
one string comparison. That is deliberately less flexible than a trie
(which would support arbitrary-length prefixes) because OUI lookups are
always exactly 24 bits. The trade-off is that the table is immutable:
adding entries after construction would require locking, and the common
case is a table loaded once at startup.

## The awkward edge

`lookup` returns `None` for both an unknown OUI and an input that does
not contain at least six hex digits. There is no way to distinguish
"this MAC is malformed" from "this vendor is not in the table" through
the return value alone. That is intentional: callers who care about
malformed input should call `normalize_mac` first, which raises
`ValueError` for anything that is not exactly twelve hex digits.
