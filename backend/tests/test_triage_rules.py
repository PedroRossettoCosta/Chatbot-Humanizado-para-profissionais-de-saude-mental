"""Camada 1 da triagem contra as frases do protocolo da Marília.

As listas abaixo vêm da entrevista de protocolo de segurança: a primeira
são as frases que ela disse que devem disparar; a segunda, as que ela
disse que NÃO podem disparar sozinhas, por serem comuns no nicho dela.
"""

import pytest

from app.models import AlertLevel
from app.services import triage

# Citadas por ela como gatilho, mais os sinais de tentativa, meios e
# violência que ela listou em seguida.
EMERGENCIA = [
    "Quero me matar.",
    "Vou acabar com a minha vida.",
    "Estou pensando em me machucar.",
    "Tenho um plano para me matar.",
    "Já fiz alguma coisa para me machucar.",
    "Não consigo garantir que vou ficar em segurança.",
    "Estou prestes a fazer alguma coisa comigo.",
    "tomei todos os remédios da caixa",
    "ele ameaçou me matar",
    "to sendo agredida agora",
    # Variações de escrita comuns no WhatsApp
    "to pensando em me matar...",
    "tenho pensamentos suicidas",
]

# Desejo de morrer sem intenção clara: no protocolo eram emergência, mas
# na rotulagem de 23/09 (itens 7 e 31) ela marcou como dúvida, porque
# isoladas podem ser só uma expressão forte.
DUVIDA = [
    "Não quero mais viver.",
    "Quero morrer.",
    "Seria melhor se eu não existisse.",
    "Queria dormir e não acordar.",
    "não consigo continuar vivendo",
    "queria desaparecer para sempre",
    "nao quero mais viver",
    "QUERO MORRER",
]

# Citadas por ela como linguagem comum do nicho, que não é emergência.
NAO_PODE_DISPARAR = [
    "preciso de ajuda",
    "estou desesperada",
    "não estou bem",
    "estou deprimida",
    "perdi o meu chão",
    "não quero fazer nada",
    "não consigo continuar assim",
    "não consigo continuar nesse relacionamento",
    "quero desaparecer da vida dele",
    "não quero mais viver assim nesse casamento",
    "terminei um relacionamento",
    "estou sem chão",
    "quero sair desse ciclo",
    "preciso de atendimento com urgência, não estou nada bem",
    "Perdi totalmente o meu chão, não estou comendo, não estou tomando banho",
    # Expressões idiomáticas e hipérboles sobre terceiros
    "quero morrer de vergonha",
    "minha mãe vai me matar se eu chegar tarde",
    "oi, quanto custa a sessão?",
]


@pytest.mark.parametrize("texto", EMERGENCIA)
def test_sinais_explicitos_sao_emergencia(texto):
    resultado = triage.check_rules(texto)
    assert resultado is not None, texto
    assert resultado.level == AlertLevel.EMERGENCY
    assert resultado.trigger.startswith("camada1:")


@pytest.mark.parametrize("texto", DUVIDA)
def test_desejo_de_morrer_isolado_e_duvida(texto):
    resultado = triage.check_rules(texto)
    assert resultado is not None, texto
    assert resultado.level == AlertLevel.POSSIBLE_RISK


def test_emergencia_vence_quando_os_dois_niveis_aparecem():
    resultado = triage.check_rules("quero morrer, tomei todos os remédios")
    assert resultado.level == AlertLevel.EMERGENCY


@pytest.mark.parametrize("texto", NAO_PODE_DISPARAR)
def test_linguagem_comum_do_nicho_nao_dispara(texto):
    assert triage.check_rules(texto) is None


def test_trecho_guarda_o_texto_original():
    resultado = triage.check_rules("Oi. Não quero mais viver.")
    assert resultado.excerpt == "Oi. Não quero mais viver."
