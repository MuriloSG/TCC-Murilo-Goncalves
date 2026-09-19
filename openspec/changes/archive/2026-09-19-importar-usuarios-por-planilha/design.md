## Context

O projeto tem dois apps: `accounts`, com usuários, perfis e permissões, e `ui`, com os tokens, os componentes e a `ModalView`. Não há nenhuma funcionalidade de importação, upload, processamento de arquivos ou tarefa em segundo plano. O cadastro de usuários passa por `User.objects.register(email, name, role)`, a edição por `User.update_details(executor, name, email)` e a troca de perfil por `User.change_role(role)`, que verifica a continuidade administrativa ao fim de cada chamada pelo gerenciador `administrative_continuity()`.

O TCC prevê a importação das planilhas de horários (RF01 e RF02), com reimportação ao longo do semestre, mas não cita importação de usuários. O autor decidiu criar primeiro um motor reutilizável, com a importação de usuários como primeiro consumidor, porque o model e as regras dela já estão prontos e testados. A importação de horários é o segundo consumidor previsto e foi usada só na especificação, para conferir as fronteiras do motor.

Esta Change depende da Change `enviar-emails-por-outbox`, que cria o outbox, o worker e a operação que registra um envio na transação corrente.

As decisões abaixo foram fechadas numa entrevista com o autor antes da proposal.

Interessados: o autor do TCC, os orientadores, os administradores do campus e quem implementar a importação de horários.

## Goals / Non-Goals

**Goals:**

- Um motor que leia um CSV, confira a estrutura, mostre uma prévia fiel e aplique tudo ou nada, sem conhecer nenhuma regra de domínio.
- Uma importação de usuários que só traduza linhas em chamadas das operações existentes do model.
- Garantir que o administrador confirme exatamente o que viu na prévia.
- Histórico auditável de cada importação que chegou à prévia.

**Non-Goals:**

- Importação de horários, `.xlsx`, outras codificações, colunas opcionais, separador e limites por tipo.
- Processamento assíncrono, progresso, lotes, cancelamento e estado de falha.
- Tela genérica de importações, registro central de tipos e permissão separada para o histórico.
- Correção de células pela tela e limpeza do histórico.
- O outbox em si.

## Decisions

### D1. Motor genérico com um só consumidor, implementado só no que é usado

A convenção §1 proíbe estruturas antecipadas. O motor é uma exceção justificada: o RF01 garante o segundo consumidor. Para limitar o custo, a spec descreve o contrato inteiro, mas o código implementa só o que a importação de usuários exercita. As capacidades previstas ficam registradas nesta seção e são implementadas junto com a primeira importação que as usar, com testes.

Capacidades previstas, sem implementação:
- **Colunas opcionais:** cabeçalho ausente significa que o campo nunca é alterado; célula vazia na atualização mantém o valor atual; célula vazia no cadastro fica a critério do model.
- **Separador, codificação e limites por tipo de importação.**
- **Processamento assíncrono**, com as situações `PROCESSANDO` e `FALHOU`, progresso e cancelamento.
- **Tela genérica de importações** com registro central de tipos e permissão de visualização do histórico.
- **Limpeza do histórico.**

Alternativas consideradas:
- **Importação de usuários sem motor**, extraindo o motor quando chegarem os horários: menos código agora, mas o autor quis fixar as fronteiras enquanto o caso simples está à mão.
- **Implementar o contrato inteiro:** deixaria código sem uso real e sem teste de consumo.

### D2. App `imports`

O motor fica num app novo, `imports`, e nunca importa código de `accounts` nem de outro app de domínio. Ele depende só do Django, de `ui` (a `ModalView`, os componentes e os templates base) e de `settings.AUTH_USER_MODEL` para os campos de autoria. A importação de usuários fica em `accounts/imports.py`, com as views em `accounts/views.py` e as rotas em `accounts/urls.py`.

Alternativa considerada: **motor dentro de `accounts`**. O acoplamento ficaria implícito e a importação de horários teria que depender de `accounts`.

### D3. Sem registro central

Cada view da importação de usuários declara a definição que usa (`definition = UserImport()`), e o histórico filtra `Import.objects.filter(kind='USUARIO')`. O motor não mantém um mapa `tipo → definição`.

Alternativa considerada: **registro central com telas genéricas parametrizadas pelo tipo**. Só faria sentido com uma tela "Importações" que lista todos os tipos, que ficou fora do escopo.

### D4. Contrato da definição

`imports.definitions.ImportDefinition` é a classe base que cada importação estende. Ela declara:

| Elemento | Na importação de usuários |
|---|---|
| `kind` | `'USUARIO'` |
| `columns` | `Column('E-mail')`, `Column('Nome')`, `Column('Perfil')`, todas obrigatórias |
| `identifier` e `normalize_identifier(value)` | `'E-mail'` e `UserManager.normalize_email` |
| `execution()` | Contexto em volta de todas as linhas e de `check_file`: `deferred_administrative_continuity()` (D11) |
| `lock(rows, executor)` | Trava os usuários ativos (`lock_active_users`) e os usuários com os e-mails do arquivo, em ordem de `pk` |
| `execute_row(values, executor)` | Devolve um `RowPlan` |
| `check_file(executor)` | Verifica a continuidade administrativa e devolve os erros do arquivo |
| Rótulos | Ações, campos (`name` → "Nome", `role` → "Perfil"), avisos e códigos de erro |

`RowPlan` é uma dataclass com `action`, `target`, `changes`, `warnings`, `errors` e `created`. `created` é a chave do registro criado pela linha, fica fora da comparação e só é gravado na conclusão. Cada erro é um `RowError(column, code, message)`. O motor oferece `errors_from_validation(error, columns_by_field)`, que traduz uma `ValidationError` do model para erros de coluna usando o mapa `{'email': 'E-mail', 'name': 'Nome', 'role': 'Perfil'}` declarado pela definição. Assim, a mensagem exibida é a mesma da tela.

Nesta versão, `Column` só tem o rótulo. O atributo `required` entra junto com a primeira coluna opcional (D1).

A definição não tem gancho "depois de gravar": efeitos externos vão para o outbox dentro da própria execução da linha (D12).

### D5. Leitura do arquivo

`imports.reader.read_csv(uploaded_file, definition)` devolve as linhas ou lança `FileRejected` com a mensagem para o formulário:

1. confere `uploaded_file.size` com `IMPORT_MAX_FILE_SIZE` antes de ler;
2. decodifica com `utf-8-sig`, em modo estrito. `UnicodeDecodeError` gera a recusa com a instrução de salvar como "CSV UTF-8";
3. lê com `csv.reader(delimiter=';')`;
4. normaliza cada cabeçalho (NFKD sem marcas combinantes, `casefold`, `strip`) e compara com os rótulos normalizados das colunas. Coluna desconhecida, ausente ou repetida gera a recusa. Se o cabeçalho tiver uma única célula e, dividido por vírgula, fosse reconhecido, a mensagem pede o separador `;`;
5. numera cada registro pela linha física em que começa. O `csv.reader.line_num` informa a linha em que o registro termina, então o número é a linha anterior mais um;
6. descarta os registros com todas as células vazias ou só com espaços;
7. confere a quantidade de linhas restantes com `IMPORT_MAX_ROWS` e recusa um arquivo sem linhas.

Os limites ficam em `settings.py`, lidos de variáveis de ambiente, como os demais. **Valores iniciais:** `IMPORT_MAX_FILE_SIZE = 1 MB` e `IMPORT_MAX_ROWS = 1.000`. Eles foram medidos no ambiente de desenvolvimento, com a importação de usuários e só cadastros:

| Linhas | Tamanho | Prévia | Confirmação |
|---|---|---|---|
| 100 | 4 KB | 0,15 s | 0,15 s |
| 500 | 25 KB | 0,72 s | 0,76 s |
| 1.000 | 52 KB | 1,55 s | 1,66 s |
| 2.000 | 107 KB | 3,58 s | 3,88 s |

O tempo cresce de forma linear, cerca de 1,6 ms por linha em cada etapa. Com 1.000 linhas, as duas etapas ficam abaixo de 2 segundos, e os valores iniciais foram mantidos. O limite de 1 MB fica bem acima do tamanho de 1.000 linhas e serve só para recusar, antes da leitura, arquivos claramente fora do esperado. Os dois valores podem ser ajustados por variável de ambiente (`DJANGO_IMPORT_MAX_ROWS` e `DJANGO_IMPORT_MAX_FILE_SIZE`) quando houver hospedagem definida.

Alternativas consideradas:
- **Detectar a codificação e o separador:** Windows-1252 decodifica qualquer sequência de bytes, então a detecção esconderia erros. Recusar com instrução é mais previsível.
- **Aceitar `.xlsx`:** exigiria `openpyxl`. Fica para quando for necessário, com a leitura já isolada neste módulo.

### D6. Model

```text
Import
  kind              CharField(20)              'USUARIO'
  status            CharField(choices)         VALIDADA | COM_ERROS | CONCLUIDA | DESCARTADA
  file_name         CharField(255)
  created_by        FK AUTH_USER_MODEL PROTECT
  created_at        DateTimeField(auto_now_add)
  resolved_by       FK AUTH_USER_MODEL PROTECT, nulo
  resolved_at       DateTimeField, nulo
  revalidation_count PositiveIntegerField(default=0)
  file_errors       JSONField(default=list)    [{code, message}]
  índice (kind, -created_at)

ImportRow
  import            FK Import CASCADE, related_name='rows'
  line_number       PositiveIntegerField
  values            JSONField                  {rótulo da coluna: texto bruto}
  action            CharField(choices), nulo   create | update | unchanged
  target            CharField(64), nulo        chave do registro existente
  changes           JSONField(default=dict)    {campo: [anterior, novo]}
  warnings          JSONField(default=list)    [código]
  errors            JSONField(default=list)    [{column, code, message}]
  created_object    CharField(64), nulo        chave do registro criado, só na conclusão
  único (import, line_number)
```

- `resolved_by` e `resolved_at` servem tanto para a confirmação quanto para o descarte. A situação diz qual das duas aconteceu.
- `target` e `created_object` são texto porque o motor não sabe o tipo da chave de cada model.
- `PROTECT` na autoria segue a regra de que usuários não são excluídos (desativação lógica).
- Os totais por ação são contados com `rows.values('action').annotate(Count(...))`.

Alternativa considerada: **guardar o plano inteiro num único JSON na importação**. Seria mais simples de comparar, mas pior para listar e contar as linhas na tela.

### D7. Prévia por executar e desfazer

`Import.objects.preview(definition, rows, file_name, executor)`:

```text
atomic (externa)
  plan = execute(definition, rows, executor)       ← domínio num savepoint que sofre rollback
  cria Import(status conforme plan) e ImportRow
commit
```

`execute` roda dentro de `transaction.atomic()` e termina com `transaction.set_rollback(True)`, de modo que só o savepoint do domínio é desfeito. Dentro dele:
1. `definition.lock(rows, executor)`;
2. para cada linha, um `transaction.atomic()` próprio (savepoint). Uma `ValidationError` ou um `IntegrityError` numa linha desfaz só aquela linha e vira erro no plano. Sem o savepoint, o PostgreSQL invalidaria a transação inteira depois do primeiro erro de banco;
3. `definition.check_file(executor)`.

Uma exceção que não seja recusa de regra atravessa tudo e desfaz também a importação (requisito de erros inesperados).

Alternativa considerada: **validação separada da aplicação**. A regra de negócio ficaria em dois lugares, e a continuidade teria que ser simulada, o que contraria o P2.

### D8. Plano e comparação

O plano é normalizado antes de gravar e antes de comparar: listas de avisos em ordem, erros ordenados por (coluna, código), e mudanças como dicionário. Na comparação, o motor monta de cada linha a tupla `(line_number, action, target, changes, warnings, [(column, code) ...])` e do arquivo a lista de códigos, e compara as duas estruturas com `==`. As mensagens, os valores lidos e `created_object` ficam de fora.

Valores canônicos na importação de usuários: e-mail normalizado, nome depois do `strip` e perfil pelo `code`. Renomear um perfil não altera o plano.

Alternativa considerada: **hash do plano**. Só serviria para comparar, e o plano completo precisa ser gravado de qualquer forma para a tela.

### D9. Confirmação

`Import.confirm(executor, definition)`:

```text
atomic (externa)
  trava a importação (select_for_update); fora de VALIDADA → ValidationError
  plan = execute(definition, valores gravados, executor, keep=True)   ← savepoint mantido
  se plan == plano gravado e sem erros:
      grava created_object das linhas create, status CONCLUIDA, resolved_by/at
  senão:
      desfaz o savepoint do domínio
      substitui o plano das linhas, revalidation_count += 1,
      status VALIDADA ou COM_ERROS
commit
```

Na divergência, a importação é atualizada na mesma transação externa, já sem as alterações de domínio. A view mostra a mensagem de divergência e reabre a prévia.

A trava da importação serializa confirmações simultâneas: a segunda espera, encontra `CONCLUIDA` e é recusada. Duas importações diferentes que atingem os mesmos usuários são serializadas pelas travas de `lock`, e a segunda diverge.

Alternativa considerada: **aplicar o que a reexecução produzir quando não houver erros**. O administrador aplicaria algo diferente do que viu.

### D10. Situações como métodos do model

As transições ficam em `Import.confirm` e `Import.discard`, que travam o registro, conferem a situação e recusam com `ValidationError`, como as demais operações do projeto. Não há expiração nem situação de falha.

Alternativa considerada: **`django-fsm`**. É uma dependência para quatro situações e duas transições.

### D11. Continuidade administrativa adiada

Hoje, `administrative_continuity()` trava os usuários ativos, executa a operação e verifica a continuidade no fim de cada chamada. Na importação, isso recusaria um arquivo que rebaixa um administrador na linha 3 e promove outro na linha 7.

Mudança em `accounts/models.py`: um gerenciador `deferred_administrative_continuity()` marca, numa `contextvars.ContextVar`, que a verificação está adiada. Enquanto a marca estiver ativa, `administrative_continuity()` continua travando e executando, mas não verifica. A verificação passa a ser feita por quem abriu o gerenciador adiado, no `check_file` da importação, que chama `ensure_administrative_continuity()` e converte a recusa em erro do arquivo.

- Fora da importação, nada muda: as telas e os comandos continuam verificando a cada operação, e os testes existentes cobrem isso.
- A marca só é ativada dentro da transação da importação e é sempre removida no `finally`.

Alternativas consideradas:
- **Parâmetro `check_continuity=False` nas operações:** espalharia uma opção perigosa pela interface pública do model.
- **Ordenar as linhas para promover antes de rebaixar:** não resolve todos os casos e esconde a regra.

### D12. Outbox dentro da execução da linha

Na ação `create`, a importação de usuários só chama `register`. Pela D7 da Change `enviar-emails-por-outbox`, o próprio `register` registra no outbox o envio `LINK_SENHA`, na transação corrente, com `OutboxEntry.objects.enqueue`. Assim, o registro fica no mesmo savepoint do usuário. Na prévia, o rollback desfaz o registro junto com o usuário. Na confirmação, ele é efetivado junto com o usuário. Por isso o motor não precisa de gancho "depois de gravar". O link é gerado pelo worker no momento do envio e nunca é gravado no outbox.

### D13. Permissão por ação dentro do plano

`USUARIO.IMPORTAR` protege as rotas pelo `PermissionMiddleware`, como qualquer view. Dentro de `execute_row`, a importação de usuários consulta `executor.has_perm` antes de cada operação:
- `create` → `USUARIO.CRIAR`, erro sem coluna;
- mudança de nome → `USUARIO.EDITAR`, erro na coluna `Nome`;
- mudança de perfil → `USUARIO.ALTERAR_PERFIL`, erro na coluna `Perfil`.

`unchanged` não consulta nada. Como a confirmação recalcula o plano com o executor atual, um confirmador com menos permissões gera divergência com erros. `has_perm` continua sendo o único ponto de decisão.

Alternativas consideradas:
- **`USUARIO.IMPORTAR` sozinha:** abre um desvio no RBAC, porque troca perfis sem `USUARIO.ALTERAR_PERFIL`.
- **Exigir as outras permissões ao conceder `IMPORTAR` a um perfil:** cria dependência entre permissões na gestão de perfis.

### D14. Ações de usuários

`execute_row` normaliza os valores, resolve o perfil por `Role.objects.filter(code=...)` e procura o usuário por `email__iexact`:
- sem usuário: `register(email, name, role)`, que já registra o envio do link no outbox (D12);
- com usuário: compara nome e perfil. Nome diferente chama `update_details(executor, name, user.email)`, e perfil diferente chama `change_role(role)`. Nada diferente gera `unchanged`;
- usuário inativo: acrescenta o aviso `inactive_user`, sem mudar a situação.

Como o e-mail enviado a `update_details` é o atual, a proteção do e-mail de superadmin nunca é acionada, e o superadmin é tratado como os demais.

### D15. Permissão e migration

- `USER_IMPORT = 'USUARIO.IMPORTAR'` entra em `accounts/permissions.py`, em `ALL_PERMISSIONS` e em `RESOURCE_LABELS` (o recurso `USUARIO` já tem rótulo). Não entra em `ADMINISTRATIVE_CAPABILITY` nem em `SUPERADMIN_RESERVED_PERMISSIONS`.
- A migration de dados `0003` cria a permissão e a concede ao `ADMINISTRADOR`, com códigos literais e models históricos, seguindo a D9 da Change `gerenciar-usuarios-e-controle-de-acesso`: idempotente, só perfis do sistema, uma única vez.

### D16. Rotas e views

| Rota | View (em `accounts`) | Base (em `imports`) |
|---|---|---|
| `usuarios/importacoes/` | `UserImportListView` | `ImportListView` |
| `usuarios/importacoes/nova/` | `UserImportUploadView` | `ImportUploadView` (modal) |
| `usuarios/importacoes/modelo/` | `UserImportTemplateView` | `ImportTemplateView` |
| `usuarios/importacoes/<pk>/` | `UserImportDetailView` | `ImportDetailView` (prévia e detalhe) |
| `usuarios/importacoes/<pk>/confirmar/` | `UserImportConfirmView` | `ImportConfirmView` (POST) |
| `usuarios/importacoes/<pk>/descartar/` | `UserImportDiscardView` | `ImportDiscardView` (modal, GET e POST) |

- Todas declaram `permission_required = permissions.USER_IMPORT` e têm `login_required` na URL.
- O detalhe carrega a importação com `get_object_or_404(Import, pk=pk, kind=definition.kind)` no `setup()`.
- **Confirmação:** a página de prévia é o GET que mostra o que será confirmado, e o botão "Confirmar importação" envia o POST. Não há um segundo modal de confirmação.
- **Descarte:** segue o padrão de confirmação em modal ("Descartar importação?").
- As views base do motor usam a `ModalView` de `ui` e não reaproveitam `OperationFormView` e `ConfirmedActionView`, que estão em `accounts` e criariam dependência do motor com um app de domínio.
- Um botão "Importar usuários" na lista de usuários abre o envio, e um link leva ao histórico. Os dois aparecem só com `perms.USUARIO.IMPORTAR`.

Alternativa considerada: **mover `ConfirmedActionView` para `ui`**. Seria um refactor fora do escopo desta Change.

### D17. Telas e textos

O autor não tem imagem de referência para estas telas e dispensou a exigência da seção 9.8 das convenções nesta Change. As telas de envio, prévia, histórico e detalhe são derivadas do que a interface já usa: a lista de usuários (cartão com cabeçalho, tabela densa e rodapé de contagem), a página de detalhe de perfil, os modais de formulário e de confirmação, os selos de situação e os tokens e componentes do app `ui`. Nenhum componente visual novo é criado sem necessidade, e os que forem criados entram no `app.css`. Textos definidos desde já:

- Botões: "Importar usuários", "Baixar modelo", "Enviar arquivo", "Confirmar importação", "Descartar importação".
- Sucesso da confirmação: "Importação concluída. 6 usuários cadastrados e 4 atualizados. O link para definir a senha será enviado aos usuários cadastrados."
- Divergência: "Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo."
- Estado vazio do histórico: "Nenhuma importação de usuários."

Telas implementadas, conferidas no navegador em 360 e 1280 px:
- **Lista de usuários:** ganha os botões secundários "Importações" (ícone `history`) e "Importar usuários" (ícone `upload`), ao lado de "Cadastrar usuário", visíveis só com `USUARIO.IMPORTAR`.
- **Envio:** modal de formulário com o campo "Arquivo CSV", a ajuda com o formato e as colunas e o link "Baixar modelo do arquivo". O botão do seletor de arquivo recebe o visual do botão secundário, numa regra de `.field input[type="file"]` no `app.css`. As recusas do arquivo aparecem como erro do campo.
- **Prévia e detalhe:** página completa com título "Importação de <arquivo>", as ações "Descartar importação" e "Confirmar importação" só na importação validada, e "Enviar arquivo corrigido" na importação com erros. Um alerta fixo aparece só nas situações que pedem ação (validada e com erros), e a confirmação ou o descarte vão para o resumo, que usa o `detail-grid` da tela de perfil. As linhas ficam numa `data-table` com as colunas do arquivo e o resultado, que mostra a ação, as mudanças no formato "Perfil: DOCENTE → ADMINISTRADOR", os avisos e os erros com a coluna. O link "Mostrar só as linhas com erro" filtra pela URL (`?linhas=erros`). O resultado usa o componente `.line-result`, criado no `app.css` com os tokens existentes.
- **Histórico:** `data-table` com arquivo e autor, data, selo de situação, resultado e o botão só com ícone "Ver importação". Selos: "Validada" (info), "Com erros" (erro), "Concluída" (sucesso) e "Descartada" (info com `circle-minus`, como "Inativo").
- **Descarte:** modal de confirmação padrão, com a pergunta, a consequência e o botão de perigo.
- Ícones novos do Lucide: `upload`, `download` e `history`.
- Aviso de inativo: "Usuário inativo. Os dados serão atualizados e ele continuará inativo."

### D18. Modelo para baixar

`ImportTemplateView` responde com `text/csv`, `Content-Disposition` com o nome `modelo-importacao-usuarios.csv`, BOM UTF-8 e o cabeçalho `E-mail;Nome;Perfil`.

## Risks / Trade-offs

- **[Travamento durante a prévia]** A prévia trava os usuários ativos, e operações administrativas simultâneas esperam. → O limite de linhas mantém a prévia curta. A medição de D5 fixa o limite.
- **[Divergências repetidas]** Com muitas alterações concorrentes, a confirmação pode divergir várias vezes. → É improvável no volume do campus. O contador de prévias refeitas torna o fenômeno visível.
- **[Continuidade adiada por variável de contexto]** Um erro de programação que deixasse a marca ativa desligaria a verificação. → A marca só é ativada por um gerenciador de contexto com `finally`, e há teste de que as telas continuam recusando a perda da continuidade depois de uma importação.
- **[Planos não determinísticos]** Uma ordem instável em listas faria toda confirmação divergir. → Normalização de D8 e teste que gera a prévia duas vezes e compara.
- **[Chaves consumidas pela prévia]** O rollback consome valores das sequências do PostgreSQL. → Não tem efeito funcional, e nenhuma chave da prévia é gravada.
- **[Histórico com dados pessoais]** Valores lidos e mudanças guardam e-mails, nomes e perfis antigos. → São os mesmos dados da tabela de usuários, visíveis só com `USUARIO.IMPORTAR`. A limpeza fica prevista.
- **[CSV salvo com a opção errada no Excel]** É a recusa mais provável. → Mensagem com a instrução exata e modelo para baixar já em UTF-8 com `;`.
- **[Escalada de privilégio herdada]** Quem tem `USUARIO.CRIAR` pode cadastrar alguém como `ADMINISTRADOR`, pela tela e pela importação. → A decisão continua pendente na spec `gestao-usuarios` e, quando tomada no model, vale para as duas.

## Migration Plan

1. Implantar depois da Change `enviar-emails-por-outbox`.
2. `make migrate` aplica `imports.0001_initial` e `accounts.0003`, que cria `USUARIO.IMPORTAR` e a concede ao `ADMINISTRADOR`.
3. Rollback: reverter `accounts.0003` remove a permissão e as concessões, e reverter `imports.0001` remove as tabelas e o histórico. Os usuários importados continuam, porque são usuários comuns.

## Open Questions

- Valores definitivos de `IMPORT_MAX_FILE_SIZE` e `IMPORT_MAX_ROWS`, a registrar em D5 depois da medição.
- Imagens de referência das telas (D17).
