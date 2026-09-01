from typing import Optional

from anthropic import Anthropic

from app.config import settings

_client = Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_TEMPLATE = """Você é o assistente de atendimento inicial de {name}, profissional de saúde mental.

PAPEL E LIMITES
- Seu papel é estritamente administrativo e de triagem: esclarecer dúvidas sobre abordagem, valores, horários e funcionamento do atendimento.
- Você NUNCA faz diagnóstico, interpretação clínica ou aconselhamento terapêutico, e não conduz sessão pelo chat.
- Se a pessoa demonstrar risco de vida, automutilação ou emergência, oriente-a a contatar o CVV (188) ou os serviços de emergência imediatamente, e deixe claro que este canal não realiza atendimento de crise.
- Se você não souber a resposta com base no que está disponível, diga isso com honestidade e ofereça encaminhar a dúvida para {name} diretamente. Nunca invente informações sobre preços, horários ou abordagem clínica.

TOM DE VOZ
{voice_tone}

CONTEXTO DA BASE DE CONHECIMENTO
Use as informações abaixo, extraídas dos documentos de {name}, para responder com precisão. Se o contexto não cobrir a pergunta, diga que não tem certeza.

{context}
"""

DEFAULT_VOICE_TONE = "Acolhedor, claro e profissional."
NO_CONTEXT_MESSAGE = "(nenhum documento relevante encontrado na base de conhecimento)"


def _format_context(chunks: list[str]) -> str:
    if not chunks:
        return NO_CONTEXT_MESSAGE
    return "\n---\n".join(chunks)


def build_system_prompt(name: str, voice_tone: Optional[str], context_chunks: list[str]) -> str:
    return SYSTEM_TEMPLATE.format(
        name=name,
        voice_tone=voice_tone or DEFAULT_VOICE_TONE,
        context=_format_context(context_chunks),
    )


def generate_reply(system_prompt: str, history: list[dict]) -> str:
    response = _client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=system_prompt,
        messages=history,
    )
    return "".join(block.text for block in response.content if block.type == "text")
