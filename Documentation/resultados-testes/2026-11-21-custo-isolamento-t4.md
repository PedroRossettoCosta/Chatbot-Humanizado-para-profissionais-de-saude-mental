# Custo por resposta, testes de isolamento e a tarefa T4 (21/11/2026)

Mais uma rodada do feedback do orientador. Sem chamada à API e sem mudar o
comportamento do sistema. Só foram acrescentados testes, um script de
leitura e correções de comentário e de documentação.

## 1. Custo por resposta e por mensagem

**Fonte:** tabela `llm_usage` do banco local, de 13/10 a 05/11/2026 (238
chamadas: 106 de triagem e 132 de resposta, 9 conversas de teste). Os
preços estão em `scripts/custo.py`.

**Como as chamadas foram agrupadas:** uma resposta com ferramenta faz mais
de uma chamada ao modelo. As chamadas de uma mesma resposta são gravadas
juntas, no mesmo `commit`, e ficam com o mesmo horário. Por isso, chamadas
da mesma conversa a menos de 1 segundo uma da outra contam como uma
resposta. Entre respostas diferentes, o menor intervalo encontrado foi de
7,7 segundos. Para refazer a conta:
`python -m scripts.custo_por_resposta`.

| | Por chamada (média / mediana) | Por unidade (média / mediana) | Unidades | Chamadas por unidade |
|---|---|---|---|---|
| **Triagem** (unidade = mensagem) | US$ 0,0108 / 0,0107 | **US$ 0,0108 / 0,0107** por mensagem | 106 mensagens | sempre 1 |
| **Resposta** (unidade = resposta) | US$ 0,0069 / 0,0053 | **US$ 0,0098 / 0,0063** por resposta | 93 respostas | 1 em 61; 2 em 25; 3 em 7 |

- **Respostas com mais de uma chamada:** 32 de 93 (34%), com média de
  US$ 0,0159 cada.
- **Respostas de uma chamada:** média de US$ 0,0067.
- **Média maior que a mediana nas respostas:** as respostas com
  ferramenta puxam a média para cima.

### De onde saíram os valores do artigo (US$ 0,0103 e US$ 0,0119)

**O de US$ 0,0119 não se confirma.**

- **Explicação mais provável:** os dois valores vêm de uma amostra menor e
  mais antiga. Nos primeiros dias da medição, a resposta saía mais cara
  por haver poucas respostas, várias com ferramenta, e a triagem saía um
  pouco mais barata.
- **Nenhum recorte reproduz exatamente o par 0,0103 e 0,0119.**
- **O custo por resposta só chega perto de 0,0119 em recortes pequenos:**
  - US$ 0,0128 a 0,0129 por resposta até 15/10 (8 respostas);
  - US$ 0,0126 no simulador (21 respostas);
  - US$ 0,0113 numa conversa de WhatsApp de 04/11 (12 respostas).
- **Com as 93 respostas, o custo é US$ 0,0098 por resposta.** Ou seja,
  0,0119 já era custo por resposta, e não por chamada. A diferença para o
  US$ 0,0070 da checagem anterior é justamente o agrupamento.
- **O de US$ 0,0103 na triagem está próximo do medido:** dá 0,0100 a 0,0102
  até 18/10 e **0,0108** com as 106 mensagens.

**Valores confirmados para o artigo:** US$ 0,0108 por mensagem na triagem
e US$ 0,0098 por resposta.

### Custo mensal no mesmo cenário

**Premissas:**

- 350 mensagens recebidas por mês, todas pela triagem;
- 280 respostas;
- WhatsApp e e-mail a US$ 0;
- 1 profissional: Railway Hobby (US$ 5) e Vercel Hobby (US$ 0);
- 50 profissionais: planos Pro da Railway e da Vercel divididos por 50,
  US$ 0,40 cada um por profissional (US$ 0,80 de infraestrutura).

**Conta do modelo:**

| | Artigo (0,0103 e 0,0119) | Confirmado (0,0108 e 0,0098) |
|---|---|---|
| Triagem | 350 × 0,0103 = US$ 3,605 | 350 × 0,0108 = **US$ 3,78** |
| Resposta | 280 × 0,0119 = US$ 3,332 | 280 × 0,0098 = **US$ 2,74** |
| **Modelo por mês** | **US$ 6,94** | **US$ 6,52** |

**Custo mensal por profissional** (corrigido em 21/11/2026: a primeira
versão desta tabela esqueceu a Vercel no cenário de 50 profissionais e
comparava com valores do artigo que não eram os dele):

| Cenário | Confirmado | Artigo dizia |
|---|---|---|
| **1 profissional** | 3,78 (triagem) + 2,74 (respostas) + 5,00 (Railway Hobby) + 0 (Vercel Hobby) = **US$ 11,52** | US$ 11,93 |
| **50 profissionais** | 3,78 + 2,74 + 0,40 (Railway Pro ÷ 50) + 0,40 (Vercel Pro ÷ 50) = **US$ 7,32** por profissional, **US$ 366,00** no total | US$ 7,73 |

Os valores do artigo usavam 0,0103 e 0,0119, com a Vercel incluída. Com
as médias sem arredondar (0,010796 e 0,009841), o modelo dá US$ 6,53 por
mês, e o total de 50 profissionais fica em US$ 366,70. A diferença está
dentro do arredondamento.

**Ressalvas:**

- **Amostra pequena e de teste:** são 9 conversas, de teste.
- **Média e mediana divergem:** com a mediana por resposta (US$ 0,0063), a
  resposta custaria US$ 1,76 por mês, e não US$ 2,74.
- **A tabela usa a média de propósito:** ela inclui o custo das respostas
  com agenda e é mais conservadora.

### Média por conversa (confirmada)

Com as mesmas 238 chamadas, a média é **US$ 0,229 por conversa** (mediana
US$ 0,184), em **9 conversas**, com **13,6 mensagens do contato** por
conversa em média (mediana 11; de 1 a 31). Arredondado: US$ 0,23, mediana
US$ 0,18. O valor de US$ 0,13 continua sem origem confirmada
([checagens](2026-11-21-checagens-artigo.md), item c).

## 2. Testes de isolamento e total de testes

Dois testes novos, sem mudar código de produção:

- **(a) RAG:** `tests/test_rag_isolation.py`, com um ChromaDB de verdade
  numa pasta temporária e uma função de embedding simples, sem baixar
  modelo.
  - `test_query_of_one_professional_never_returns_another_ones_chunks`
    grava documentos de duas profissionais (e de uma terceira com slug
    parecido) e busca na coleção de uma com o texto exato da outra. Volta
    só o material da própria. Apagar o documento de uma não mexe no da
    outra.
  - `test_reply_prompt_only_carries_the_professionals_own_documents` envia
    os documentos pela rota real e conversa com B pelo simulador,
    perguntando o que está no material de A. O prompt da resposta de B tem
    o material de B e não tem o de A.
- **(b) Rotas por id:** `test_routes_by_id_refuse_another_professional`, em
  `tests/test_auth.py`. A profissional B chama, com os ids da profissional
  A: aprovar pedido de horário, recusar pedido de horário, revisar alerta,
  liberar conversa e apagar documento. **As 5 rotas respondem 404** e o
  teste confere que nada mudou no banco: pedido ainda provisório, alerta
  sem revisão, conversa no mesmo estado, documento ainda lá.

**Os dois testes novos passam.** O
[modelo de ameaças](../modelo-de-ameacas.md) foi atualizado: as duas
lacunas saíram de "O que não está coberto", e as linhas da tabela citam
os testes.

### Suíte inteira

**320 testes: 319 passam, 1 falha.** Antes desta rodada eram 318.
(**Atualização, 21/11/2026:** o teste que falhava foi ajustado à regra
atual, como descrito abaixo, e **os 320 passam**.)

O que falha é um teste antigo, não um dos novos:
`tests/test_handoff.py::test_every_emergency_alert_must_be_reviewed`.

- **O que o teste espera:** duas mensagens de emergência na mesma conversa
  geram dois alertas, e liberar exige revisar os dois. Ele quebra ao
  desempacotar os alertas: só há 1.
- **Quando começou a falhar:** conferido numa cópia temporária do
  repositório.
  - Passa em `66ab566` (14/11/2026), o commit que criou o teste.
  - Falha a partir de `35c9021` (19/11/2026), "Espera de emergência:
    mensagem nova não abre outro alerta". Esse commit fez a segunda
    mensagem, durante a espera, não abrir alerta novo.
  - **Já falhava antes desta rodada**, no último commit (`a75f653`).
- **O que está em conflito:** o teste e a regra de 19/11. Cabe ao Pedro
  decidir o que vale:
  - ajustar o teste à regra nova; ou
  - rever a regra para o caso de uma emergência **nova** durante a espera.
    Hoje ela não gera alerta nem e-mail; a pessoa recebe de novo o texto
    fixo.
- **Não corrigi nada**, como pedido.
- **Decisão do Pedro (21/11/2026): manter a regra de 35c9021.** O teste
  virou `test_new_emergency_during_hold_repeats_the_text_and_release_still_needs_review`,
  sem mudar código de produção. Ele confere:
  - uma segunda mensagem de emergência durante a espera não cria alerta
    nem e-mail;
  - o texto fixo de emergência sai de novo;
  - a SelenIA só é liberada depois que o alerta da conversa é revisado.

  Ele não foi removido porque os outros testes não cobriam tudo:
  - `test_release_after_emergency_needs_review_first` (test_handoff) cobre
    "liberar exige revisar";
  - `test_message_during_emergency_hold_repeats_the_text_without_a_new_alert`
    (test_triage_fragments) usa uma mensagem neutra e não confere o
    e-mail. A segunda mensagem *grave* não estava coberta.

  A limitação (uma piora durante a espera não gera novo aviso) está em
  [triagem de segurança](../funcionalidades/triagem-de-seguranca.md) e no
  [modelo de ameaças](../modelo-de-ameacas.md).

## 3. Tarefa T4 da validação de 03/11 ("Erro para clientes especiais")

No [registro da sessão](2026-11-03-sessao-validacao.md), a T4 ("Confirmar
o horário pedido no cenário 5") foi feita sozinha, com a anotação "Erro
para clientes especiais". **O registro não diz qual foi o erro**, e nenhum
commit cita a T4.

**O que o git mostra perto de 03/11:** só há dois commits entre 28/10 e
10/11.

- **`a69c8b4`, 05/11/2026 00:18** (trabalho de 03 e 04/11), "SelenIA: 'Em
  consulta' pela agenda e cliente especial sem restrição de horário". É a
  única correção ligada a clientes especiais e a pedido de horário no
  período. A mensagem do commit atribui a parte de cliente especial a um
  "teste de 04/11", feito pelo Pedro no simulador, e não à sessão de
  03/11. Corrigiu três coisas:
  1. **A condição especial dependia de o modelo chamar a ferramenta.** Se
     a profissional ligava "cliente especial" com a conversa em andamento,
     a SelenIA podia repetir a lista de horários de antes, de quando a
     pessoa ainda não era especial. Passou a ler a agenda e a permissão a
     cada mensagem sobre horário (`pipeline._about_scheduling`, seção
     "HORÁRIOS DE AGORA" do prompt).
  2. **A antecedência mínima de 12 horas valia também para cliente
     especial.** Um pedido para "daqui a 30 minutos" foi trocado pelas
     23:00 do dia seguinte no teste. Ela deixou de valer para cliente
     especial.
  3. **Pedido provisório podia vencer depois da hora da sessão.** Passou a
     vencer na hora da sessão, e a pessoa é avisada.
- **`614cb05`, 05/11/2026 01:25**, "Formas de pagamento passam a ser
  obrigatórias". Não tem relação com clientes especiais.

**Testes que cobrem a correção** (`tests/test_clients.py`, criados em
`a69c8b4`):

- `test_turning_on_special_mid_conversation_reaches_the_next_message_without_the_tool`
- `test_special_clients_have_no_minimum_notice`
- `test_no_minimum_notice_also_applies_outside_special_days`
- `test_list_warns_that_short_notice_requests_are_outside_it`
- `test_short_notice_request_emails_right_away_even_in_session`
- `test_expired_request_tells_the_person_through_the_conversation`

**Conclusão:** a correção mais provável é `a69c8b4` (05/11/2026), mas
**não dá para afirmar** que ela corrige o erro anotado na T4. Pelos
registros, o "erro para clientes especiais" pode ser o da condição
especial que não chegava à conversa em andamento (item 1 acima). Só quem
anotou consegue confirmar. Na tela de confirmação do pedido
(`/calendar/appointments/{id}/approve`) não houve mudança perto de 03/11.
