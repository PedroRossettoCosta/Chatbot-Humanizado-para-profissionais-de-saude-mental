from app.services import crypto


def test_encrypt_decrypt_roundtrip():
    original = "conteúdo sensível de uma mensagem"
    encrypted = crypto.encrypt(original)
    assert encrypted != original
    assert crypto.decrypt(encrypted) == original


def test_decrypt_gracefully_handles_unencrypted_legacy_value():
    legacy_plaintext = "mensagem gravada antes da criptografia"
    assert crypto.decrypt(legacy_plaintext) == legacy_plaintext


def test_encrypt_is_not_deterministic():
    """Cifras iguais se repetiriam e vazariam quem falou o quê."""
    texto = "+5521999999999"
    assert crypto.encrypt(texto) != crypto.encrypt(texto)


def test_blind_index_is_deterministic_and_irreversible():
    telefone = "+5521999999999"
    indice = crypto.blind_index(telefone)

    # Determinístico: é isso que permite buscar o contato no banco.
    assert indice == crypto.blind_index(telefone)
    # Telefones diferentes geram índices diferentes.
    assert indice != crypto.blind_index("+5521888888888")
    # O índice não contém o valor original.
    assert telefone not in indice
