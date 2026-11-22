"""Rotulagem independente das 40 mensagens da triagem (item 1 do orientador).

Junta os rótulos da Marília (`Documentation/triagem-conjunto-teste.md`) com
os de duas psicólogas que rotularam sozinhas, sem ver os dela
(`Documentation/resultados-testes/2026-11-21-rotulagem-independente.json`,
já anonimizado: Avaliadora A e Avaliadora B, sem nome nem e-mail), e:

- mede a concordância entre as três (simples, kappa de Fleiss, kappa de
  Cohen por par), nos 4 níveis e nas duas decisões do sistema;
- monta o gabarito por maioria (pelo menos duas iguais; as três diferentes
  = ambígua);
- refaz a comparação só regras × só modelo × híbrido contra esse gabarito,
  usando os níveis já gravados na triagem de 21/11
  (`2026-11-21-triagem-so-modelo.json`). As regras são recalculadas com
  `triage.check_rules`, que não chama a API.

Não chama a API. Uso, a partir de `backend/`:

    python -m scripts.avaliar_rotulagem_independente
"""

import json
import random
from collections import Counter
from pathlib import Path

from app.services import triage
from scripts.avaliar_triagem import ORDEM, SIGLA, carregar
from scripts.avaliar_triagem_so_modelo import (
    CONFIGS,
    DECISOES,
    GRAVIDADE,
    NOME_CONFIG,
    hibrido,
    metricas,
    pct,
    wilson,
)

RESULTADOS = Path(__file__).resolve().parents[2] / "Documentation" / "resultados-testes"
ROTULAGEM = RESULTADOS / "2026-11-21-rotulagem-independente.json"
TRIAGEM = RESULTADOS / "2026-11-21-triagem-so-modelo.json"
SAIDA = RESULTADOS / "2026-11-21-rotulagem-independente.md"

AVALIADORAS = ["M", "A", "B"]
NOME = {"M": "Marília", "A": "Avaliadora A", "B": "Avaliadora B"}
PARES = [("M", "A"), ("M", "B"), ("A", "B")]
NOME_NIVEL = {"N": "normal", "S": "sofrimento intenso", "D": "dúvida", "E": "emergência"}

# Os 4 níveis e as duas decisões do sistema, como funções de agrupamento.
ESCALAS = {
    "niveis": ("4 níveis (N, S, D, E)", lambda x: x),
    "alerta": ("Gera alerta (D ou E) × não gera (N ou S)", lambda x: "sim" if x in ("D", "E") else "não"),
    "emergencia": ("Emergência (E) × não emergência", lambda x: "sim" if x == "E" else "não"),
}

REAMOSTRAS = 10_000
SEMENTE = 20261121


# ---------------------------------------------------------------------------
# Concordância
# ---------------------------------------------------------------------------


def cohen(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def fleiss(colunas: list[list[str]]) -> float:
    """Kappa de Fleiss; `colunas` = uma lista de rótulos por avaliadora."""
    m = len(colunas)
    itens = list(zip(*colunas))
    n = len(itens)
    categorias = sorted({x for c in colunas for x in c})
    p_i = []
    for item in itens:
        c = Counter(item)
        p_i.append((sum(v * v for v in c.values()) - m) / (m * (m - 1)))
    p_barra = sum(p_i) / n
    total = Counter(x for c in colunas for x in c)
    pe = sum((total[k] / (n * m)) ** 2 for k in categorias)
    return float("nan") if pe == 1 else (p_barra - pe) / (1 - pe)


def bootstrap(func, colunas: list[list[str]]) -> tuple[float, float]:
    """IC 95% percentil, reamostrando as mensagens (semente fixa)."""
    rng = random.Random(SEMENTE)
    n = len(colunas[0])
    valores = []
    for _ in range(REAMOSTRAS):
        idx = [rng.randrange(n) for _ in range(n)]
        v = func(*[[c[i] for i in idx] for c in colunas]) if func is not fleiss else fleiss(
            [[c[i] for i in idx] for c in colunas]
        )
        if v == v:  # descarta reamostras em que o kappa não é definido
            valores.append(v)
    valores.sort()
    return valores[int(0.025 * len(valores))], valores[int(0.975 * len(valores)) - 1]


def landis_koch(k: float) -> str:
    if k != k:
        return "não definido"
    if k < 0:
        return "pobre (abaixo do acaso)"
    for limite, nome in ((0.20, "leve"), (0.40, "razoável"), (0.60, "moderada"), (0.80, "substancial")):
        if k <= limite:
            return nome
    return "quase perfeita"


def num(x: float, casas: int = 2) -> str:
    return f"{x:.{casas}f}".replace(".", ",").replace("-", "−")


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


def main() -> None:
    mensagens = carregar()
    numeros = [n for n, _, _ in mensagens]
    textos = [t for _, t, _ in mensagens]
    rot = {"M": [r for _, _, r in mensagens]}
    dados = json.loads(ROTULAGEM.read_text(encoding="utf-8"))
    for k in ("A", "B"):
        rot[k] = dados["avaliadoras"][k]["rotulos"]
        assert len(rot[k]) == 40

    # Gabarito por maioria e quem discordou.
    gabarito, discordancias = [], []
    for i in range(40):
        votos = Counter(rot[k][i] for k in AVALIADORAS)
        nivel, qtd = votos.most_common(1)[0]
        if qtd >= 2:
            gabarito.append(nivel)
            if qtd == 2:
                quem = next(k for k in AVALIADORAS if rot[k][i] != nivel)
                lado = "mais grave" if GRAVIDADE[rot[quem][i]] > GRAVIDADE[nivel] else "menos grave"
                discordancias.append((numeros[i], textos[i], quem, rot[quem][i], nivel, lado))
        else:
            gabarito.append(None)
    ambiguas = [i for i in range(40) if gabarito[i] is None]
    validas = [i for i in range(40) if gabarito[i] is not None]

    # Níveis da triagem de 21/11.
    triagem = json.loads(TRIAGEM.read_text(encoding="utf-8"))
    regras = [SIGLA[(lambda x: x.level if x else None)(triage.check_rules(t))] for t in textos]
    rodadas = []
    for e in triagem["execucoes"]:
        modelo = e["niveis"]
        rodadas.append({"regras": regras, "modelo": modelo, "hibrido": [hibrido(r, m) for r, m in zip(regras, modelo)]})

    L: list[str] = []
    L.append("# Rotulagem independente das 40 mensagens da triagem (21/11/2026)")
    L.append("")
    L.append(
        "Item 1 do feedback do orientador. Duas psicólogas rotularam sozinhas as 40 mensagens sintéticas de "
        "`Documentation/triagem-conjunto-teste.md`, por um formulário com as mensagens em ordem embaralhada e "
        "sem ver os rótulos da Marília. Este relatório compara as três rotulagens, monta um gabarito por "
        "maioria e refaz contra ele a comparação das três configurações da triagem."
    )
    L.append("")
    L.append(
        "As duas avaliadoras (A e B) usaram o texto do [manual de rotulagem](../rotulagem-manual.md); os "
        "rótulos da Marília são de 23/09/2026, anteriores ao manual, que foi escrito a partir dos níveis "
        "definidos por ela."
    )
    L.append("")
    L.append(
        "**Nenhuma chamada à API.** Os níveis do modelo são os já gravados na triagem de 21/11 "
        "(`2026-11-21-triagem-so-modelo.json`, 3 execuções); os das regras são recalculados com "
        "`triage.check_rules`, que é determinístico e local. Gerado por "
        "`backend/scripts/avaliar_rotulagem_independente.py`. Os rótulos anonimizados estão em "
        "`2026-11-21-rotulagem-independente.json`; a planilha original, com nome e e-mail, fica fora do "
        "repositório."
    )
    L.append("")
    L.append("## Avaliadoras")
    L.append("")
    L.append("| | Formação | Experiência clínica | Já atendeu risco à vida? |")
    L.append("|---|---|---|---|")
    L.append("| Marília | Psicanalista (a profissional que definiu os níveis; rótulos de 23/09/2026, anteriores ao manual) | De 5 a 10 anos | — |")
    for k in ("A", "B"):
        p = dados["avaliadoras"][k]["perfil"]
        L.append(f"| {NOME[k]} | {p['formacao']} | {p['experiencia']} | {p['ja_atendeu_risco']} |")
    L.append("")
    L.append(
        "Avaliadora A e Avaliadora B seguem a ordem de envio do formulário. As duas declararam já ter "
        "atendido pessoas em situação de risco à vida (ideação suicida, autolesão, violência)."
    )
    L.append("")

    # 1. Tabela lado a lado
    L.append("## 1. Rótulos lado a lado")
    L.append("")
    L.append("N = normal, S = sofrimento intenso, D = dúvida sobre segurança, E = emergência. "
             "\"Maioria\" é o gabarito da seção 3.")
    L.append("")
    L.append("| Nº | Mensagem | Marília | Aval. A | Aval. B | Maioria |")
    L.append("|---|---|---|---|---|---|")
    for i in range(40):
        g = gabarito[i] or "ambígua"
        iguais = len({rot[k][i] for k in AVALIADORAS}) == 1
        marca = "" if iguais else " ≠"
        L.append(f"| {numeros[i]} | {textos[i]} | {rot['M'][i]} | {rot['A'][i]} | {rot['B'][i]} | {g}{marca} |")
    L.append("")
    L.append("≠ = pelo menos uma avaliadora diferente das outras.")
    L.append("")
    L.append("Distribuição dos rótulos:")
    L.append("")
    L.append("| | N | S | D | E |")
    L.append("|---|---|---|---|---|")
    for k in AVALIADORAS:
        c = Counter(rot[k])
        L.append(f"| {NOME[k]} | " + " | ".join(str(c[x]) for x in ORDEM) + " |")
    cg = Counter(g for g in gabarito if g)
    L.append(f"| Maioria ({len(validas)} não ambíguas) | " + " | ".join(str(cg[x]) for x in ORDEM) + " |")
    L.append("")

    # 2. Concordância
    L.append("## 2. Concordância entre as avaliadoras (antes de qualquer discussão)")
    L.append("")
    L.append(
        f"Kappa com IC 95% por bootstrap ({REAMOSTRAS:,} reamostras das 40 mensagens, semente {SEMENTE}, "
        "percentis 2,5 e 97,5).".replace(",", ".", 1)
    )
    L.append("")
    resumo_kappa = {}
    for chave, (titulo, f) in ESCALAS.items():
        cols = {k: [f(x) for x in rot[k]] for k in AVALIADORAS}
        tres = sum(len({cols[k][i] for k in AVALIADORAS}) == 1 for i in range(40))
        L.append(f"### {titulo}")
        L.append("")
        L.append(f"Concordância simples das três: **{tres}/40 = {pct(tres / 40)}**.")
        L.append("")
        L.append("| Medida | Concordância simples | Kappa | IC 95% | Landis e Koch |")
        L.append("|---|---|---|---|---|")
        kf = fleiss([cols[k] for k in AVALIADORAS])
        lo, hi = bootstrap(fleiss, [cols[k] for k in AVALIADORAS])
        L.append(f"| Fleiss, as três | {tres}/40 ({pct(tres / 40)}) | **{num(kf)}** | {num(lo)} a {num(hi)} | {landis_koch(kf)} |")
        resumo_kappa[(chave, "fleiss")] = kf
        for a, b in PARES:
            kc = cohen(cols[a], cols[b])
            lo, hi = bootstrap(cohen, [cols[a], cols[b]])
            iguais = sum(x == y for x, y in zip(cols[a], cols[b]))
            L.append(
                f"| Cohen, {NOME[a]} × {NOME[b]} | {iguais}/40 ({pct(iguais / 40)}) | **{num(kc)}** | "
                f"{num(lo)} a {num(hi)} | {landis_koch(kc)} |"
            )
            resumo_kappa[(chave, a + b)] = kc
        L.append("")
    L.append(
        "Escala de Landis e Koch (1977) para o kappa: < 0 pobre; 0,00–0,20 leve; 0,21–0,40 razoável; "
        "0,41–0,60 moderada; 0,61–0,80 substancial; 0,81–1,00 quase perfeita. Os próprios autores "
        "apresentam os limites como arbitrários, uma convenção para descrever o valor."
    )
    L.append("")
    L.append("Referências:")
    L.append("")
    L.append("- LANDIS, J. R.; KOCH, G. G. The measurement of observer agreement for categorical data. "
             "*Biometrics*, v. 33, n. 1, p. 159–174, 1977. DOI: 10.2307/2529310.")
    L.append("- FLEISS, J. L. Measuring nominal scale agreement among many raters. *Psychological Bulletin*, "
             "v. 76, n. 5, p. 378–382, 1971. DOI: 10.1037/h0031619.")
    L.append("- COHEN, J. A coefficient of agreement for nominal scales. *Educational and Psychological "
             "Measurement*, v. 20, n. 1, p. 37–46, 1960. DOI: 10.1177/001316446002000104.")
    L.append("- WILSON, E. B. Probable inference, the law of succession, and statistical inference. "
             "*Journal of the American Statistical Association*, v. 22, n. 158, p. 209–212, 1927. "
             "DOI: 10.1080/01621459.1927.10502953 (intervalos da seção 4).")
    L.append("")

    # 3. Gabarito
    L.append("## 3. Gabarito por maioria")
    L.append("")
    L.append(
        f"Nível escolhido por pelo menos duas das três. **{len(validas)} mensagens têm maioria**: "
        f"{len(validas) - len(discordancias)} com as três iguais e {len(discordancias)} com uma "
        f"discordando. **{len(ambiguas)} ambígua(s)** (as três diferentes)."
    )
    L.append("")
    if ambiguas:
        L.append("**Ambíguas** (ficam de fora da seção 4):")
        L.append("")
        L.append("| Nº | Mensagem | Marília | Aval. A | Aval. B |")
        L.append("|---|---|---|---|---|")
        for i in ambiguas:
            L.append(f"| {numeros[i]} | {textos[i]} | {rot['M'][i]} | {rot['A'][i]} | {rot['B'][i]} |")
        L.append("")
    L.append("**Uma discordou:**")
    L.append("")
    L.append("| Nº | Mensagem | Maioria | Quem discordou | Rótulo dela | Lado |")
    L.append("|---|---|---|---|---|---|")
    for n, t, quem, nivel, maioria, lado in discordancias:
        L.append(f"| {n} | {t} | {maioria} | {NOME[quem]} | {nivel} | {lado} |")
    L.append("")
    cont = Counter((d[2], d[5]) for d in discordancias)
    L.append("Quem ficou sozinha, e para que lado:")
    L.append("")
    L.append("| | Mais grave que a maioria | Menos grave que a maioria | Total |")
    L.append("|---|---|---|---|")
    for k in AVALIADORAS:
        L.append(f"| {NOME[k]} | {cont[(k, 'mais grave')]} | {cont[(k, 'menos grave')]} | "
                 f"{cont[(k, 'mais grave')] + cont[(k, 'menos grave')]} |")
    L.append("")
    muda_alerta = [d for d in discordancias if (d[3] in "DE") != (d[4] in "DE")]
    muda_emerg = [d for d in discordancias if (d[3] == "E") != (d[4] == "E")]
    L.append(
        f"Das {len(discordancias)} discordâncias isoladas, {len(muda_alerta)} mudam a decisão de alerta "
        f"(nº {', '.join(str(d[0]) for d in muda_alerta) or '—'}) e {len(muda_emerg)} mudam a decisão de "
        f"emergência (nº {', '.join(str(d[0]) for d in muda_emerg) or '—'}); as demais ficam do mesmo lado "
        "das duas decisões do sistema (por exemplo, N × S)."
    )
    L.append("")
    m_vs_g = [(numeros[i], rot["M"][i], gabarito[i]) for i in validas if rot["M"][i] != gabarito[i]]
    L.append(
        f"Rótulos da Marília que o gabarito por maioria muda: **{len(m_vs_g)}** "
        f"({'; '.join(f'nº {n}: {a} → {b}' for n, a, b in m_vs_g) or 'nenhum'})."
    )
    L.append("")

    # 4. Comparação das configurações
    L.append("## 4. Só regras × só modelo × híbrido contra o gabarito por maioria")
    L.append("")
    L.append(
        f"Base: as **{len(validas)} mensagens com maioria** ({len(ambiguas)} ambígua(s) de fora: "
        f"nº {', '.join(str(numeros[i]) for i in ambiguas) or '—'}). Execução 1 como principal; "
        "entre colchetes, a faixa das 3 execuções (as regras não variam). Na coluna \"Antes\", o "
        "mesmo número contra só a Marília, nas 40 mensagens, como no relatório de 21/11."
    )
    L.append("")
    g_val = [gabarito[i] for i in validas]
    m_all = rot["M"]

    def sub(niveis):
        return [niveis[i] for i in validas]

    def faixa(valores, fmt):
        lo, hi = min(valores), max(valores)
        return "" if lo == hi else f" [{fmt(lo)}–{fmt(hi)}]"

    for chave, (titulo, positivo) in DECISOES.items():
        L.append(f"### {titulo}")
        L.append("")
        pos = sum(g in positivo for g in g_val)
        L.append(f"Gabarito: {pos} positivas e {len(g_val) - pos} negativas (antes, com a Marília: "
                 f"{sum(x in positivo for x in m_all)} e {sum(x not in positivo for x in m_all)}).")
        L.append("")
        L.append("| Configuração | Acertos | FP | FN | Sensibilidade (IC 95%) | Especificidade (IC 95%) | "
                 "Antes: sensibilidade | Antes: especificidade |")
        L.append("|---|---|---|---|---|---|---|---|")
        for cfg in CONFIGS:
            ms = [metricas(g_val, sub(r[cfg]), positivo) for r in rodadas]
            mo = [metricas(m_all, r[cfg], positivo) for r in rodadas]
            m, a = ms[0], mo[0]
            s_lo, s_hi = wilson(m["vp"], m["vp"] + m["fn"])
            e_lo, e_hi = wilson(m["vn"], m["vn"] + m["fp"])
            sens = m["vp"] / (m["vp"] + m["fn"])
            esp = m["vn"] / (m["vn"] + m["fp"])
            inteiro = lambda x: str(x)
            L.append(
                f"| {NOME_CONFIG[cfg]} | {m['acertos']}/{len(g_val)}{faixa([x['acertos'] for x in ms], inteiro)} "
                f"| {m['fp']}{faixa([x['fp'] for x in ms], inteiro)} "
                f"| {m['fn']}{faixa([x['fn'] for x in ms], inteiro)} "
                f"| {m['vp']}/{m['vp'] + m['fn']} = {pct(sens)} ({pct(s_lo)}–{pct(s_hi)})"
                f"{faixa([x['vp'] / (x['vp'] + x['fn']) for x in ms], pct)} "
                f"| {m['vn']}/{m['vn'] + m['fp']} = {pct(esp)} ({pct(e_lo)}–{pct(e_hi)})"
                f"{faixa([x['vn'] / (x['vn'] + x['fp']) for x in ms], pct)} "
                f"| {a['vp']}/{a['vp'] + a['fn']} = {pct(a['vp'] / (a['vp'] + a['fn']))} "
                f"| {a['vn']}/{a['vn'] + a['fp']} = {pct(a['vn'] / (a['vn'] + a['fp']))} |"
            )
        L.append("")

    L.append("### Concordância exata nos 4 níveis")
    L.append("")
    L.append("| Configuração | Contra a maioria | Antes: contra a Marília (40) | Contra a Marília, só nas mesmas "
             f"{len(validas)} |")
    L.append("|---|---|---|---|")
    for cfg in CONFIGS:
        cg_ = [sum(x == y for x, y in zip(g_val, sub(r[cfg]))) for r in rodadas]
        cm = [sum(x == y for x, y in zip(m_all, r[cfg])) for r in rodadas]
        cms = [sum(x == y for x, y in zip(sub(m_all), sub(r[cfg]))) for r in rodadas]
        n_ = len(validas)
        L.append(
            f"| {NOME_CONFIG[cfg]} | {cg_[0]}/{n_} = {pct(cg_[0] / n_)}{faixa(cg_, str)} "
            f"| {cm[0]}/40 = {pct(cm[0] / 40)}{faixa(cm, str)} "
            f"| {cms[0]}/{n_} = {pct(cms[0] / n_)}{faixa(cms, str)} |"
        )
    L.append("")
    L.append(
        "A última coluna separa os dois efeitos: tirar as ambíguas (mesma referência, menos mensagens) e "
        "trocar a referência (Marília → maioria)."
    )
    L.append("")
    L.append("Matriz da execução 1 contra a maioria (linha = gabarito, coluna = configuração):")
    L.append("")
    for cfg in CONFIGS:
        niveis = sub(rodadas[0][cfg])
        mz = Counter(zip(g_val, niveis))
        L.append(f"**{NOME_CONFIG[cfg]}**")
        L.append("")
        L.append("| Maioria \\ Sistema | N | S | D | E | Total |")
        L.append("|---|---|---|---|---|---|")
        for r in ORDEM:
            L.append(f"| **{r}** | " + " | ".join(str(mz[(r, x)]) for x in ORDEM) + f" | {g_val.count(r)} |")
        L.append("| **Total** | " + " | ".join(str(niveis.count(x)) for x in ORDEM) + f" | {len(niveis)} |")
        L.append("")
    L.append("Erros de cada configuração (execução 1) nas duas decisões, contra a maioria:")
    L.append("")
    L.append("| Configuração | Alerta: FP | Alerta: FN | Emergência: FP | Emergência: FN |")
    L.append("|---|---|---|---|---|")
    for cfg in CONFIGS:
        niv = rodadas[0][cfg]
        cel = []
        for positivo in (DECISOES["alerta"][1], DECISOES["emergencia"][1]):
            fp = [numeros[i] for i in validas if gabarito[i] not in positivo and niv[i] in positivo]
            fn = [numeros[i] for i in validas if gabarito[i] in positivo and niv[i] not in positivo]
            cel += [", ".join(map(str, fp)) or "—", ", ".join(map(str, fn)) or "—"]
        L.append(f"| {NOME_CONFIG[cfg]} | " + " | ".join(cel) + " |")
    L.append("")

    # 5. Mensagem 14
    i14 = numeros.index(14)
    L.append("## 5. Mensagem 14: \"tenho pensado muito na morte ultimamente\"")
    L.append("")
    L.append(
        f"Marília: **{NOME_NIVEL[rot['M'][i14]]}** ({rot['M'][i14]}). Avaliadora A: "
        f"**{NOME_NIVEL[rot['A'][i14]]}** ({rot['A'][i14]}). Avaliadora B: **{NOME_NIVEL[rot['B'][i14]]}** "
        f"({rot['B'][i14]}). Maioria: **{gabarito[i14] or 'ambígua'}**."
    )
    L.append("")
    L.append(
        "Triagem de 21/11 nessa mensagem: só regras "
        + rodadas[0]["regras"][i14]
        + ", só modelo "
        + "/".join(r["modelo"][i14] for r in rodadas)
        + ", híbrido "
        + "/".join(r["hibrido"][i14] for r in rodadas)
        + " (execuções 1/2/3)."
    )
    L.append("")

    # 6. Comentários
    L.append("## 6. Comentários do campo opcional")
    L.append("")
    L.append("Pergunta: \"Alguma mensagem foi difícil de classificar? Diga o número e por quê.\" "
             "Sem identificar quem escreveu:")
    L.append("")
    for c in dados["comentarios"]:
        L.append(f"- \"{c}\"")
    L.append("")
    L.append("Nenhuma das duas apontou mensagem específica como difícil.")
    L.append("")

    SAIDA.write_text("\n".join(L), encoding="utf-8")
    print(f"Relatório: {SAIDA}")


if __name__ == "__main__":
    main()
