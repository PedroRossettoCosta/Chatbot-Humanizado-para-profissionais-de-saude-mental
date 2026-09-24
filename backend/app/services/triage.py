"""Triagem de segurança: camada 1 (regras) e camada 2 (modelo).

A camada 1 roda **antes** de qualquer chamada ao modelo de linguagem e
não depende de rede, chave de API ou sorte. Ela só reconhece sinais
**explícitos**, em dois níveis, conforme o protocolo da Marília
(`Documentation/Entrevista_Marilia_Protocolo_Seguranca`) e a rotulagem
do conjunto de teste (`Documentation/triagem-conjunto-teste.md`):

Emergência (texto fixo de emergência, o bot para):
- ideação ou plano de suicídio;
- automutilação (intenção ou ato);
- tentativa em andamento (ingestão de remédios, veneno);
- incapacidade de se manter em segurança;
- violência ou perigo imediato.

Dúvida sobre segurança (alerta para a profissional, o bot segue):
- desejo de morrer ("quero morrer", "queria dormir e não acordar").
  No protocolo essas frases eram emergência, mas na rotulagem ela
  marcou como dúvida: isoladas, podem ser só uma expressão forte. A
  camada 2 decide pelo contexto se a pessoa recebe o texto de emergência.

O que ela **não** quer que dispare, porque é a linguagem comum do nicho
dela (relacionamentos): "preciso de ajuda", "estou desesperada",
"perdi o meu chão", "não consigo continuar assim", "urgente". Nenhuma
dessas frases aparece aqui. Casos ambíguos ("queria sumir", "não vejo
sentido") ficam para a camada 2 (LLM), que olha o contexto.

Critério de desenho: dentro dos sinais de morte, suicídio,
automutilação e perigo imediato, ela prefere um alarme falso a deixar
passar um caso real. Por isso as regras aceitam variações de escrita
(sem acento, "to", "pra") e erram para o lado de disparar.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass

from app.models import AlertLevel
from app.services import llm

logger = logging.getLogger(__name__)

# Texto aprovado pela Marília, em forma neutra de gênero e de canal (vale
# para qualquer profissional e qualquer canal). Fica fixo no código de
# propósito: a mensagem de emergência nunca é gerada pelo modelo e a
# profissional não pode editá-la.
EMERGENCY_MESSAGE = (
    "Sinto muito que você esteja passando por isso. Este canal não "
    "funciona como serviço de emergência e não é monitorado 24 horas.\n\n"
    "Se você corre risco de se machucar ou não consegue se manter em "
    "segurança, ligue agora para o SAMU pelo 192 ou procure uma UPA ou "
    "pronto-socorro. Se houver violência ou perigo imediato, ligue para o 190.\n\n"
    "Você também pode ligar gratuitamente para o CVV pelo 188 para "
    "conversar com alguém neste momento.\n\n"
    "Se puder, entre em contato agora com uma pessoa de confiança e procure "
    "não ficar só. Não espere uma resposta por este canal para buscar "
    "ajuda imediata."
)

# Expressões idiomáticas com "morrer" que não indicam risco
# ("quero morrer de vergonha"). Sem isso a regra dispararia em conversa
# comum.
_IDIOMAS_MORRER = r"(?! de (rir|vergonha|saudade|saudades|fome|sono|calor|frio|inveja|tedio|amor|ciume|curiosidade|preguica))"

# Formas de primeira pessoa que aparecem antes de "me matar", "me
# machucar" etc. Separar a intenção evita disparar em "minha mãe vai me
# matar" (hipérbole sobre outra pessoa).
_INTENCAO = r"(quero|queria|vou|vo|preciso|pensando em|penso em|pensei em|pensado em|vontade de|planejando|plano (pra|para|de)|tentar|tentei|decidi|resolvi)"

_REGRAS_DUVIDA: dict[str, list[str]] = {
    "desejo_de_morrer": [
        rf"\b(quero|queria|prefiro|preferia) morrer\b{_IDIOMAS_MORRER}",
        # "não quero mais viver assim nesse casamento" é sofrimento na
        # relação, não risco (rótulo da Marília, conjunto de teste nº 32).
        r"\bnao (quero|aguento|consigo) mais viver\b(?! (assim|desse jeito|dessa forma|dessa maneira|nesse|nessa|com))",
        r"\bnao quero (mais )?(continuar|seguir) (vivendo|viva|vivo)\b",
        r"\bnao consigo (mais )?(continuar|seguir) vivendo\b",
        r"\b(seria|era) melhor (se )?eu (nao existisse|nao existir|nao estivesse aqui|morrer|estar mort[oa])\b",
        r"\b(queria|quero) (dormir|deitar) e nao acordar\b",
        r"\bdormir e nunca mais acordar\b",
        r"\b(queria|quero) (desaparecer|sumir) (para|pra) sempre\b",
        r"\b(queria|quero) (estar|ta) mort[oa]\b",
    ],
}

_REGRAS_EMERGENCIA: dict[str, list[str]] = {
    "suicidio": [
        r"\bsuicid",  # suicídio, suicidar, suicida
        rf"\b{_INTENCAO} me matar\b",
        r"\bacabar com (a )?minha (propria )?vida\b",
        r"\btirar (a )?minha (propria )?vida\b",
        r"\b(dar|por) (um )?fim (a|na|em) minha vida\b",
    ],
    "automutilacao": [
        rf"\b{_INTENCAO} me (machucar|cortar|ferir|mutilar|queimar)\b",
        r"\bauto ?mutil",  # automutilação, auto mutilar
        r"\b(fiz|estou fazendo|to fazendo) (alguma coisa|algo) (pra|para|contra) (me machucar|me ferir|mim)\b",
        r"\b(estou|to|tou) me (cortando|machucando|ferindo)\b",
    ],
    "tentativa_em_andamento": [
        r"\b(tomei|engoli|ingeri) (todos os|todas as|varios|varias|muitos|muitas|um monte de|uma caixa|a caixa|uma cartela|a cartela)\b.{0,20}\b(remedio|comprimido|medicamento|pilula|capsula|rivotril|clonazepam)",
        r"\b(tomei|bebi|ingeri|engoli) (veneno|chumbinho|agua sanitaria|soda caustica)\b",
        r"\b(estou|to|tou) prestes a fazer (alguma coisa|algo|uma besteira)\b",
        r"\b(vou|vo) fazer (alguma coisa|algo|uma besteira) (comigo|contra mim)\b",
        r"\b(estou|to|tou) com (a|uma) (arma|corda|lamina|gilete) (aqui|na mao)\b",
    ],
    "sem_seguranca": [
        r"\bnao consigo (garantir|prometer) que (vou|vo) ficar (em )?segur",
        r"\bnao consigo (me manter|ficar|permanecer) (em )?segur",
    ],
    "violencia_perigo_imediato": [
        # "vai me matar" fica de fora: é hipérbole comum ("minha mãe vai
        # me matar"). A ameaça real sem esses verbos fica para a camada 2.
        r"\b(ameacou|ameacando|tentou|tentando) me matar\b",
        r"\b(estou|to|tou) (sendo )?(agredid[oa]|espancad[oa]|ameacad[oa] de morte)\b",
        r"\b(esta|ta) me (batendo|agredindo|espancando|estrangulando|enforcando)\b",
        r"\b(estou|to|tou) em perigo\b",
        r"\bcorro (risco de vida|perigo)\b",
    ],
}

def _compilar(regras: dict[str, list[str]]) -> dict[str, list[re.Pattern]]:
    return {categoria: [re.compile(p) for p in padroes] for categoria, padroes in regras.items()}


# A emergência é verificada primeiro: uma mensagem que casa com os dois
# níveis ("quero morrer, tomei os remédios") precisa virar emergência.
_REGRAS_POR_NIVEL = [
    (AlertLevel.EMERGENCY, _compilar(_REGRAS_EMERGENCIA)),
    (AlertLevel.POSSIBLE_RISK, _compilar(_REGRAS_DUVIDA)),
]


@dataclass(frozen=True)
class TriageResult:
    level: AlertLevel
    # Qual regra disparou (ex.: "camada1:suicidio"). Serve para auditoria
    # e para a análise de falsos positivos com a Marília.
    trigger: str
    # Trecho do texto original que casou com a regra.
    excerpt: str


def normalize(text: str) -> str:
    """Minúsculas, sem acento, sem pontuação, espaços simples.

    Mensagens de WhatsApp chegam sem acento, com abreviações e
    pontuação solta; a regra precisa casar com "Nao quero mais viver..."
    tanto quanto com "não quero mais viver".
    """
    sem_acento = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9\s]", " ", sem_acento.lower())
    return re.sub(r"\s+", " ", texto).strip()


def check_rules(text: str) -> TriageResult | None:
    """Camada 1. Devolve o nível e a regra se houver sinal explícito de risco."""
    normalizado = normalize(text)
    for nivel, regras in _REGRAS_POR_NIVEL:
        for categoria, padroes in regras.items():
            if any(padrao.search(normalizado) for padrao in padroes):
                return TriageResult(level=nivel, trigger=f"camada1:{categoria}", excerpt=text[:500])
    return None


# ---------------------------------------------------------------------------
# Camadas 1 + 2
# ---------------------------------------------------------------------------

_NIVEL_DA_CAMADA2 = {
    "normal": None,
    "sofrimento_intenso": AlertLevel.INTENSE_SUFFERING,
    "duvida": AlertLevel.POSSIBLE_RISK,
    "emergencia": AlertLevel.EMERGENCY,
}

# Da menos grave para a mais grave.
_GRAVIDADE = [None, AlertLevel.INTENSE_SUFFERING, AlertLevel.POSSIBLE_RISK, AlertLevel.EMERGENCY]


def assess(text: str, history: list[dict], audience: str | None = None) -> TriageResult | None:
    """Triagem completa da última mensagem. `None` quer dizer normal.

    - `audience` é a especialidade e o público da profissional; só chega
      à camada 2, nunca às regras da camada 1.
    - Se a camada 1 já achou emergência, o modelo nem é chamado.
    - A camada 2 só pode **subir** o nível que a camada 1 deu, nunca
      rebaixar: um erro do modelo não transforma "quero me matar" em
      conversa normal.
    - **Falha fechada:** se o modelo falhar (rede, tempo, recusa,
      formato), a mensagem vira dúvida e a profissional é avisada.
    """
    regra = check_rules(text)
    if regra and regra.level == AlertLevel.EMERGENCY:
        return regra

    try:
        classificacao = llm.classify_risk(history, audience)
        modelo = _NIVEL_DA_CAMADA2[classificacao.nivel]
        trigger = f"camada2:{classificacao.nivel}"
    except Exception:
        # Qualquer falha, sem exceção. Não registra o texto da mensagem
        # no log: só o fato de que a camada 2 falhou.
        logger.exception("camada 2 da triagem falhou; tratando como dúvida")
        modelo = AlertLevel.POSSIBLE_RISK
        trigger = "camada2:falha"

    if regra and _GRAVIDADE.index(regra.level) >= _GRAVIDADE.index(modelo):
        return regra
    if modelo is None:
        return None
    return TriageResult(level=modelo, trigger=trigger, excerpt=text[:500])
