import sqlalchemy as sa

from app import models
from app.models import Channel, MessageRole, SentBy
from app.services import conversations

TEST_SLUG = "test-pytest-conversas"
TELEFONE = "+5521955554444"


def _cleanup(db):
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if professional:
        db.delete(professional)
        db.commit()


def _professional(db):
    professional = models.Professional(slug=TEST_SLUG, name="Teste Conversas")
    db.add(professional)
    db.commit()
    return professional


def test_same_external_id_reuses_contact_and_conversation(db):
    _cleanup(db)
    professional = _professional(db)

    contato = conversations.get_or_create_contact(db, professional, Channel.WHATSAPP, TELEFONE)
    conversa, nova = conversations.get_or_create_conversation(db, contato)
    assert nova is True

    # Mesma pessoa mandando mensagem de novo: nada é duplicado.
    mesmo_contato = conversations.get_or_create_contact(db, professional, Channel.WHATSAPP, TELEFONE)
    mesma_conversa, nova_de_novo = conversations.get_or_create_conversation(db, mesmo_contato)

    assert mesmo_contato.id == contato.id
    assert mesma_conversa.id == conversa.id
    assert nova_de_novo is False

    _cleanup(db)


def test_same_number_on_another_channel_is_another_contact(db):
    _cleanup(db)
    professional = _professional(db)

    whatsapp = conversations.get_or_create_contact(db, professional, Channel.WHATSAPP, TELEFONE)
    simulador = conversations.get_or_create_contact(db, professional, Channel.SIMULATOR, TELEFONE)

    assert whatsapp.id != simulador.id

    _cleanup(db)


def test_phone_number_is_encrypted_at_rest(db):
    _cleanup(db)
    professional = _professional(db)
    contato = conversations.get_or_create_contact(db, professional, Channel.WHATSAPP, TELEFONE)

    # Lido pela aplicação: texto normal.
    assert contato.external_id == TELEFONE

    # Lido com SQL puro, sem passar pelo tipo EncryptedText: cifrado.
    # (Uma consulta pelo modelo decifraria de volta e não provaria nada.)
    bruto = db.execute(
        sa.text("SELECT external_id FROM contacts WHERE id = :id"), {"id": contato.id}
    ).scalar_one()
    assert bruto != TELEFONE
    assert TELEFONE not in bruto

    _cleanup(db)


def test_history_respects_order_and_limit(db):
    """Mensagens gravadas em rajada precisam manter a ordem de inserção.

    O relógio do sistema tem resolução de milissegundos: estas três
    chamadas seguidas recebem o mesmo `created_at`. Ordenar por horário
    devolveria o histórico embaralhado, e o modelo veria a conversa fora
    de ordem.
    """
    _cleanup(db)
    professional = _professional(db)
    contato = conversations.get_or_create_contact(db, professional, Channel.SIMULATOR, "sessao-1")
    conversa, _ = conversations.get_or_create_conversation(db, contato)

    conversations.record_message(db, conversa, MessageRole.USER, "primeira")
    conversations.record_message(db, conversa, MessageRole.ASSISTANT, "segunda", sent_by=SentBy.BOT)
    conversations.record_message(db, conversa, MessageRole.USER, "terceira")

    historico = conversations.recent_history(db, conversa, limit=2)

    # As duas últimas, na ordem em que foram gravadas.
    assert [m["content"] for m in historico] == ["segunda", "terceira"]

    # E o histórico completo continua na ordem certa.
    completo = conversations.recent_history(db, conversa, limit=10)
    assert [m["content"] for m in completo] == ["primeira", "segunda", "terceira"]

    _cleanup(db)
