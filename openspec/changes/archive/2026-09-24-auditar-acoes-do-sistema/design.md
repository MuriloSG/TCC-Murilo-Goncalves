## Context

O projeto tem quatro apps. `accounts` concentra as regras de negócio de usuários e perfis em operações do model (`User.objects.register`, `update_details`, `change_role`, `deactivate`, `reactivate`, `Role.objects.create_role`, `set_permissions`, `delete_role`), e as views apenas as chamam. `imports` executa a prévia e a confirmação das planilhas chamando essas mesmas operações. `outbox` envia os e-mails num worker, fora de qualquer requisição. `ui` traz os componentes, a paginação e a classe base das ações em modal.

O acesso já é decidido em um ponto único: a rota exige autenticação com `login_required`, a view declara `permission_required` como dado e o `accounts.middleware.PermissionMiddleware` aplica a permissão. O `accounts.models` já usa `contextvars` para adiar a verificação de continuidade administrativa durante a importação, então o padrão de contexto de execução já existe no projeto.

Nada disso deixa rastro: nenhuma tabela guarda quem fez o quê. A auditoria precisa alcançar três lugares diferentes, com informações diferentes disponíveis em cada um: a requisição (quem, IP, cliente, tela acessada), a operação do model (o que mudou) e os processos sem requisição (worker e comandos).

## Goals / Non-Goals

**Goals:**

- Uma tabela e um ponto único de gravação para toda ação auditável, hoje e nos módulos futuros.
- A operação do model continua sendo o lugar onde a regra de negócio acontece, e é lá que o fato é registrado, sem que o model precise conhecer a requisição.
- Ação nova exige apenas uma constante no catálogo, nunca uma estrutura de log própria.
- Registro fiel: o que está no log aconteceu, e o que aconteceu está no log.

**Non-Goals:**

- Reconstituir o estado de um registro em qualquer instante do passado. O log guarda o que mudou em cada ação, e não versões completas.
- Retenção, expurgo e exportação dos registros.
- Assinatura ou encadeamento criptográfico dos registros.

## Decisions

### D1. Tabela única no app `audit`

O model `AuditLog`, no app novo `audit`, tem os campos `user`, `action`, `resource`, `resource_id`, `old_values`, `new_values`, `metadata`, `origin`, `ip_address`, `user_agent` e `created_at`. `action`, `resource` e `origin` são códigos gravados como dado, em português e maiúsculas, como `USUARIO.CRIAR` e `ADMINISTRADOR` já são. Os rótulos ficam no catálogo e só aparecem na interface.

`user` é uma chave estrangeira com `PROTECT` e `null=True`: nulo quando não há usuário identificado (ação do sistema ou tentativa de login recusada), e protegida porque o sistema não exclui usuários, apenas desativa. `resource_id` é texto, e não inteiro, para aceitar identificadores que não sejam números em módulos futuros. `old_values`, `new_values` e `metadata` são `JSONField` com `dict` vazio como padrão.

A ordenação padrão é `['-created_at', '-pk']`, e os índices são `(-created_at)`, `(user, -created_at)`, `(action, -created_at)` e `(resource, resource_id)`, que atendem à lista e aos filtros da consulta.

Alternativa considerada: **uma tabela por módulo**. Recusada pelo pedido de tabela centralizada e porque cada módulo novo exigiria estrutura própria.

Alternativa considerada: **`GenericForeignKey` para o recurso**. Recusada porque prende o log ao `ContentType` do registro, que pode deixar de existir, e porque o log precisa registrar recursos que não são models, como a autenticação e o acesso às telas.

### D2. Ponto único de gravação: `AuditLog.objects.record`

`AuditLog.objects.record(action, resource, resource_id=None, old_values=None, new_values=None, metadata=None)` é o único lugar que grava. Ele completa o registro com o ator do contexto (D3), recusa uma ação ou um recurso fora do catálogo (D4) e retira os campos sensíveis (D8). Nenhuma view, formulário ou template grava direto.

### D3. Ator da ação num `ContextVar`

`audit/context.py` define `Actor(user, ip_address, user_agent, origin)` e um `ContextVar` com o ator atual, além dos gerenciadores de contexto `acting_as(actor)` e `acting_from_import()`. O padrão, quando ninguém define nada, é o ator do sistema, sem usuário.

- O `AuditMiddleware` define o ator da requisição em volta da chamada da view, com o usuário autenticado (ou nenhum), o IP, o cliente e a origem `INTERFACE`.
- O worker do outbox e os comandos de gerenciamento rodam com o ator padrão, de origem `SISTEMA`.
- A execução das linhas de uma importação troca a origem para `IMPORTACAO`, mantendo o usuário que confirmou.

Assim `User.objects.register` registra o cadastro sem receber `request`, e a mesma operação chamada pela tela, pela importação ou por um comando produz registros com origens diferentes. É o mesmo mecanismo que `deferred_administrative_continuity` já usa no projeto.

Alternativa considerada: **passar o executor e o IP como parâmetro em todas as operações do model**. Recusada porque mudaria a assinatura de todas as operações e de toda a importação para carregar dados de apresentação, e ainda assim não alcançaria o worker.

Alternativa considerada: **`threading.local`**. Recusada porque `ContextVar` é o que o projeto já usa e não vaza entre tarefas assíncronas.

### D4. Catálogo de ações e recursos em `audit/catalog.py`

As ações são `LOGIN`, `LOGIN_RECUSADO`, `LOGOUT`, `SENHA_SOLICITADA`, `SENHA_REDEFINIDA`, `ACESSO`, `CRIAR`, `ALTERAR`, `EXCLUIR`, `ATIVAR`, `DESATIVAR`, `IMPORTAR`, `DESCARTAR`, `EXPORTAR`, `ENVIAR` e `FALHAR`. Os recursos são `AUTENTICACAO`, `USUARIO`, `PERFIL`, `IMPORTACAO_USUARIO`, `EMAIL` e `AUDITORIA`. As origens são `INTERFACE`, `SISTEMA` e `IMPORTACAO`.

Cada um é uma constante com um rótulo em português no mesmo módulo, e `record` recusa um código que não esteja no catálogo, o que impede erro de digitação virar uma ação nova sem querer. Incluir uma ação é acrescentar uma constante e o rótulo dela, sem migration de esquema e sem estrutura de log própria: `action` é um `CharField` comum, e não `TextChoices`.

Uma alteração de permissões de perfil é registrada como `ALTERAR` no recurso `PERFIL`, com a lista de permissões em `old_values` e `new_values`. Não há ação específica para isso, porque o par de valores já mostra o que mudou e o filtro por recurso já separa essas alterações.

### D5. Registro do acesso pelo middleware, a partir do que a view declara

A view declara `audit_resource = catalog.USER`, como já declara `permission_required`. O `AuditMiddleware` lê o atributo no `process_view`, guarda o recurso na requisição e registra `ACESSO` depois que a resposta fica pronta, quando todas estas condições valem:

- o método é GET;
- a resposta tem status 200;
- a requisição não veio do htmx.

O `PermissionMiddleware` vem antes na lista, então um acesso recusado com 403 nunca chega a ser registrado como acesso concedido. A exclusão das requisições do htmx cumpre o pedido de não registrar requisição técnica: o formulário de busca da lista de usuários dispara um GET a cada 300 ms de digitação, a troca de página troca o mesmo fragmento e a abertura de um modal é parte da renderização da tela em que o usuário já está. Sem JavaScript, essas mesmas URLs são páginas completas e são registradas, o que é correto: aí elas são navegação.

O `metadata` do acesso guarda o nome da rota e o caminho, o que distingue a lista de usuários do formulário de cadastro dentro do mesmo recurso. Arquivos estáticos não passam por view e nunca declaram recurso. A página inicial não declara recurso, por não ser uma funcionalidade.

Alternativa considerada: **registrar toda requisição**. Recusada pelo próprio pedido, e porque encheria a tabela de fragmentos de busca.

### D6. Autenticação registrada onde a decisão acontece

- **Login realizado e logout:** sinais `user_logged_in` e `user_logged_out`, ligados no `ready()` do app `audit`. O allauth dispara os dois.
- **Login recusado:** no `AccountAdapter.authenticate` do app `accounts`, que já é o ponto único que decide a recusa, inclusive a do usuário inativo com a senha correta, caso que não chega ao sinal `user_login_failed` do Django. O registro guarda o e-mail informado em `metadata`, o IP e o cliente, sem usuário responsável e sem nunca tocar na senha.
- **Solicitação de recuperação de senha:** no `save` do `PasswordResetForm` do projeto, com o e-mail informado. O registro é o mesmo para e-mail cadastrado e não cadastrado, para não abrir uma via de enumeração de contas pela auditoria.
- **Senha redefinida:** sinal `password_reset` do allauth, que cobre tanto a criação inicial da senha quanto a recuperação, já que os dois usam o mesmo fluxo.

### D7. Alterações de dados registradas nas operações do model

Cada operação que já concentra a regra de negócio chama `record` dentro da própria transação, depois de gravar:

| Operação | Ação | Recurso | Valores |
|---|---|---|---|
| `User.objects.register` | `CRIAR` | `USUARIO` | `new_values` com e-mail, nome e código do perfil |
| `User.update_details` | `ALTERAR` | `USUARIO` | só os campos que mudaram |
| `User.change_role` | `ALTERAR` | `USUARIO` | código do perfil anterior e do novo |
| `User.deactivate` / `reactivate` | `DESATIVAR` / `ATIVAR` | `USUARIO` | sem valores |
| `User.objects.create_superadmin` | `CRIAR` | `USUARIO` | e-mail, nome, perfil e a marca de superadmin |
| `User.set_superadmin` | `ALTERAR` | `USUARIO` | marca de superadmin antes e depois |
| `Role.objects.create_role` | `CRIAR` | `PERFIL` | código, nome, descrição e permissões concedidas |
| `Role.update_details` | `ALTERAR` | `PERFIL` | só os campos que mudaram |
| `Role.set_permissions` | `ALTERAR` | `PERFIL` | listas de permissões antes e depois |
| `Role.delete_role` | `EXCLUIR` | `PERFIL` | `old_values` com os dados do perfil excluído |
| `Import.objects.preview` | `CRIAR` | `IMPORTACAO_USUARIO` | arquivo, totais e situação |
| `Import.confirm` concluída | `IMPORTAR` | `IMPORTACAO_USUARIO` | totais aplicados |
| `Import.discard` | `DESCARTAR` | `IMPORTACAO_USUARIO` | sem valores |
| `ImportTemplateView` | `EXPORTAR` | recurso da tela | nome do arquivo |

Os dois comandos de gerenciamento do superadmin passam por essas mesmas operações e, por rodarem fora de uma requisição, deixam registros com a origem `SISTEMA`.

Uma operação sem efeito não registra nada: `update_details` chamado com os mesmos dados e `set_permissions` sem diferença não geram registro, porque não houve alteração.

Como as linhas da importação chamam as mesmas operações, cada usuário cadastrado ou alterado por planilha gera o seu próprio registro, com origem `IMPORTACAO`, além do registro da importação. Na prévia, essas chamadas acontecem dentro do savepoint que sofre rollback, então os registros delas são desfeitos junto com as alterações, e a prévia deixa apenas o registro da própria prévia.

Alternativa considerada: **sinais `post_save` e `post_delete` em todos os models**. Recusada porque o sinal não distingue desativar de editar, não conhece o motivo da operação, registraria gravações internas como a atualização do `last_login` e as linhas da importação, e obrigaria a comparar o estado anterior com uma consulta extra.

### D8. Dados sensíveis nunca chegam ao registro

Os valores registrados são montados pelos chamadores, campo a campo, e nenhum deles inclui senha ou token. Como isso depende de quem escreve a chamada, `record` ainda retira de `old_values`, `new_values` e `metadata` qualquer chave cujo nome contenha `senha`, `password`, `token`, `secret`, `chave` ou `hash`. É uma rede de proteção verificada por teste, e não a regra principal.

### D9. Registro na mesma transação da operação

`record` grava na transação de quem chama. Uma operação desfeita leva o registro junto, e uma falha ao registrar desfaz a operação. É a mesma decisão já tomada no outbox, em que o envio é enfileirado na transação do cadastro: o log e o fato nascem e morrem juntos, e não existe operação aplicada sem registro.

O preço é que um defeito na auditoria derruba a operação de negócio. A alternativa, registrar fora da transação e ignorar falhas, foi recusada porque produziria exatamente o que a auditoria existe para evitar: alteração sem rastro. Os registros de autenticação e de acesso não têm transação de negócio em volta e são gravados isoladamente.

### D10. Integridade dos registros

`AuditLog.save` recusa qualquer gravação com chave primária já existente, e `delete`, tanto do objeto quanto do queryset, é recusado. Não existe view, formulário, comando ou ação de interface que altere ou exclua registros. A consulta é somente leitura. A recusa acontece na aplicação: uma gravação direta no banco por quem tem acesso ao PostgreSQL continua possível, e isso é limite conhecido desta Change.

### D11. Ações automáticas do worker

O worker do outbox registra, com ator do sistema e recurso `EMAIL`, a ação `ENVIAR` quando um e-mail é enviado e `FALHAR` quando o envio se encerra em falha definitiva. As tentativas intermediárias continuam só no log da aplicação, para não gerar um registro de auditoria a cada nova tentativa. O `metadata` guarda o tipo e a referência do envio, nunca o conteúdo nem o link.

### D12. Permissão e tela de consulta

A permissão nova é `AUDITORIA.VISUALIZAR`, concedida ao perfil `ADMINISTRADOR` por migration de dados, no mesmo formato da migration que acrescentou `USUARIO.IMPORTAR`, sem alterar as demais permissões concedidas pelos perfis existentes. Ela não é reservada ao superadmin: o autor optou por deixá-la concedível, de modo que o superadmin possa dá-la a perfis personalizados.

A tela `auditoria/` adapta o que já existe, sem referência visual nova (conforme a decisão do autor):

```text
Auditoria                                                  [ contagem ]
[ busca do registro ] [ ação ] [ recurso ] [ origem ] [ de ] [ até ]
---------------------------------------------------------------------
Data e hora        Usuário        Ação        Recurso      Origem   [ ]
24/09/2026 11:42   Ana Souza      Alteração   Usuários     Interface (i)
24/09/2026 11:40   Sistema        Envio       E-mails      Sistema   (i)
---------------------------------------------------------------------
Exibindo 1 a 5 de 57 registros         [Anterior]  Página 1 de 12  [Próxima]
```

- Cartão, cabeçalho com filtros, `data-table` e rodapé de paginação são os mesmos da lista de usuários e do histórico de importações, com os mesmos componentes do app `ui`.
- Os filtros são parâmetros da URL (`usuario`, `acao`, `recurso`, `origem`, `registro`, `de` e `ate`), combináveis entre si e com `pagina`, como na lista de usuários.
- A ordem é do mais recente para o mais antigo, que é a ordem em que o log é lido.
- Cada linha tem a ação "Ver detalhes", que abre um modal com todos os campos do registro, os valores anteriores e posteriores campo a campo e as informações adicionais. O modal é somente leitura, com o controle "Fechar".
- Abaixo de 640 px a tabela vira blocos empilhados, como as demais.
- A tela declara `audit_resource`, então consultar a auditoria também é auditado.

**Detalhe do registro, a partir da referência do autor (seção 9.8 das convenções).** O autor enviou uma referência do modal de detalhe. O que foi adaptado:

- as seções nomeadas ("Usuário", "Ação", "Valores alterados", "Informações adicionais" e "Informações de rede"), que substituem a lista corrida de campos;
- os rótulos em maiúsculas, pequenos e em cinza, com o mesmo tratamento que o cabeçalho das tabelas já usa;
- os campos em duas colunas a partir de 640 px, e uma coluna abaixo disso;
- o painel com fundo da página e borda fina em volta dos blocos técnicos;
- a ação e o módulo em pastilha (`.chip`), sem tom de cor;
- o valor anterior em cinza, a seta e o valor novo em destaque, numa linha só.

O que foi retirado:

- **tema escuro**, trocado pela superfície clara e pelo verde institucional;
- **pastilhas coloridas por ação e por módulo** (azul e roxo na referência): a seção 9.7 exige que toda cor tenha função definida, e o tom colorido é do selo de estado. Ação e módulo são categoria, e ficam em pastilha neutra;
- **ícones ao lado dos títulos das seções e do título do modal**: ícone decorativo ao lado de título é proibido pela seção 9.6;
- **fonte monoespaçada e botão "Copiar"** no IP e no cliente: não há token de fonte monoespaçada na escala fechada, e o botão exigiria JavaScript próprio;
- **ícone de localização ao lado do IP**, pelo mesmo motivo dos ícones decorativos.

### D13. Ordem dos middlewares

`AuditMiddleware` entra no fim da lista, depois de `PermissionMiddleware`. A fase de requisição dele é a última a rodar, então o ator já está definido quando a view e as operações do model executam, e o `process_view` dele roda depois do que decide o acesso.

## Risks / Trade-offs

- **[Crescimento da tabela]** Toda ação e todo acesso a tela geram uma linha, e nada é expurgado. → A exclusão dos fragmentos do htmx tira o maior volume, os índices atendem à consulta e a retenção fica para uma Change própria, quando houver uso real para medir.
- **[Falha na auditoria derruba a operação]** A gravação na mesma transação faz um defeito no `record` recusar o cadastro do usuário. → O `record` é simples e sem dependência externa, e os testes cobrem cada chamada; a alternativa seria aceitar alteração sem rastro.
- **[Ator esquecido num caminho novo]** Um código futuro que rode fora da requisição sem definir o ator registra a ação como do sistema. → É o padrão seguro: a ação continua registrada, e a origem mostra que não veio da interface.
- **[Log não substitui histórico]** Só os campos alterados são guardados, então o log não reconstrói o estado completo de um registro em qualquer data. → É o que o escopo pede, e os valores anteriores e posteriores bastam para identificar o que mudou.
- **[Gravação direta no banco]** A integridade é garantida pela aplicação, e não por privilégio do PostgreSQL. → Limite conhecido e registrado na spec, coerente com o ambiente do TCC, em que a aplicação e o banco são administrados pela mesma pessoa.

## Migration Plan

1. A migration inicial do app `audit` cria a tabela, sem tocar nas tabelas existentes.
2. A migration de dados do `accounts` acrescenta `AUDITORIA.VISUALIZAR` ao catálogo e a concede ao perfil `ADMINISTRADOR`, sem alterar as demais permissões concedidas pelos perfis existentes.
3. Os registros anteriores à Change não existem: a auditoria começa na aplicação das migrations, e a consulta de uma instalação recém-atualizada mostra a lista vazia.
4. Reversão: desfazer as migrations remove a tabela e a permissão. Nenhum dado de domínio depende delas.

## Open Questions

- Nenhuma.
