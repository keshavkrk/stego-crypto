"""
Tests for PIIDetector — regex-based PII pattern matching.
"""
import pytest
from core.pii_detector import PIIDetector


@pytest.fixture
def detector():
    return PIIDetector()


class TestAadhaar:
    def test_aadhaar_with_spaces(self, detector):
        results = detector.detect("My Aadhaar is 1234 5678 9012")
        types = [r["type"] for r in results]
        assert "Aadhaar Number" in types

    def test_aadhaar_no_spaces(self, detector):
        results = detector.detect("Aadhaar: 123456789012")
        types = [r["type"] for r in results]
        assert "Aadhaar Number" in types

    def test_aadhaar_with_dashes(self, detector):
        results = detector.detect("ID: 1234-5678-9012")
        types = [r["type"] for r in results]
        assert "Aadhaar Number" in types


class TestPAN:
    def test_valid_pan(self, detector):
        results = detector.detect("PAN: ABCDE1234F")
        types = [r["type"] for r in results]
        assert "PAN Card" in types

    def test_lowercase_pan_should_not_match(self, detector):
        results = detector.detect("PAN: abcde1234f")
        types = [r["type"] for r in results]
        assert "PAN Card" not in types


class TestPhone:
    def test_indian_phone_10_digit(self, detector):
        results = detector.detect("Call me at 9876543210")
        types = [r["type"] for r in results]
        assert "Indian Phone" in types

    def test_indian_phone_with_country_code(self, detector):
        results = detector.detect("Phone: +91-9876543210")
        types = [r["type"] for r in results]
        assert "Indian Phone" in types

    def test_invalid_phone_starting_digit(self, detector):
        """Indian mobile numbers start with 6-9."""
        results = detector.detect("Number: 1234567890")
        phone_results = [r for r in results if r["type"] == "Indian Phone"]
        assert len(phone_results) == 0


class TestEmail:
    def test_valid_email(self, detector):
        results = detector.detect("Contact: user@example.com")
        types = [r["type"] for r in results]
        assert "Email Address" in types

    def test_email_with_plus(self, detector):
        results = detector.detect("Mail: user+tag@company.co.in")
        types = [r["type"] for r in results]
        assert "Email Address" in types


class TestCreditCard:
    def test_valid_visa(self, detector):
        # 4111 1111 1111 1111 is a well-known Visa test number (passes Luhn)
        results = detector.detect("Card: 4111 1111 1111 1111")
        types = [r["type"] for r in results]
        assert "Credit Card" in types

    def test_invalid_luhn_should_not_match(self, detector):
        results = detector.detect("Card: 1234 5678 9012 3456")
        cc_results = [r for r in results if r["type"] == "Credit Card"]
        assert len(cc_results) == 0


class TestDates:
    def test_dd_mm_yyyy(self, detector):
        results = detector.detect("DOB: 15/08/1947")
        types = [r["type"] for r in results]
        assert any("Date" in t for t in types)

    def test_yyyy_mm_dd(self, detector):
        results = detector.detect("Date: 2024-02-28")
        types = [r["type"] for r in results]
        assert any("Date" in t for t in types)


class TestNoMatch:
    def test_empty_string(self, detector):
        results = detector.detect("")
        assert results == []

    def test_plain_text(self, detector):
        results = detector.detect("Hello, this is just a normal sentence.")
        # Should have no high-severity matches
        high = [r for r in results if r["severity"] == "high"]
        assert len(high) == 0

    def test_single_word(self, detector):
        result = detector.detect_in_word("hello")
        assert result is None


class TestDetectInWord:
    def test_email_word(self, detector):
        result = detector.detect_in_word("user@example.com")
        assert result == "Email Address"

    def test_pan_word(self, detector):
        result = detector.detect_in_word("ABCDE1234F")
        assert result == "PAN Card"
