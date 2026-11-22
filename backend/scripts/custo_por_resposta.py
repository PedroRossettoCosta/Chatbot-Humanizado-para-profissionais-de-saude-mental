"""Custo por resposta e por mensagem, a partir da tabela `llm_usage`.

Uma resposta com ferramenta (consulta à agenda, pedido de horário) faz
mais de uma chamada ao modelo. As chamadas de uma mesma resposta são
gravadas juntas, no mesmo `commit` (`services/usage.record`), com o mesmo
horário; este script junta as chamadas de uma conversa gravadas a menos
de 1 segundo uma da outra. A triagem faz uma chamada por mensagem.

Só lê o banco; não chama a API. Preços em `scripts/custo.py` (`PRICES`).

Uso, a partir de `backend/`:

    python -m scripts.custo_por_resposta                          # 13/10 a 05/11/2026
    python -m scripts.custo_por_resposta --de 2026-10-13 --ate 2026-11-06
"""

import argparse
from collections import Counter
from statistics import mean, median

from sqlalchemy import text

from app.database import SessionLocal
from scripts.custo import PRICES

MESMA_RESPOSTA_SEGUNDOS = 1.0


def custo(r) -> float:
    p = PRICES[r.model]
    return (
        r.input_tokens * p["input"]
        + r.cache_read_tokens * p["cache_read"]
        + r.cache_write_tokens * p["cache_write"]
        + r.output_tokens * p["output"]
    ) / 1_000_000


def agrupar(linhas, finalidade: str) -> list[list]:
    grupos: list[list] = []
    for r in linhas:
        if r.purpose != finalidade:
            continue
        ultimo = grupos[-1][-1] if grupos else None
        if (
            ultimo is not None
            and ultimo.conversation_id == r.conversation_id
            and (r.created_at - ultimo.created_at).total_seconds() < MESMA_RESPOSTA_SEGUNDOS
        ):
            grupos[-1].append(r)
        else:
            grupos.append([r])
    return grupos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--de", default="2026-10-13")
    parser.add_argument("--ate", default="2026-11-06", help="exclusivo")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        linhas = db.execute(
            text(
                "select conversation_id, purpose, model, input_tokens, cache_read_tokens, cache_write_tokens, "
                "output_tokens, created_at from llm_usage where created_at >= :de and created_at < :ate "
                "order by conversation_id, created_at"
            ),
            {"de": args.de, "ate": args.ate},
        ).fetchall()
    finally:
        db.close()

    print(f"llm_usage de {args.de} até {args.ate} (exclusivo): {len(linhas)} chamadas\n")
    for finalidade, unidade in (("triage", "mensagem"), ("reply", "resposta")):
        grupos = agrupar(linhas, finalidade)
        chamadas = [custo(r) for g in grupos for r in g]
        por_grupo = [sum(custo(r) for r in g) for g in grupos]
        nome = "Triagem" if finalidade == "triage" else "Resposta"
        print(f"{nome}: {len(chamadas)} chamadas, {len(grupos)} por {unidade}")
        print(f"  por chamada: média US$ {mean(chamadas):.4f}, mediana US$ {median(chamadas):.4f}")
        print(f"  por {unidade}: média US$ {mean(por_grupo):.4f}, mediana US$ {median(por_grupo):.4f}")
        distribuicao = sorted(Counter(len(g) for g in grupos).items())
        print(f"  chamadas por {unidade}: {', '.join(f'{n} chamada(s): {q}' for n, q in distribuicao)}")
        varias = [sum(custo(r) for r in g) for g in grupos if len(g) > 1]
        if varias:
            print(f"  com mais de uma chamada: {len(varias)} de {len(grupos)}, média US$ {mean(varias):.4f}")
        print(f"  total US$ {sum(chamadas):.4f}\n")


if __name__ == "__main__":
    main()
