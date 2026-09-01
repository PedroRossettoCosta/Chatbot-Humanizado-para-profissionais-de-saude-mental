from app.services import crypto


def test_encrypt_decrypt_roundtrip():
    original = "conteúdo sensível de uma mensagem"
    encrypted = crypto.encrypt(original)
    assert encrypted != original
    assert crypto.decrypt(encrypted) == original


def test_decrypt_gracefully_handles_unencrypted_legacy_value():
    legacy_plaintext = "mensagem gravada antes da criptografia"
    assert crypto.decrypt(legacy_plaintext) == legacy_plaintext
