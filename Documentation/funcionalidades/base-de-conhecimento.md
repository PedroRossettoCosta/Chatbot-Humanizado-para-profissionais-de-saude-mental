# Base de conhecimento

> Situação: funcionando. Última atualização: 27/09/2026.

## O que é

Os documentos que a profissional envia (abordagem, perguntas
frequentes, informações práticas) para a MarIA responder dúvidas sobre
o trabalho dela com base no que está escrito, e não inventando.

## Por que existe

Desde o começo do projeto (`planejamento-projeto.md`), a MarIA responde
com RAG: busca os trechos dos documentos mais parecidos com a pergunta
e manda junto para o modelo. Assim a resposta fica presa ao material da
profissional. Em 27/09/2026 a tela ganhou o visual do protótipo e o
botão de remover documento, que não existia.

## Como usar

1. No painel, abra **Base de conhecimento**.
2. Arraste arquivos para a área de envio ou clique em **Selecionar do
   computador**. Aceita PDF, DOCX, TXT e MD, até 10 MB, vários de uma vez.
3. Cada documento aparece na lista com o tipo, o número de trechos e a
   data. Enquanto é processado, mostra "Processando…".
4. Para remover, clique na lixeira e confirme em **Sim**.
5. Use **Testar a MarIA** para ver a resposta usando o documento: a
   etiqueta "Com base em: arquivo" mostra de onde veio.

## Como funciona

- Envio: `POST /documents/upload`. O texto é extraído
  (`services/text_extraction.py`), dividido em trechos e indexado no
  ChromaDB, numa coleção só da profissional (`prof-{slug}`). O registro
  fica na tabela `documents`.
- Resposta: a cada mensagem, `rag.query` busca os 4 trechos mais
  parecidos, que entram no prompt como contexto.
- Remoção: `DELETE /documents/{id}` apaga os trechos do documento no
  ChromaDB (`rag.delete_document`) e o registro no banco.
- A triagem de risco **não** usa os documentos.

Arquivos: `routers/documents.py`, `services/rag.py`,
`services/text_extraction.py`, `frontend/src/pages/KnowledgeBase.jsx`.

## Textos fixos

Não se aplica.

## Configuração

`CHROMA_PERSIST_DIR` ([configuração](../tecnico/configuracao.md)): pasta
onde o ChromaDB guarda os trechos.

## Segurança e LGPD

A tela pede para não enviar documentos com dados de pacientes. Os
trechos ficam no ChromaDB local, sem cifra (é material público do
consultório, não conversa clínica). Só a própria profissional lista,
envia ou remove os documentos dela.

## Limitações e pendências

- O limite de 10 MB é conferido só na tela.
- Documentos digitalizados (PDF de imagem) não têm texto extraível.
- Apagar a profissional pelo banco deixa a coleção dela no ChromaDB.

## Como testar

Automático: `tests/test_documents_api.py` (envio e remoção, com o
ChromaDB substituído), `tests/test_text_extraction.py`.

Manual: envie um `.txt` com uma pergunta frequente, pergunte a mesma
coisa no simulador e confira a etiqueta "Com base em"; depois remova o
documento e pergunte de novo.

## Histórico
- Antes de 27/09/2026: envio e indexação no painel provisório.
- 27/09/2026: tela no visual do protótipo, arrastar e soltar, envio de
  vários arquivos e remoção de documento.
