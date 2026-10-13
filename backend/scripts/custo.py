"""Resumo do custo real das chamadas ao modelo (tabela `llm_usage`).

Mostra, por profissional e no período pedido: quantas chamadas, tokens,
custo da resposta e da triagem, quantas conversas e o custo médio por
conversa. Os preços estão em `PRICES` (dólar por milhão de tokens, tabela
da Anthropic conferida em 12/10/2026); modelo fora da tabela aparece
com custo "?".

Não inclui a Meta (mensagens de serviço cobradas desde 01/10/2026, com
franquia de ~1.000 por mês por número) nem a hospedagem. Ver a seção
de custos do TCC.

Uso (de dentro de backend/, com o venv ativado):
    python scripts/custo.py               # últimos 30 dias
    python scripts/custo.py --dias 7
    python scripts/custo.py --dolar 5.50  # também em reais
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402

# Dólar por milhão de tokens: entrada sem cache, leitura do cache,
# escrita no cache (1,25x a entrada) e saída.
PRICES = {
    "claude-sonnet-5": {"input": 2.00, "cache_read": 0.20, "cache_write": 2.50, "output": 10.00},
    "claude-sonnet-5-5": {"input": 2.00, "cache_read": 0.20, "cache_write": 2.50, "output": 10.00},
    "claude-opus-5": {"input": 5.00, "cache_read": 0.50, "cache_write": 6.25, "output": 25.00},
    "claude-opus-5-5": {"input": 4.00, "cache_read": 0.20, "cache_write": 5.00, "output": 20.00},
    "claude-haiku-5-5": {"input": 0.10, "cache_read": 0.01, "cache_write": 0.125, "output": 0.50},
}


def cost(row: models.LlmUsage) -> float | None:
    price = PRICES.get(row.model)
    if price is None:
        return None
    return (
        row.input_tokens * price["input"]
        + row.cache_read_tokens * price["cache_read"]
        + row.cache_write_tokens * price["cache_write"]
        + row.output_tokens * price["output"]
    ) / 1_000_000


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dias", type=int, default=30)
    parser.add_argument("--dolar", type=float, default=None, help="cotação para mostrar em reais")
    args = parser.parse_args()

    since = datetime.now(timezone.utc) - timedelta(days=args.dias)
    db = SessionLocal()
    try:
        rows = db.query(models.LlmUsage).filter(models.LlmUsage.created_at >= since).all()
        names = {p.id: p.name for p in db.query(models.Professional).all()}
    finally:
        db.close()

    if not rows:
        print(f"Nenhuma chamada registrada nos últimos {args.dias} dias.")
        return

    by_professional = defaultdict(list)
    for row in rows:
        by_professional[row.professional_id].append(row)

    def money(value):
        if value is None:
            return "?"
        text = f"US$ {value:.4f}"
        if args.dolar:
            text += f" (R$ {value * args.dolar:.2f})"
        return text

    print(f"Custo do modelo nos últimos {args.dias} dias\n")
    for professional_id, items in by_professional.items():
        print(names.get(professional_id, professional_id))
        unknown = False
        totals = {}
        for purpose in ("reply", "triage"):
            part = [r for r in items if r.purpose == purpose]
            costs = [cost(r) for r in part]
            unknown |= None in costs
            totals[purpose] = sum(c for c in costs if c is not None)
            tokens_in = sum(r.input_tokens + r.cache_read_tokens + r.cache_write_tokens for r in part)
            cached = sum(r.cache_read_tokens for r in part)
            share = f", {100 * cached / tokens_in:.0f}% da entrada veio do cache" if tokens_in else ""
            label = "Resposta" if purpose == "reply" else "Triagem "
            print(f"  {label}: {len(part)} chamadas, {money(totals[purpose])}{share}")
        total = totals["reply"] + totals["triage"]
        conversations = {r.conversation_id for r in items if r.conversation_id}
        print(f"  Total   : {money(total)}{' (há modelo sem preço na tabela)' if unknown else ''}")
        if conversations:
            print(f"  Conversas: {len(conversations)}, média de {money(total / len(conversations))} por conversa")
        print()


if __name__ == "__main__":
    main()
