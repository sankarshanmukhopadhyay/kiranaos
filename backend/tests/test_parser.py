"""
Unit tests for the order text parser.
No database, no HTTP — pure function tests.
"""

import pytest

from app.services.parser import ParsedItem, parse_order_text


class TestParseOrderText:

    def test_simple_comma_list(self):
        items = parse_order_text("2 kg atta, 1 l oil, bread")
        names = [i.name for i in items]
        assert "Atta" in names
        assert "Oil" in names
        assert "Bread" in names

    def test_quantity_and_unit_extracted(self):
        items = parse_order_text("5 kg rice")
        assert len(items) == 1
        assert items[0].quantity == 5.0
        assert items[0].unit == "kg"

    def test_newline_delimited_list(self):
        items = parse_order_text("atta\ndal\ndahi\ntamatar")
        assert len(items) == 4

    def test_semicolon_delimited(self):
        items = parse_order_text("soap; shampoo; toothpaste")
        assert len(items) == 3

    def test_hinglish_filler_words_stripped(self):
        items = parse_order_text("bhaiya atta chahiye, doodh bhi dena")
        # Filler words should not appear as item names
        names_lower = [i.name.lower() for i in items]
        assert "bhaiya" not in names_lower
        assert "chahiye" not in names_lower

    def test_high_confidence_when_qty_present(self):
        items = parse_order_text("2 kg sugar")
        assert items[0].confidence == pytest.approx(0.85)

    def test_low_confidence_when_no_qty(self):
        items = parse_order_text("bread")
        assert items[0].confidence == pytest.approx(0.65)

    def test_deduplication(self):
        items = parse_order_text("atta, atta, doodh")
        names_lower = [i.name.lower() for i in items]
        assert names_lower.count("atta") == 1

    def test_none_returns_empty(self):
        assert parse_order_text(None) == []

    def test_empty_string_returns_empty(self):
        assert parse_order_text("") == []
        assert parse_order_text("   ") == []

    def test_non_order_text_minimal_items(self):
        # "bhaiya order aaya kya?" should not parse as grocery items
        items = parse_order_text("bhaiya order aaya kya?")
        assert len(items) < 2

    def test_unit_aliases_normalised(self):
        items = parse_order_text("2 ltr oil")
        assert items[0].unit == "l"

    def test_mixed_format(self):
        """Real-world message format: quantity before and after item name."""
        items = parse_order_text("rice 5 kg\n1 packet tea\nsoap")
        assert len(items) == 3

    def test_first_letter_capitalised(self):
        items = parse_order_text("atta")
        assert items[0].name[0].isupper()

    def test_returns_list_of_parsed_item(self):
        items = parse_order_text("milk")
        assert isinstance(items[0], ParsedItem)
