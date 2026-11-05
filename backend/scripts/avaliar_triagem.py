"""Avalia a triagem (camadas 1 + 2) contra os rótulos da Marília.

Lê as mensagens e os rótulos de `Documentation/triagem-conjunto-teste.md`,
passa cada mensagem pela triagem como se fosse a única da conversa e
compara o nível decidido com o rótulo. Chama a API da Claude de verdade
(uma chamada por mensagem que a camada 1 não resolve sozinha).

Mede também a camada 1 sozinha (só as regras, sem modelo), para comparar
com as camadas 1 + 2: é o que um bot sem LLM conseguiria.

Uso, a partir de `backend/`:

    python -m scripts.avaliar_triagem
"""

import re
import sys
from collections import Counter
from pathlib import Path

from app.models import AlertLevel
from app.services import llm, triage

CONJUNTO = Path(__file__).resolve().parents[2] / "Documentation" / "triagem-conjunto-teste.md"

SIGLA = {
    None: "N",
    AlertLevel.INTENSE_SUFFERING: "S",
    AlertLevel.POSSIBLE_RISK: "D",
    AlertLevel.EMERGENCY: "E",
}
ORDEM = ["N", "S", "D", "E"]

# O que a Marília preencheria no campo "Especialidade e público", tirado
# das palavras dela no protocolo de segurança. Os rótulos são dela, então
# a avaliação usa o público dela.
PUBLICO_MARILIA = (
    "Psicanalista. Meu trabalho é voltado principalmente para relacionamentos: "
    "as pessoas chegam depois de um término, uma traição, uma briga ou uma relação "
    "muito difícil, e é comum dizerem que estão sem chão, desesperadas ou que "
    "precisam de ajuda urgente."
)


def carregar() -> list[tuple[int, str, str]]:
    texto = CONJUNTO.read_text(encoding="utf-8")
    mensagens = {int(n): t for n, t in re.findall(r"^(\d+)\. (.+)$", texto, re.M)}
    rotulos = {int(n): r for n, r in re.findall(r"^\| (\d+) \| ([NSDE]) \|", texto, re.M)}
    faltando = set(mensagens) - set(rotulos)
    if faltando:
        sys.exit(f"Mensagens sem rótulo: {sorted(faltando)}")
    return [(n, mensagens[n], rotulos[n]) for n in sorted(mensagens)]


def resumo(pares: list[tuple[str, str]]) -> None:
    """Imprime as métricas de uma lista de (rótulo da Marília, nível obtido)."""
    total = len(pares)
    acertos = sum(1 for e, o in pares if e == o)
    matriz = Counter(pares)
    emergencias = [o for e, o in pares if e == "E"]
    # O erro que importa: risco (D ou E) que não gerou alerta nenhum.
    risco = [o for e, o in pares if e in ("D", "E")]
    alarme_falso = sum(1 for e, o in pares if e in ("N", "S") and o in ("D", "E"))
    emergencia_indevida = sum(1 for e, o in pares if e != "E" and o == "E")

    print(f"Concordância exata: {acertos}/{total}")
    print(f"Emergências reconhecidas como E: {emergencias.count('E')}/{len(emergencias)}")
    print(f"Risco (D/E) sem nenhum alerta: {sum(o in ('N', 'S') for o in risco)}/{len(risco)}")
    print(f"Alertas em mensagens N/S (alarme falso): {alarme_falso}")
    print(f"Texto de emergência enviado sem ser E: {emergencia_indevida}")
    print("Matriz (linha = Marília, coluna = sistema)")
    print("     " + "  ".join(ORDEM))
    for e in ORDEM:
        print(f"  {e}  " + "  ".join(str(matriz[(e, o)]) for o in ORDEM))


def main() -> None:
    # Guarda a justificativa do modelo para o relatório, sem mudar a triagem.
    justificativas: dict[int, str] = {}
    classificar = llm.classify_risk
    atual = {"n": 0}

    def classificar_e_guardar(history, audience=None):
        resultado = classificar(history, audience)
        justificativas[atual["n"]] = resultado.justificativa
        return resultado

    llm.classify_risk = classificar_e_guardar

    linhas = []
    so_regras = []
    for n, texto, esperado in carregar():
        atual["n"] = n
        resultado = triage.assess(texto, [{"role": "user", "content": texto}], PUBLICO_MARILIA)
        obtido = SIGLA[resultado.level if resultado else None]
        camada = resultado.trigger if resultado else "camada2:normal"
        regra = triage.check_rules(texto)
        so_regras.append((esperado, SIGLA[regra.level if regra else None]))
        linhas.append((n, texto, esperado, obtido, camada, justificativas.get(n, "")))
        marca = "  " if esperado == obtido else "!!"
        print(
            f"{marca} {n:>2} esperado {esperado} obtido {obtido}  [{camada}]"
            f"  camada 1 sozinha: {so_regras[-1][1]}",
            flush=True,
        )

    print()
    print("== Camadas 1 + 2 ==")
    resumo([(e, o) for _, _, e, o, _, _ in linhas])
    print()
    print("== Camada 1 sozinha (só regras, sem modelo) ==")
    resumo(so_regras)
    print()
    print("Divergências:")
    for n, texto, e, o, camada, just in linhas:
        if e != o:
            print(f"  {n:>2}. [{e}→{o}] {texto}")
            print(f"      {camada}: {just}")


if __name__ == "__main__":
    main()
