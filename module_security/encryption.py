"""
E2EE Encryption.

Mã hóa đầu cuối cho dữ liệu cảnh báo (snapshot, video clip):
- AES-256-GCM cho encryption
- HMAC-SHA256 cho data integrity
"""

from __future__ import annotations

import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from loguru import logger

from configs.settings import get_settings


class E2EEncryption:
    """
    End-to-End Encryption sử dụng AES-256-GCM.

    Mã hóa dữ liệu cảnh báo trước khi gửi tới mobile app.
    """

    def __init__(self, secret_key: str | None = None):
        settings = get_settings()
        key_str = secret_key or settings.e2ee_secret_key

        # Derive 256-bit key từ secret string
        self._key = hashlib.sha256(key_str.encode()).digest()
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, data: bytes) -> bytes:
        """
        Mã hóa data với AES-256-GCM.

        Returns:
            nonce (12 bytes) + ciphertext + tag
        """
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Giải mã data.

        Args:
            encrypted_data: nonce (12 bytes) + ciphertext + tag
        """
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return self._aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_file(self, input_path: str, output_path: str) -> None:
        """Mã hóa file."""
        with open(input_path, "rb") as f:
            data = f.read()

        encrypted = self.encrypt(data)

        with open(output_path, "wb") as f:
            f.write(encrypted)

        logger.debug(f"Encrypted: {input_path} → {output_path}")

    def decrypt_file(self, input_path: str, output_path: str) -> None:
        """Giải mã file."""
        with open(input_path, "rb") as f:
            encrypted = f.read()

        data = self.decrypt(encrypted)

        with open(output_path, "wb") as f:
            f.write(data)


class HMACVerifier:
    """HMAC-SHA256 cho data integrity verification."""

    def __init__(self, secret_key: str | None = None):
        settings = get_settings()
        self._key = (secret_key or settings.hmac_secret_key).encode()

    def sign(self, data: bytes) -> bytes:
        """Tạo HMAC signature."""
        return hmac.new(self._key, data, hashlib.sha256).digest()

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Xác minh HMAC signature."""
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)
