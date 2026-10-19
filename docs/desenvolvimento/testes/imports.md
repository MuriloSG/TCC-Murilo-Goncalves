# Testes do app `imports`

Motor de importação: leitura, prévia, confirmação, situações e worker. Comportamento descrito em [motor de importação](../../arquitetura/motor-de-importacao.md). Os testes não dependem de app de domínio. Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Auxiliares

- `definitions.py`: `GroupImport`, importação de teste sobre `auth.Group`. Os valores `ERRO`, `BANCO`, `FALHA`, `PROIBIDO` e `DECIDIR` provocam cada tipo de recusa do motor.
- `worker.py`: pede uma operação e roda o worker em seguida, com a definição registrada no teste, e faz a consulta de andamento que o detalhe faria.

## Módulos

### `test_reader.py`

Leitura do CSV, sem banco.

| Classe | O que garante |
|---|---|
| `FileTests` | Linhas lidas pelo rótulo da coluna; BOM fora do cabeçalho; recusa arquivo fora do UTF-8, acima dos limites de tamanho e de linhas, vazio, só com cabeçalho e separado por vírgula |
| `HeaderTests` | Ordem, caixa, acentos e espaços do cabeçalho não importam; coluna desconhecida, ausente ou repetida recusada |
| `RowTests` | Linhas vazias ignoradas mantendo a numeração; células entre aspas com separador e quebra de linha; valores crus; obrigatória só com espaços; células faltando ficam vazias; coluna opcional aceita vazio, mas é exigida no cabeçalho; células extras; identificador repetido com grafia diferente |
| `ValidationTranslationTests` | Erros de campo vão para a coluna; erro geral fica sem coluna |

### `test_sources.py`

Capacidades do motor usadas pelo ensalamento.

| Classe | O que garante |
|---|---|
| `WorkbookSourceTests` | Uma linha por célula das abas declaradas; aba extra ignorada; aba declarada ausente, arquivo que não é planilha e planilha sem dados recusados; valores crus; fórmula sem valor guardado é célula vazia |
| `PackageTests` | O pacote XLSX é conferido antes do openpyxl: ZIP que não é planilha, truncado, que expande demais, com entradas demais ou com célula distante recusados; planilha válida pode ser lida de novo |
| `LimitTests` | Limites de linhas e tamanho da definição substituem os configurados; sem eles, vale a configuração |
| `UploadFieldTests` | Campo próprio da definição aparece ao lado do arquivo, é gravado em toda linha e, se obrigatório, vira erro do formulário; a importação CSV mantém seus textos |
| `AuditMetadataTests` | Prévia, confirmação e descarte registram a auditoria com os metadados da definição; só a importação é registrada |

### `test_models.py`

| Classe | O que garante |
|---|---|
| `PreviewTests` | A prévia guarda o plano e desfaz o domínio; registro existente fica inalterado; todos os erros de uma vez, inclusive de banco; erros de leitura pulam a execução; erro de arquivo; erro inesperado mantém a prévia pendente enquanto há tentativas e depois a deixa com falha; o plano é determinístico |
| `ConfirmTests` | Plano idêntico aplica e grava quem confirmou; dados alterados dão plano novo sem aplicar, com ou sem erros; erro inesperado mantém validada; situações finais recusam confirmar e descartar; descarte |
| `PendingTests` | Pendência de decisão sem erro desfaz a linha e impede confirmar e excluir, mas permite descartar; erro prevalece; a pendência entra na comparação; atualizar o plano não conta divergência e pode voltar a pendente; checagem própria recusa sem reexecutar |
| `RemoveTests` | Descartadas e com erros são excluídas com as linhas, com auditoria; pendentes e concluídas não |
| `ConcurrentConfirmTests` | Confirmações simultâneas aplicam uma vez |
| `IsolationTests` | O motor não importa apps de domínio |

### `test_worker.py`

| Classe | O que garante |
|---|---|
| `BusinessStatusTests` | A situação só tem estados de negócio e o pedido não a altera; restrição recusa operação incoerente; confirmação pendente conta como importação aberta no painel |
| `ReservationTests` | Reservar conta a tentativa e adia a próxima; queda entre reserva e execução é retomada no prazo; quedas repetidas esgotam sem executar; o último atraso se repete; tipo sem definição esgota |
| `FailureTests` | Erro inesperado desfaz e mantém a operação pendente; esgotado, mantém situação e plano; recusas de regra e da checagem própria não são repetidas; recusa de linha é resultado de negócio; erros de leitura chegam à prévia |
| `LoggingTests` | Log só com número, tipo, operação e classe do erro, nunca a mensagem; loggers do projeto no stdout; falha esgotada é `ERROR`; início e fim do comando |
| `RequesterTests` | Quem pediu é executor e autor da auditoria; solicitante inativo recusa a execução ou faz a prévia falhar |
| `LockTimeoutTests` | A espera por travas tem o limite configurado |
| `CommandTests` | `--once` processa o que venceu e descarta conexões velhas |
| `ConcurrencyTests` | Um segundo worker pula a importação em execução; ações sobre importação travada são recusadas sem esperar |
