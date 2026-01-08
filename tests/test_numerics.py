"""
Tests for numeric parsing utilities
"""
import pytest
from decimal import Decimal

from app.utils.numerics import parse_financial_value, is_numeric_string


class TestParseFinancialValue:
    """Test parse_financial_value function"""
    
    def test_simple_integer(self):
        """Test simple integer parsing"""
        assert parse_financial_value("1234") == Decimal("1234")
    
    def test_with_commas(self):
        """Test parsing numbers with comma separators"""
        assert parse_financial_value("1,234,567") == Decimal("1234567")
    
    def test_negative(self):
        """Test negative number parsing"""
        assert parse_financial_value("-1234") == Decimal("-1234")
    
    def test_decimal(self):
        """Test decimal number parsing"""
        assert parse_financial_value("123.45") == Decimal("123.45")
    
    def test_negative_with_commas_and_decimal(self):
        """Test complex number with negative sign, commas, and decimal"""
        assert parse_financial_value("-1,234.56") == Decimal("-1234.56")
    
    def test_none_input(self):
        """Test None input returns None"""
        assert parse_financial_value(None) is None
    
    def test_empty_string(self):
        """Test empty string returns None"""
        assert parse_financial_value("") is None
    
    def test_half_width_dash(self):
        """Test half-width dash returns None"""
        assert parse_financial_value("-") is None
    
    def test_full_width_dash(self):
        """Test full-width dash returns None"""
        assert parse_financial_value("—") is None
    
    def test_whitespace_only(self):
        """Test whitespace-only string returns None"""
        assert parse_financial_value("   ") is None
    
    def test_whitespace_around_number(self):
        """Test number with surrounding whitespace"""
        assert parse_financial_value("  1234  ") == Decimal("1234")
    
    def test_invalid_string(self):
        """Test invalid string returns None"""
        assert parse_financial_value("abc") is None
    
    def test_mixed_invalid(self):
        """Test mixed valid/invalid string returns None"""
        assert parse_financial_value("12abc34") is None
    
    def test_large_number(self):
        """Test large financial number"""
        assert parse_financial_value("123,456,789,012") == Decimal("123456789012")
    
    def test_zero(self):
        """Test zero value"""
        assert parse_financial_value("0") == Decimal("0")
    
    def test_negative_decimal(self):
        """Test negative decimal number"""
        assert parse_financial_value("-0.5") == Decimal("-0.5")


class TestIsNumericString:
    """Test is_numeric_string function"""
    
    def test_valid_integer(self):
        """Test valid integer string"""
        assert is_numeric_string("1234") is True
    
    def test_valid_with_commas(self):
        """Test valid number with commas"""
        assert is_numeric_string("1,234,567") is True
    
    def test_valid_negative(self):
        """Test valid negative number"""
        assert is_numeric_string("-1234") is True
    
    def test_valid_decimal(self):
        """Test valid decimal number"""
        assert is_numeric_string("123.45") is True
    
    def test_valid_complex(self):
        """Test valid complex number"""
        assert is_numeric_string("-1,234.56") is True
    
    def test_invalid_none(self):
        """Test None input returns False"""
        assert is_numeric_string(None) is False
    
    def test_invalid_empty(self):
        """Test empty string returns False"""
        assert is_numeric_string("") is False
    
    def test_invalid_dash(self):
        """Test dash-only returns False"""
        assert is_numeric_string("-") is False
    
    def test_invalid_text(self):
        """Test text string returns False"""
        assert is_numeric_string("abc") is False
    
    def test_invalid_multiple_decimals(self):
        """Test multiple decimal points returns False"""
        assert is_numeric_string("1.2.3") is False
