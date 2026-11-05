"""Cadastro em etapas: o que precisa estar preenchido para concluir.

A SelenIA só começa a atender em nome da profissional com o perfil
completo. Sem valores, apresentação ou exemplos de tom, ela responderia
no escuro; sem o aceite das regras, a profissional não saberia o que o
sistema faz numa emergência.
"""

from app import models
from app.services import guidelines


def missing_fields(professional: models.Professional) -> list[str]:
    """Lista, em linguagem da tela, o que falta para concluir o cadastro."""
    missing = []
    if not (professional.name or "").strip():
        missing.append("Nome de exibição")
    if not (professional.alert_email or "").strip():
        missing.append("E-mail para alertas")
    if professional.pronouns not in guidelines.PRONOUNS:
        missing.append("Como a SelenIA fala de você")
    if not (professional.audience_description or "").strip():
        missing.append("Especialidade e público")
    if not (professional.service_info or "").strip():
        missing.append("Informações do serviço")
    if not professional.payment_methods:
        missing.append("Formas de pagamento aceitas")
    if not professional.session_minutes:
        missing.append("Duração da sessão")
    if not (professional.voice_tone or "").strip():
        missing.append("Tom de voz")
    examples = professional.voice_examples or {}
    for question in guidelines.VOICE_QUESTIONS:
        answer = examples.get(question["key"]) or {}
        if not (answer.get("good") or "").strip() or not (answer.get("bad") or "").strip():
            missing.append(f'Respostas boa e ruim para "{question["question"]}"')
    if professional.rules_accepted_at is None:
        missing.append("Aceite das regras da SelenIA")
    return missing


def accept_rules(professional: models.Professional) -> None:
    professional.rules_accepted_at = models._now()


def complete(professional: models.Professional) -> list[str]:
    """Conclui o cadastro. Devolve o que falta (vazio = concluído)."""
    missing = missing_fields(professional)
    if not missing and professional.onboarding_completed_at is None:
        professional.onboarding_completed_at = models._now()
    return missing
