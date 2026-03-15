"""
Crypto Manager — Handles encryption/decryption with proper key derivation.
Uses Fernet (AES-128-CBC) with PBKDF2-HMAC-SHA256 and random salts.
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Salt length in bytes
SALT_LENGTH = 16

# OWASP 2024 recommendation for PBKDF2-SHA256
PBKDF2_ITERATIONS = 480_000


class CryptoManager:
    """Encrypts and decrypts data using password-derived keys with random salts."""

    def _derive_key(self, password, salt):
        """Derive a Fernet-compatible key from a password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt(self, data, password):
        """
        Encrypt data with a password. A random salt is generated and
        prepended to the output so decryption can recover it.

        Args:
            data: bytes or str to encrypt.
            password: User-provided password string.

        Returns:
            bytes: salt (16 bytes) + encrypted ciphertext.
        """
        if isinstance(data, str):
            data = data.encode()

        salt = os.urandom(SALT_LENGTH)
        key = self._derive_key(password, salt)
        f = Fernet(key)
        encrypted = f.encrypt(data)

        # Prepend salt so we can recover it during decryption
        return salt + encrypted

    def decrypt(self, encrypted_data, password):
        """
        Decrypt data that was encrypted with encrypt().
        Reads the salt from the first 16 bytes.

        Args:
            encrypted_data: bytes (salt + ciphertext).
            password: User-provided password string.

        Returns:
            bytes: Original plaintext data.

        Raises:
            ValueError: If password is wrong or data is corrupted.
        """
        if len(encrypted_data) < SALT_LENGTH:
            raise ValueError("Data too short — not a valid encrypted payload.")

        salt = encrypted_data[:SALT_LENGTH]
        ciphertext = encrypted_data[SALT_LENGTH:]

        key = self._derive_key(password, salt)
        f = Fernet(key)

        try:
            return f.decrypt(ciphertext)
        except Exception:
            raise ValueError("Invalid password or corrupted data.")