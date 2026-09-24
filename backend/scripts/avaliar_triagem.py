"""Avalia a triagem (camadas 1 + 2) contra os rótulos da Marília.

Lê as mensagens e os rótulos de `Documentation/triagem-conjunto-teste.md`,
passa cada mensagem pela triagem como se fosse a única da conversa e
compara o nível decidido com o rótulo. Chama a API da Claude de verdade
(uma chamada por mensagem que a camada 1 não resolve sozinha).

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
    for n, texto, esperado in carregar():
        atual["n"] = n
        resultado = triage.assess(texto, [{"role": "user", "content": texto}], PUBLICO_MARILIA)
        obtido = SIGLA[resultado.level if resultado else None]
        camada = resultado.trigger if resultado else "camada2:normal"
        linhas.append((n, texto, esperado, obtido, camada, justificativas.get(n, "")))
        marca = "  " if esperado == obtido else "!!"
        print(f"{marca} {n:>2} esperado {esperado} obtido {obtido}  [{camada}]", flush=True)

    total = len(linhas)
    acertos = sum(1 for _, _, e, o, _, _ in linhas if e == o)
    matriz = Counter((e, o) for _, _, e, o, _, _ in linhas)

    emergencias = [l for l in linhas if l[2] == "E"]
    e_pegas = sum(1 for l in emergencias if l[3] == "E")
    # O erro que importa: risco (D ou E) que não gerou alerta nenhum.
    risco = [l for l in linhas if l[2] in ("D", "E")]
    risco_sem_alerta = [l for l in risco if l[3] in ("N", "S")]
    alarme_falso = [l for l in linhas if l[2] in ("N", "S") and l[3] in ("D", "E")]

    print()
    print(f"Concordância exata: {acertos}/{total}")
    print(f"Emergências reconhecidas como E: {e_pegas}/{len(emergencias)}")
    print(f"Risco (D/E) sem nenhum alerta: {len(risco_sem_alerta)}/{len(risco)}")
    print(f"Alertas em mensagens N/S (alarme falso): {len(alarme_falso)}")
    print()
    print("Matriz (linha = Marília, coluna = sistema)")
    print("     " + "  ".join(ORDEM))
    for e in ORDEM:
        print(f"  {e}  " + "  ".join(str(matriz[(e, o)]) for o in ORDEM))
    print()
    print("Divergências:")
    for n, texto, e, o, camada, just in linhas:
        if e != o:
            print(f"  {n:>2}. [{e}→{o}] {texto}")
            print(f"      {camada}: {just}")


if __name__ == "__main__":
    main()
