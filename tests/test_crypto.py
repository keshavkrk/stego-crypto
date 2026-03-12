"""
Tests for CryptoManager — encryption/decryption with random salts.
"""
import pytest
from core.crypto_manager import CryptoManager, SALT_LENGTH


@pytest.fixture
def crypto():
    return CryptoManager()


class TestEncryptDecrypt:
    def test_round_trip(self, crypto):
        """Encrypt then decrypt should return original data."""
        original = b"Hello, SecureGuard! This is a test payload."
        password = "test_password_123"

        encrypted = crypto.encrypt(original, password)
        decrypted = crypto.decrypt(encrypted, password)

        assert decrypted == original

    def test_round_trip_string_input(self, crypto):
        """String input should be auto-converted to bytes."""
        original = "This is a string, not bytes."
        password = "pass"

        encrypted = crypto.encrypt(original, password)
        decrypted = crypto.decrypt(encrypted, password)

        assert decrypted == original.encode()

    def test_round_trip_empty(self, crypto):
        """Empty data should encrypt and decrypt correctly."""
        encrypted = crypto.encrypt(b"", "pwd")
        decrypted = crypto.decrypt(encrypted, "pwd")
        assert decrypted == b""

    def test_round_trip_large_data(self, crypto):
        """Test with a larger payload (~1 MB)."""
        original = b"X" * (1024 * 1024)
        encrypted = crypto.encrypt(original, "big_password")
        decrypted = crypto.decrypt(encrypted, "big_password")
        assert decrypted == original

    def test_wrong_password_fails(self, crypto):
        """Decrypting with the wrong password should raise ValueError."""
        encrypted = crypto.encrypt(b"secret", "correct_password")

        with pytest.raises(ValueError, match="Invalid password"):
            crypto.decrypt(encrypted, "wrong_password")

    def test_unique_salts(self, crypto):
        """Two encryptions of the same data with the same password should produce different ciphertexts."""
        data = b"same data"
        password = "same_password"

        enc1 = crypto.encrypt(data, password)
        enc2 = crypto.encrypt(data, password)

        # The salt (first 16 bytes) should be different
        assert enc1[:SALT_LENGTH] != enc2[:SALT_LENGTH]

        # The full ciphertext should be different
        assert enc1 != enc2

        # But both should decrypt to the same value
        assert crypto.decrypt(enc1, password) == data
        assert crypto.decrypt(enc2, password) == data

    def test_corrupted_data_fails(self, crypto):
        """Tampered ciphertext should raise ValueError."""
        encrypted = crypto.encrypt(b"data", "pwd")

        # Corrupt a byte in the middle of the ciphertext
        corrupted = bytearray(encrypted)
        corrupted[SALT_LENGTH + 10] ^= 0xFF  # Flip bits
        corrupted = bytes(corrupted)

        with pytest.raises(ValueError):
            crypto.decrypt(corrupted, "pwd")

    def test_too_short_data_fails(self, crypto):
        """Data shorter than the salt should raise ValueError."""
        with pytest.raises(ValueError, match="too short"):
            crypto.decrypt(b"short", "pwd")
