# Custo do modelo

> Situação: funcionando (medição e cache); sem tela no painel. Última atualização: 12/10/2026.

## O que é
A SelenIA guarda quantos tokens cada chamada ao modelo usou, sem guardar
o texto, e um script transforma isso em custo por mês e por conversa. A
parte do prompt que não muda entre mensagens vai com cache, que custa
10% do preço normal nas chamadas seguintes.

## Por que existe
- **Feedback da apresentação de 30/09/2026:** avaliar o custo da solução
  no dia a dia. A estimativa de 12/10 (cerca de R$ 1,20 de modelo por
  conversa, R$ 90 a 160 por mês para uma profissional com 60 conversas,
  com hospedagem) era um chute; esta medição dá o número real para o TCC.
- **Cache (12/10/2026):** é a economia sem perda de qualidade. A estimativa
  era cortar 30 a 40% do custo das respostas; o script mostra quanto da
  entrada veio do cache para confirmar.
- **Teto de custo da conta inteira: não entra** (Pedro, 12/10/2026). Um
  teto da conta podia travar o atendimento de todo mundo num dia
  movimentado; ficam só os [limites por pessoa](limites-por-contato.md).

## Como usar
Não há tela. De dentro de `backend/`, com o venv ativado:

```bash
python scripts/custo.py                 # últimos 30 dias
python scripts/custo.py --dias 7 --dolar 5.50
```

Mostra, por profissional: chamadas e custo da resposta e da triagem,
quanto da entrada veio do cache, total, número de conversas e custo
médio por conversa.

## Como funciona
- `services/llm.py`: depois de cada chamada (cada rodada de ferramenta
  da resposta e a camada 2 da triagem), `_note_usage` anota modelo e
  tokens, se houver um `collect_usage()` aberto.
- `services/pipeline.py` abre `collect_usage()` em volta da triagem e da
  resposta, e `services/usage.py` grava as linhas em `llm_usage`. Uma
  falha ao gravar nunca derruba a resposta.
- Cache: o prompt é dividido em duas partes no título
  `CONTEXTO DA BASE DE CONHECIMENTO`. Tudo antes (papel, limites, nunca
  dizer, perfil, valores, horários, tom e exemplos) vai com
  `cache_control`; os trechos do RAG, que mudam a cada pergunta, vão
  depois, sem cache. As ferramentas da agenda vêm antes do sistema na
  ordem do cache e também são fixas.
- Preços em `scripts/custo.py` (`PRICES`), conferidos em 12/10/2026.

## Textos fixos
Não se aplica.

## Configuração
Nenhuma variável nova. O modelo de cada chamada vem de `CLAUDE_MODEL` e
`TRIAGE_MODEL`; um modelo fora da tabela de preços aparece com custo "?".

## Segurança e LGPD
A tabela guarda só números, o modelo e as ligações com profissional e
conversa: nenhum texto. Quando a retenção apaga uma conversa, as linhas
ficam sem a conversa (`conversation_id` nulo), sem dado pessoal.

## Limitações e pendências
- Não inclui a Meta: desde 01/10/2026 as respostas no WhatsApp são
  cobradas (cerca de US$ 0,0068 cada no Brasil), com franquia relatada
  de ~1.000 por mês por número. Nem a hospedagem.
- **O cache ainda não foi conferido com chamada real.** Se a parte fixa
  do prompt for menor que o mínimo do modelo para cache, a API ignora o
  pedido sem erro; o script mostra 0% vindo do cache. Conferir depois
  das primeiras conversas.
- A triagem não usa cache: o prompt dela é curto, provavelmente abaixo
  do mínimo.
- Sem tela no painel; o número sai pelo script.

## Como testar
Automático: `tests/test_usage.py` (uma linha por chamada, sem conteúdo;
parte fixa com cache; nada anotado fora de `collect_usage`).

Manual: depois de reiniciar o backend, converse duas ou três vezes pelo
simulador e rode `python scripts/custo.py --dias 1`. Da segunda mensagem
em diante, a parte vinda do cache deve ser maior que zero.

## Histórico
- 12/10/2026: primeira versão (tokens por chamada, script de custo,
  cache da parte fixa do prompt).
