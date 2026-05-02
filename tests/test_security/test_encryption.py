"""Tests cho module_security - encryption."""

import pytest

from module_security.encryption import E2EEncryption, HMACVerifier


class TestE2EEncryption:
    def test_encrypt_decrypt(self):
        enc = E2EEncryption(secret_key="test-secret-key-1234")
        original = b"Hello, AI Child Guardian!"
        encrypted = enc.encrypt(original)
        decrypted = enc.decrypt(encrypted)
        assert decrypted == original

    def test_encrypted_differs(self):
        enc = E2EEncryption(secret_key="test-secret-key-1234")
        data = b"sensitive data"
        enc1 = enc.encrypt(data)
        enc2 = enc.encrypt(data)
        # Different nonces → different ciphertext
        assert enc1 != enc2

    def test_wrong_key_fails(self):
        enc1 = E2EEncryption(secret_key="key-1")
        enc2 = E2EEncryption(secret_key="key-2")
        encrypted = enc1.encrypt(b"data")
        with pytest.raises(Exception):
            enc2.decrypt(encrypted)


class TestHMACVerifier:
    def test_sign_and_verify(self):
        verifier = HMACVerifier(secret_key="test-hmac-key")
        data = b"important data"
        sig = verifier.sign(data)
        assert verifier.verify(data, sig) is True

    def test_tampered_data_fails(self):
        verifier = HMACVerifier(secret_key="test-hmac-key")
        data = b"original"
        sig = verifier.sign(data)
        assert verifier.verify(b"tampered", sig) is False
