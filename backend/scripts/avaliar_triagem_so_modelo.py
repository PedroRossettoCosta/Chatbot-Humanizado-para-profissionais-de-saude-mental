"""Compara três configurações da triagem: só regras, só modelo e híbrido.

Pedido do orientador (item 4 do feedback de novembro de 2026): o artigo
comparava "só regras" com o sistema híbrido, mas faltava o "só modelo".

- **Só regras:** `triage.check_rules`, a camada 1 sozinha.
- **Só modelo:** `llm.classify_risk`, a camada 2 sozinha, com o mesmo
  modelo, o mesmo prompt de produção e o mesmo público usado na avaliação
  original (`avaliar_triagem.PUBLICO_MARILIA`). Roda nas 40 mensagens,
  inclusive nas 4 que o híbrido resolve pelas regras sem chamar o modelo.
- **Híbrido:** calculado a partir das duas acima, com a mesma regra de
  `triage.assess` (emergência da camada 1 encerra; senão vale o mais grave
  dos dois). Isso dá exatamente o que `assess` daria com aquela resposta do
  modelo, sem gastar outra chamada.

Nada aqui muda a triagem: o script só chama as funções de produção e
observa o que foi enviado e o que a API devolveu (identificador do modelo,
parâmetros, tokens), para a documentação da avaliação.

Uso, a partir de `backend/`:

    python -m scripts.avaliar_triagem_so_modelo            # 3 execuções
    python -m scripts.avaliar_triagem_so_modelo --execucoes 1

São 40 chamadas à API por execução. O relatório em Markdown sai em
`Documentation/resultados-testes/AAAA-MM-DD-triagem-so-modelo.md`, e as
respostas brutas em um `.json` ao lado.
"""

import argparse
import json
import math
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from app.config import settings
from app.services import llm, triage
from scripts.avaliar_triagem import ORDEM, PUBLICO_MARILIA, SIGLA, carregar

RESULTADOS = Path(__file__).resolve().parents[2] / "Documentation" / "resultados-testes"

DA_CAMADA2 = {"normal": "N", "sofrimento_intenso": "S", "duvida": "D", "emergencia": "E"}
GRAVIDADE = {s: i for i, s in enumerate(ORDEM)}

# As duas decisões que as três configurações conseguem tomar (as regras
# sozinhas nunca dão "sofrimento intenso").
DECISOES = {
    "alerta": ("Gerar alerta (dúvida ou emergência)", {"D", "E"}),
    "emergencia": ("Interromper o fluxo com o texto de emergência", {"E"}),
}
CONFIGS = ["regras", "modelo", "hibrido"]
NOME_CONFIG = {"regras": "Só regras", "modelo": "Só modelo", "hibrido": "Híbrido"}


# ---------------------------------------------------------------------------
# Observação das chamadas (sem alterar o que é enviado)
# ---------------------------------------------------------------------------

chamadas: list[dict] = []


class _Mensagens:
    def __init__(self, real):
        self._real = real

    def parse(self, **kwargs):
        resposta = self._real.parse(**kwargs)
        chamadas.append(
            {
                "modelo_pedido": kwargs.get("model"),
                "modelo_devolvido": getattr(resposta, "model", None),
                "id": getattr(resposta, "id", None),
                "max_tokens": kwargs.get("max_tokens"),
                "output_config": kwargs.get("output_config"),
                "thinking": kwargs.get("thinking"),
                "temperature": kwargs.get("temperature"),
                "stop_reason": resposta.stop_reason,
                "input_tokens": resposta.usage.input_tokens,
                "output_tokens": resposta.usage.output_tokens,
            }
        )
        return resposta


class _Cliente:
    def __init__(self, real):
        self._real = real
        self.messages = _Mensagens(real.messages)

    def with_options(self, **kwargs):
        return _Cliente(self._real.with_options(**kwargs))


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------


def wilson(acertos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (float("nan"), float("nan"))
    p = acertos / total
    centro = (p + z * z / (2 * total)) / (1 + z * z / total)
    margem = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return (centro - margem, centro + margem)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%".replace(".", ",")


def metricas(rotulos: list[str], niveis: list[str], positivo: set[str]) -> dict:
    vp = sum(r in positivo and n in positivo for r, n in zip(rotulos, niveis))
    fn = sum(r in positivo and n not in positivo for r, n in zip(rotulos, niveis))
    fp = sum(r not in positivo and n in positivo for r, n in zip(rotulos, niveis))
    vn = sum(r not in positivo and n not in positivo for r, n in zip(rotulos, niveis))
    return {"vp": vp, "fn": fn, "fp": fp, "vn": vn, "acertos": vp + vn}


def hibrido(regra: str, modelo: str) -> str:
    if regra == "E":
        return "E"
    return max(regra, modelo, key=GRAVIDADE.get)


def matriz_md(rotulos: list[str], niveis: list[str]) -> list[str]:
    m = Counter(zip(rotulos, niveis))
    linhas = ["| Rótulo \\ Sistema | N | S | D | E | Total |", "|---|---|---|---|---|---|"]
    for r in ORDEM:
        linhas.append(f"| **{r}** | " + " | ".join(str(m[(r, n)]) for n in ORDEM) + f" | {rotulos.count(r)} |")
    linhas.append("| **Total** | " + " | ".join(str(niveis.count(n)) for n in ORDEM) + f" | {len(niveis)} |")
    return linhas


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


def executar(mensagens) -> tuple[list[str], list[str]]:
    niveis, justificativas = [], []
    for n, texto, _ in mensagens:
        try:
            c = llm.classify_risk([{"role": "user", "content": texto}], PUBLICO_MARILIA)
            niveis.append(DA_CAMADA2[c.nivel])
            justificativas.append(c.justificativa)
        except Exception as erro:
            # Em produção a falha vira dúvida (falha fechada). Aqui fica
            # marcada para aparecer no relatório, sem esconder.
            niveis.append("D")
            justificativas.append(f"FALHA ({type(erro).__name__}) — contada como D, como em produção")
        print(f"  {n:>2} -> {niveis[-1]}", flush=True)
    return niveis, justificativas


def relatorio(mensagens, execucoes, inicio: datetime) -> str:
    numeros = [n for n, _, _ in mensagens]
    textos = [t for _, t, _ in mensagens]
    rotulos = [r for _, _, r in mensagens]
    regras = [SIGLA[(lambda x: x.level if x else None)(triage.check_rules(t))] for t in textos]
    rodadas = [niveis for niveis, _ in execucoes]
    iguais = all(r == rodadas[0] for r in rodadas)
    modelo = rodadas[0]
    hib = [hibrido(r, m) for r, m in zip(regras, modelo)]
    por_config = {"regras": regras, "modelo": modelo, "hibrido": hib}

    modelos_devolvidos = Counter(c["modelo_devolvido"] for c in chamadas)
    parametros = Counter(
        json.dumps({k: c[k] for k in ("modelo_pedido", "max_tokens", "output_config", "thinking", "temperature")},
                   ensure_ascii=False)
        for c in chamadas
    )
    entrada = sum(c["input_tokens"] for c in chamadas)
    saida = sum(c["output_tokens"] for c in chamadas)

    L = []
    L.append(f"# Triagem: só regras × só modelo × híbrido ({inicio:%d/%m/%Y})")
    L.append("")
    L.append(
        "Gerado por `backend/scripts/avaliar_triagem_so_modelo.py` (item 4 do feedback do orientador). "
        "Mesmas 40 mensagens e rótulos da Marília de "
        "[triagem-conjunto-teste.md](../triagem-conjunto-teste.md); cada mensagem avaliada sozinha, sem "
        "histórico, com o público da Marília, como na avaliação original "
        "([2026-11-03-triagem.md](2026-11-03-triagem.md))."
    )
    L.append("")
    L.append("## Como foi feito")
    L.append("")
    L.append(f"- **Só regras:** `triage.check_rules` (camada 1), sem modelo.")
    L.append(
        f"- **Só modelo:** `llm.classify_risk` (camada 2) nas 40 mensagens, {len(execucoes)} execuções seguidas, "
        f"sem mudar prompt, modelo ou parâmetros de produção. Modelo pedido: `{settings.triage_model}`."
    )
    L.append(
        "- **Híbrido:** calculado com a regra de `triage.assess` a partir das duas colunas acima "
        "(emergência das regras encerra; senão vale o nível mais grave). Nas mensagens 8, 13, 16 e 36 o "
        "sistema real nem chama o modelo, porque as regras já dão emergência; o resultado é o mesmo."
    )
    L.append(
        f"- Início: {inicio:%d/%m/%Y %H:%M}. Chamadas à API: {len(chamadas)}. "
        f"Tokens: {entrada} de entrada, {saida} de saída."
    )
    L.append("- Identificador de modelo devolvido pela API: " +
             ", ".join(f"`{m}` ({q} chamadas)" for m, q in modelos_devolvidos.items()) + ".")
    L.append("- Parâmetros enviados (como o código de produção envia): " +
             "; ".join(f"`{p}` ({q}×)" for p, q in parametros.items()) + ".")
    falhas = sum(j.startswith("FALHA") for _, js in execucoes for j in js)
    L.append(f"- Falhas da chamada (contadas como D, como em produção): {falhas}.")
    L.append("")
    L.append("## Estabilidade das execuções do só modelo")
    L.append("")
    if iguais:
        L.append(f"As {len(execucoes)} execuções deram **exatamente o mesmo nível** nas 40 mensagens. "
                 "As tabelas abaixo valem para qualquer uma delas.")
    else:
        L.append(f"As {len(execucoes)} execuções **não** foram idênticas. As matrizes, as tabelas de decisão e a "
                 "tabela pareada usam a execução 1, que nesta rodada é a mais favorável ao só modelo; para o texto, "
                 "use a faixa entre execuções da tabela logo abaixo. As diferenças estão aqui:")
        L.append("")
        L.append("| Nº | Rótulo | " + " | ".join(f"Exec. {i + 1}" for i in range(len(rodadas))) + " |")
        L.append("|---|---|" + "---|" * len(rodadas))
        for i, n in enumerate(numeros):
            if len({r[i] for r in rodadas}) > 1:
                L.append(f"| {n} | {rotulos[i]} | " + " | ".join(r[i] for r in rodadas) + " |")
    L.append("")
    L.append("")
    L.append("Resultado de cada execução (o só regras não muda entre execuções):")
    L.append("")
    L.append("| Execução | Config. | Concordância exata | Alerta: FP / FN | Alerta: sens. / espec. | Emergência: FP / FN | Emergência: sens. / espec. |")
    L.append("|---|---|---|---|---|---|---|")
    for i, rodada in enumerate(rodadas):
        for cfg, niveis in (("modelo", rodada), ("hibrido", [hibrido(r, m) for r, m in zip(regras, rodada)])):
            a = metricas(rotulos, niveis, DECISOES["alerta"][1])
            e = metricas(rotulos, niveis, DECISOES["emergencia"][1])
            L.append(
                f"| {i + 1} | {NOME_CONFIG[cfg]} | {sum(r == n for r, n in zip(rotulos, niveis))}/40 | "
                f"{a['fp']} / {a['fn']} | {a['vp']}/{a['vp'] + a['fn']} / {a['vn']}/{a['vn'] + a['fp']} | "
                f"{e['fp']} / {e['fn']} | {e['vp']}/{e['vp'] + e['fn']} / {e['vn']}/{e['vn'] + e['fp']} |"
            )
    L.append("")
    L.append("## Matriz 4×4 do só modelo (linha = rótulo da profissional, coluna = nível dado)")
    L.append("")
    L += matriz_md(rotulos, modelo)
    L.append("")
    L.append(f"Concordância exata: {sum(r == m for r, m in zip(rotulos, modelo))}/40.")
    L.append("")
    L.append("Para comparação, as matrizes das outras duas configurações nesta mesma rodada:")
    L.append("")
    L.append("**Só regras**")
    L.append("")
    L += matriz_md(rotulos, regras)
    L.append("")
    L.append("**Híbrido**")
    L.append("")
    L += matriz_md(rotulos, hib)
    L.append("")

    for chave, (titulo, positivo) in DECISOES.items():
        pos = sum(r in positivo for r in rotulos)
        L.append(f"## Decisão: {titulo.lower()}")
        L.append("")
        L.append(
            f"Positivo = rótulo {' ou '.join(sorted(positivo))} ({pos} mensagens); negativo = as outras "
            f"{40 - pos}. IC 95% de Wilson."
        )
        L.append("")
        L.append("| Configuração | Acertos | Falsos positivos | Falsos negativos | Sensibilidade (IC 95%) | Especificidade (IC 95%) |")
        L.append("|---|---|---|---|---|---|")
        for cfg in CONFIGS:
            m = metricas(rotulos, por_config[cfg], positivo)
            s_lo, s_hi = wilson(m["vp"], m["vp"] + m["fn"])
            e_lo, e_hi = wilson(m["vn"], m["vn"] + m["fp"])
            L.append(
                f"| {NOME_CONFIG[cfg]} | {m['acertos']}/40 | {m['fp']} | {m['fn']} | "
                f"{m['vp']}/{m['vp'] + m['fn']} = {pct(m['vp'] / (m['vp'] + m['fn']))} "
                f"({pct(s_lo)}–{pct(s_hi)}) | "
                f"{m['vn']}/{m['vn'] + m['fp']} = {pct(m['vn'] / (m['vn'] + m['fp']))} "
                f"({pct(e_lo)}–{pct(e_hi)}) |"
            )
        L.append("")
        certo = {cfg: [(n in positivo) == (r in positivo) for r, n in zip(rotulos, por_config[cfg])]
                 for cfg in CONFIGS}
        m_corrige = [numeros[i] for i in range(40) if not certo["regras"][i] and certo["modelo"][i]]
        r_corrige = [numeros[i] for i in range(40) if certo["regras"][i] and not certo["modelo"][i]]
        ambos = [numeros[i] for i in range(40) if not certo["regras"][i] and not certo["modelo"][i]]
        L.append(f"- O modelo acertou onde as regras erraram: **{len(m_corrige)}** (nº {', '.join(map(str, m_corrige)) or '—'}).")
        L.append(f"- As regras acertaram onde o modelo errou: **{len(r_corrige)}** (nº {', '.join(map(str, r_corrige)) or '—'}).")
        L.append(f"- Os dois erraram: {len(ambos)} (nº {', '.join(map(str, ambos)) or '—'}).")
        L.append("")

    L.append("## Decisões pareadas, mensagem a mensagem")
    L.append("")
    L.append("Nível de cada configuração; A = gera alerta (D/E), X = texto de emergência (E). "
             "Um ✗ marca a decisão de alerta ou de emergência que diverge do rótulo.")
    L.append("")
    L.append("| Nº | Mensagem | Rótulo | Só regras | Só modelo | Híbrido |")
    L.append("|---|---|---|---|---|---|")

    def celula(rotulo, nivel):
        marcas = []
        for _, (_, positivo) in DECISOES.items():
            if (rotulo in positivo) != (nivel in positivo):
                marcas.append("✗")
        flags = ("A" if nivel in {"D", "E"} else "") + ("X" if nivel == "E" else "")
        return f"{nivel}{' ' + flags if flags else ''}{' ' + ''.join(marcas) if marcas else ''}"

    for i, n in enumerate(numeros):
        texto = textos[i].replace("|", "\\|")
        L.append(f"| {n} | {texto} | {rotulos[i]} | " +
                 " | ".join(celula(rotulos[i], por_config[c][i]) for c in CONFIGS) + " |")
    L.append("")
    L.append("## Justificativas do modelo (execução 1)")
    L.append("")
    for i, n in enumerate(numeros):
        L.append(f"- **{n}** [{rotulos[i]}→{modelo[i]}] {execucoes[0][1][i]}")
    L.append("")
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execucoes", type=int, default=3)
    parser.add_argument("--refazer-relatorio", type=Path, help="refaz o .md a partir do .json, sem chamar a API")
    args = parser.parse_args()

    mensagens = carregar()
    if args.refazer_relatorio:
        dados = json.loads(args.refazer_relatorio.read_text(encoding="utf-8"))
        chamadas.extend(dados["chamadas"])
        execucoes = [(e["niveis"], e["justificativas"]) for e in dados["execucoes"]]
        texto = relatorio(mensagens, execucoes, datetime.fromisoformat(dados["inicio"]))
        args.refazer_relatorio.with_suffix(".md").write_text(texto, encoding="utf-8")
        print(f"Relatório refeito: {args.refazer_relatorio.with_suffix('.md')}")
        return

    llm._client = _Cliente(llm._client)
    inicio = datetime.now()
    execucoes = []
    for i in range(args.execucoes):
        print(f"Execução {i + 1}", flush=True)
        execucoes.append(executar(mensagens))

    RESULTADOS.mkdir(exist_ok=True)
    base = RESULTADOS / f"{date.today():%Y-%m-%d}-triagem-so-modelo"
    base.with_suffix(".md").write_text(relatorio(mensagens, execucoes, inicio), encoding="utf-8")
    base.with_suffix(".json").write_text(
        json.dumps(
            {"inicio": inicio.isoformat(), "execucoes": [{"niveis": n, "justificativas": j} for n, j in execucoes],
             "chamadas": chamadas},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    print(f"Relatório: {base.with_suffix('.md')}")


if __name__ == "__main__":
    main()
