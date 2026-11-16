import unittest

from mac_oui_lookup_kit import OuiTable, normalize_mac


class NormalizeMacTests(unittest.TestCase):
    def test_colon_separated(self):
        self.assertEqual(normalize_mac("00:1a:2b:3c:4d:5e"), "001A2B3C4D5E")

    def test_dash_separated(self):
        self.assertEqual(normalize_mac("00-1A-2B-3C-4D-5E"), "001A2B3C4D5E")

    def test_dotted_cisco_form(self):
        self.assertEqual(normalize_mac("001a.2b3c.4d5e"), "001A2B3C4D5E")

    def test_bare_hex(self):
        self.assertEqual(normalize_mac("001A2B3C4D5E"), "001A2B3C4D5E")

    def test_whitespace_around(self):
        self.assertEqual(normalize_mac("  00:1A:2B:3C:4D:5E  "), "001A2B3C4D5E")

    def test_too_few_digits_raises(self):
        with self.assertRaises(ValueError):
            normalize_mac("00:1A:2B")

    def test_too_many_digits_raises(self):
        with self.assertRaises(ValueError):
            normalize_mac("00:1A:2B:3C:4D:5E:6F")

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            normalize_mac(123456789012)  # type: ignore[arg-type]


class OuiTableTests(unittest.TestCase):
    def setUp(self):
        self.table = OuiTable({
            "00:1A:2B": "Acme Networks",
            "00-1a-2c": "Beta Corp",
            "001A2D": "Gamma LLC",
        })

    def test_lookup_full_mac(self):
        self.assertEqual(self.table.lookup("00:1a:2b:3c:4d:5e"), "Acme Networks")

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(self.table.lookup("00:1A:2C:00:00:00"), "Beta Corp")

    def test_lookup_unknown_returns_none(self):
        self.assertIsNone(self.table.lookup("DE:AD:BE:EF:00:00"))

    def test_lookup_invalid_returns_none(self):
        self.assertIsNone(self.table.lookup("not a mac"))

    def test_lookup_short_prefix_returns_none(self):
        self.assertIsNone(self.table.lookup("00:1A"))

    def test_contains(self):
        self.assertIn("00:1A:2B:00:00:00", self.table)
        self.assertNotIn("FF:FF:FF:00:00:00", self.table)

    def test_contains_non_string_is_false(self):
        self.assertNotIn(12345, self.table)

    def test_len(self):
        self.assertEqual(len(self.table), 3)

    def test_iter_yields_pairs(self):
        pairs = list(self.table)
        self.assertEqual(len(pairs), 3)
        self.assertEqual(pairs[0], ("001A2B", "Acme Networks"))

    def test_constructor_rejects_invalid_prefix(self):
        with self.assertRaises(ValueError):
            OuiTable({"ZZ:ZZ:ZZ": "Bad"})

    def test_constructor_rejects_short_prefix(self):
        with self.assertRaises(ValueError):
            OuiTable({"00:1A": "Too Short"})


class FromLinesTests(unittest.TestCase):
    def test_basic_parsing(self):
        table = OuiTable.from_lines([
            "# comment line",
            "",
            "00:1A:2B\tAcme Networks",
            "00-1A-2C\tBeta Corp",
        ])
        self.assertEqual(len(table), 2)
        self.assertEqual(table.lookup("00:1A:2B:00:00:00"), "Acme Networks")

    def test_line_without_tab_gets_empty_vendor(self):
        table = OuiTable.from_lines(["00:1A:2B"])
        self.assertEqual(table.lookup("00:1A:2B:00:00:00"), "")

    def test_invalid_line_raises(self):
        with self.assertRaises(ValueError):
            OuiTable.from_lines(["00:1A:2B\tAcme", "ZZ"])

    def test_comment_only_lines_ignored(self):
        table = OuiTable.from_lines(["# only a comment", "   "])
        self.assertEqual(len(table), 0)
