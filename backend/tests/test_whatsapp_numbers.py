"""Conectar o número de WhatsApp pelo painel (etapa 6 e Perfil).

A Graph API da Meta é substituída por `FakeMeta`, que guarda os números
da conta como a Meta guardaria. O teste real, com chip e SMS, está no
roteiro manual de `funcionalidades/conectar-whatsapp.md`.
"""

import pytest

from app import models
from app.config import settings
from app.services import crypto, whatsapp, whatsapp_numbers

TEST_SLUG = "test-pytest-numero"
OTHER_SLUG = "test-pytest-numero-outra"
WABA = "waba-teste"


class FakeMeta:
    def __init__(self):
        self.numbers = {}  # id -> dados do número
        self.calls = []
        self.fail = {}  # "caminho final" -> código de erro da Meta

    def __call__(self, method, path, body=None, params=None):
        self.calls.append((method, path, body))
        action = path.rsplit("/", 1)[-1]
        if action in self.fail:
            raise whatsapp.MetaError("erro simulado", self.fail[action])
        if path == f"{WABA}/phone_numbers" and method == "GET":
            return {"data": list(self.numbers.values())}
        if path == f"{WABA}/phone_numbers":
            new_id = str(9000 + len(self.numbers))
            self.numbers[new_id] = {
                "id": new_id,
                "display_phone_number": f"+{body['cc']} {body['phone_number']}",
                "verified_name": body["verified_name"],
                "code_verification_status": "NOT_VERIFIED",
            }
            return {"id": new_id}
        number_id = path.split("/")[0]
        if action == "request_code":
            if self.numbers[number_id]["code_verification_status"] == "VERIFIED":
                raise whatsapp.MetaError("já verificado", whatsapp_numbers.ALREADY_VERIFIED)
            return {"success": True}
        if action == "verify_code":
            if body["code"] != "123456":
                raise whatsapp.MetaError("código errado", 136025)
            self.numbers[number_id]["code_verification_status"] = "VERIFIED"
            return {"success": True}
        if action == "register":
            return {"success": True}
        if action == "deregister":
            self.numbers.get(number_id, {})["deregistered"] = True
            return {"success": True}
        if method == "POST" and path == number_id and params and "new_display_name" in params:
            self.numbers[number_id].update(new_display_name=params["new_display_name"], new_name_status="PENDING")
            return {"success": True}
        return {**self.numbers.get(number_id, {}), "status": "CONNECTED", "name_status": "PENDING_REVIEW"}

    def paths(self):
        return [path for _, path, _ in self.calls]


@pytest.fixture
def meta(monkeypatch):
    fake = FakeMeta()
    monkeypatch.setattr(whatsapp, "_graph", fake)
    monkeypatch.setattr(settings, "whatsapp_business_account_id", WABA)
    monkeypatch.setattr(settings, "whatsapp_access_token", "token-teste")
    return fake


@pytest.fixture
def professional(db):
    _cleanup(db)
    p = models.Professional(slug=TEST_SLUG, name="Marília Rossetto")
    db.add(p)
    db.commit()
    yield p
    _cleanup(db)


def _cleanup(db):
    db.rollback()
    for slug in (TEST_SLUG, OTHER_SLUG):
        existing = db.query(models.Professional).filter_by(slug=slug).first()
        if existing:
            db.delete(existing)
    db.commit()


def _start(client, number="(21) 99876-5432", name="Marília Rossetto", method="SMS"):
    return client.post(
        f"/professionals/{TEST_SLUG}/whatsapp", json={"number": number, "display_name": name, "method": method}
    )


def test_normalize_br_accepts_common_formats():
    assert whatsapp_numbers.normalize_br("(21) 99876-5432") == ("55", "21998765432")
    assert whatsapp_numbers.normalize_br("+55 21 99876-5432") == ("55", "21998765432")
    assert whatsapp_numbers.normalize_br("21 3876-5432") == ("55", "2138765432")
    for bad in ("99876-5432", "021998765432", "", "+1 415 555 0100"):
        with pytest.raises(whatsapp_numbers.NumberError):
            whatsapp_numbers.normalize_br(bad)


def test_full_flow_connects_number(client, db, meta, professional):
    response = _start(client)
    assert response.status_code == 200
    body = response.json()
    assert body["step"] == "code_sent" and body["connected"] is False
    assert body["display_number"] == "+55 21 99876-5432"
    assert meta.calls[1] == ("POST", f"{WABA}/phone_numbers", {
        "cc": "55", "phone_number": "21998765432", "verified_name": "Marília Rossetto"
    })
    assert meta.calls[2][1:] == ("9000/request_code", {"code_method": "SMS", "language": "pt_BR"})

    # Antes do registro o número não recebe mensagens.
    db.refresh(professional)
    assert professional.whatsapp_phone_number_id is None

    assert client.post(f"/professionals/{TEST_SLUG}/whatsapp/verify", json={"code": "12"}).status_code == 400
    response = client.post(f"/professionals/{TEST_SLUG}/whatsapp/verify", json={"code": "123 456"})
    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["registrations_last_72h"] == 1

    register = next(body for _, path, body in meta.calls if path == "9000/register")
    assert register["messaging_product"] == "whatsapp"
    assert len(register["pin"]) == 6 and register["pin"].isdigit()

    db.refresh(professional)
    assert professional.whatsapp_phone_number_id == "9000"
    assert professional.whatsapp_pending_id is None
    # O PIN fica cifrado, e é o mesmo que foi para a Meta.
    assert register["pin"] not in professional.whatsapp_pin
    assert crypto.decrypt(professional.whatsapp_pin) == register["pin"]


def test_wrong_code_keeps_waiting(client, db, meta, professional):
    _start(client)
    response = client.post(f"/professionals/{TEST_SLUG}/whatsapp/verify", json={"code": "999999"})
    assert response.status_code == 400
    assert "código não foi aceito" in response.json()["detail"]
    db.refresh(professional)
    assert professional.whatsapp_setup_step == "code_sent"
    assert "9000/register" not in meta.paths()


def test_resend_by_voice(client, meta, professional):
    _start(client)
    response = client.post(f"/professionals/{TEST_SLUG}/whatsapp/resend", json={"method": "VOICE"})
    assert response.status_code == 200
    requests = [body for _, path, body in meta.calls if path == "9000/request_code"]
    assert requests[-1] == {"code_method": "VOICE", "language": "pt_BR"}


def test_number_already_in_waba_is_reused(client, meta, professional):
    meta.numbers["777"] = {
        "id": "777",
        "display_phone_number": "+55 21 99876-5432",
        "verified_name": "Marília Rossetto",
        "code_verification_status": "NOT_VERIFIED",
    }
    assert _start(client).status_code == 200
    assert ("POST", f"{WABA}/phone_numbers") not in [(m, p) for m, p, _ in meta.calls]
    assert "777/request_code" in meta.paths()


def test_already_verified_number_skips_the_code(client, meta, professional):
    meta.numbers["777"] = {
        "id": "777",
        "display_phone_number": "+55 21 99876-5432",
        "verified_name": "Marília Rossetto",
        "code_verification_status": "VERIFIED",
    }
    body = _start(client).json()
    assert body["step"] == "verified"
    assert "777/request_code" not in meta.paths()
    response = client.post(f"/professionals/{TEST_SLUG}/whatsapp/register")
    assert response.status_code == 200 and response.json()["connected"] is True


def test_register_stops_before_meta_limit(client, db, meta, professional):
    _start(client)
    for _ in range(whatsapp_numbers.REGISTER_LIMIT):
        db.add(models.WhatsAppRegisterAttempt(professional_id=professional.id, phone_number_id="9000", ok=False))
    db.commit()
    response = client.post(f"/professionals/{TEST_SLUG}/whatsapp/verify", json={"code": "123456"})
    assert response.status_code == 429
    assert "9000/register" not in meta.paths()
    db.refresh(professional)
    # Já verificado: o próximo passo é só registrar de novo, depois.
    assert professional.whatsapp_setup_step == "verified"


def test_meta_register_block_is_explained_and_counted(client, db, meta, professional):
    meta.fail["register"] = whatsapp_numbers.REGISTER_RATE_LIMIT
    _start(client)
    response = client.post(f"/professionals/{TEST_SLUG}/whatsapp/verify", json={"code": "123456"})
    assert response.status_code == 502
    assert "bloqueado por 72 horas" in response.json()["detail"]
    attempt = db.query(models.WhatsAppRegisterAttempt).filter_by(phone_number_id="9000").one()
    assert attempt.ok is False and attempt.error_code == str(whatsapp_numbers.REGISTER_RATE_LIMIT)


def test_register_goes_back_to_the_code_when_meta_says_not_verified(client, db, meta, professional):
    meta.numbers["777"] = {
        "id": "777",
        "display_phone_number": "+55 21 99876-5432",
        "verified_name": "Marília Rossetto",
        "code_verification_status": "VERIFIED",
    }
    assert _start(client).json()["step"] == "verified"
    # A Meta muda de ideia: o número não está mais verificado.
    meta.numbers["777"]["code_verification_status"] = "NOT_VERIFIED"
    meta.fail["register"] = 100
    response = client.post(f"/professionals/{TEST_SLUG}/whatsapp/register")
    assert response.status_code == 409
    assert response.json()["detail"] == whatsapp_numbers.NOT_VERIFIED_AT_META
    db.refresh(professional)
    assert professional.whatsapp_setup_step == "code_sent"


def test_number_of_another_account_is_refused(client, db, meta, professional):
    meta.numbers["777"] = {
        "id": "777",
        "display_phone_number": "+55 21 99876-5432",
        "verified_name": "Outra",
        "code_verification_status": "VERIFIED",
    }
    db.add(models.Professional(slug=OTHER_SLUG, name="Outra", whatsapp_phone_number_id="777"))
    db.commit()
    response = _start(client)
    assert response.status_code == 409
    db.refresh(professional)
    assert professional.whatsapp_pending_id is None


def test_connected_professional_cannot_start_again(client, db, meta, professional):
    professional.whatsapp_phone_number_id = "555"
    db.commit()
    assert _start(client).status_code == 409


def test_cancel_clears_pending(client, db, meta, professional):
    _start(client)
    response = client.delete(f"/professionals/{TEST_SLUG}/whatsapp/pending")
    assert response.status_code == 200
    assert response.json()["step"] is None
    db.refresh(professional)
    assert professional.whatsapp_pending_id is None


def test_without_waba_configured(client, meta, professional, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_business_account_id", "")
    assert _start(client).status_code == 503
    status = client.get(f"/professionals/{TEST_SLUG}/whatsapp").json()
    assert status["configured"] is False and status["connected"] is False


def test_status_fills_number_linked_by_hand(client, db, meta, professional):
    meta.numbers["4242"] = {"id": "4242", "display_phone_number": "+55 21 91234-0000",
                                        "verified_name": "SelenIA"}
    professional.whatsapp_phone_number_id = "4242"
    db.commit()
    status = client.get(f"/professionals/{TEST_SLUG}/whatsapp").json()
    assert status["connected"] is True
    assert status["display_number"] == "+55 21 91234-0000"
    assert status["meta_status"] == "CONNECTED"


def _connected(client, meta):
    _start(client)
    client.post(f"/professionals/{TEST_SLUG}/whatsapp/verify", json={"code": "123456"})


def test_rename_asks_meta_and_shows_the_review(client, db, meta, professional):
    _connected(client, meta)
    assert client.post(f"/professionals/{TEST_SLUG}/whatsapp/name", json={"display_name": "x"}).status_code == 400
    body = client.post(f"/professionals/{TEST_SLUG}/whatsapp/name", json={"display_name": "Psi Marília"}).json()
    assert body["new_display_name"] == "Psi Marília" and body["new_name_status"] == "PENDING"
    # O nome antigo continua até a Meta aprovar.
    assert body["verified_name"] == "Marília Rossetto"


def test_apply_approved_name_registers_again(client, db, meta, professional):
    _connected(client, meta)
    before = meta.paths().count("9000/register")
    body = client.post(f"/professionals/{TEST_SLUG}/whatsapp/name/apply").json()
    assert body["connected"] is True
    assert meta.paths().count("9000/register") == before + 1
    assert whatsapp_numbers.registrations_in_window(db, "9000") == 2


def test_disconnect_frees_the_professional_for_another_number(client, db, meta, professional):
    _connected(client, meta)
    body = client.delete(f"/professionals/{TEST_SLUG}/whatsapp").json()
    assert body["connected"] is False and body["display_number"] is None
    assert "9000/deregister" in meta.paths()
    db.refresh(professional)
    assert professional.whatsapp_phone_number_id is None
    # Dá para começar com outro número.
    assert _start(client, number="(21) 91111-2222").status_code == 200


def test_rename_and_disconnect_need_a_connected_number(client, meta, professional):
    assert client.post(f"/professionals/{TEST_SLUG}/whatsapp/name", json={"display_name": "Psi Marília"}).status_code == 409
    assert client.delete(f"/professionals/{TEST_SLUG}/whatsapp").status_code == 409
