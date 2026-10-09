# Decisões técnicas

Decisões que explicam a forma atual do sistema, com o motivo registrado na época. Quando o motivo não foi registrado, isso é dito.

Os registros originais, com as alternativas avaliadas, ficaram no histórico do Git, no diretório `openspec/changes/` do commit `2dae843` (por exemplo, `git show 2dae843:openspec/changes/archive/2026-09-19-enviar-emails-por-outbox/design.md`).

| # | Decisão |
|---|---|
| 1 | [Monólito Django com regras de negócio no model](#1-monólito-django-com-regras-de-negócio-no-model) |
| 2 | [Acesso por `login_required` na URL e `PermissionMiddleware`](#2-acesso-por-login_required-na-url-e-permissionmiddleware) |
| 3 | [RBAC próprio, um perfil por usuário, superadmin como atributo](#3-rbac-próprio-um-perfil-por-usuário-superadmin-como-atributo) |
| 4 | [E-mails pelo outbox transacional](#4-e-mails-pelo-outbox-transacional) |
| 5 | [Prévia da importação por executar e desfazer](#5-prévia-da-importação-por-executar-e-desfazer) |
| 6 | [Fila de trabalho no PostgreSQL, sem broker](#6-fila-de-trabalho-no-postgresql-sem-broker) |
| 7 | [Auditoria em tabela única, só de inclusão](#7-auditoria-em-tabela-única-só-de-inclusão) |
| 8 | [Docente sem chave para usuário; correspondência pelo `username`](#8-docente-sem-chave-para-usuário-correspondência-pelo-username) |
| 9 | [Ocupação calculada e vigência na própria alocação](#9-ocupação-calculada-e-vigência-na-própria-alocação) |
| 10 | [Solicitação e agendamento separados, sobreposição barrada no banco](#10-solicitação-e-agendamento-separados-sobreposição-barrada-no-banco) |
| 11 | [Notificações com model próprio e Channels em memória](#11-notificações-com-model-próprio-e-channels-em-memória) |
| 12 | [Cache das telas públicas no Redis com invalidação por geração](#12-cache-das-telas-públicas-no-redis-com-invalidação-por-geração) |
| 13 | [Servidor SMTP configurado no banco, senha cifrada](#13-servidor-smtp-configurado-no-banco-senha-cifrada) |
| 14 | [Interface sem dependências externas em tempo de execução](#14-interface-sem-dependências-externas-em-tempo-de-execução) |
| 15 | [Comandos destrutivos só no banco local comprovado](#15-comandos-destrutivos-só-no-banco-local-comprovado) |

## 1. Monólito Django com regras de negócio no model

**Decisão.** Uma aplicação Django no padrão MTV, com um app por domínio. Operações de model e de manager concentram as regras, em transação, e lançam `ValidationError` ao recusar. Views e comandos só as chamam. Não há camada de serviços nem API.

**Motivo registrado.** Tecnologias e separação de camadas definidas no TCC (princípios P1 e P2). A mesma operação atende tela, importação e comando, o que permite a prévia por executar e desfazer (decisão 5).

## 2. Acesso por `login_required` na URL e `PermissionMiddleware`

**Decisão.** Autenticação declarada no `urls.py`; permissão declarada na view (`permission_required`) e verificada num só ponto, o `PermissionMiddleware`, antes da view e para todos os métodos. Sem mixins de acesso.

**Motivo registrado.** A autenticação fica visível na tabela de rotas e a autorização num único ponto; uma rota com permissão que esqueça o `login_required` ainda manda o anônimo ao login. A matriz `test_route_protection.py` falha para rota não classificada.

## 3. RBAC próprio, um perfil por usuário, superadmin como atributo

**Decisão.** `User`, `Role` e `Permission` próprios, com tabelas intermediárias explícitas. Exatamente um perfil por usuário (restrição no banco), mas modelado como N:N para liberar vários perfis com uma migration. Superadmin é `User.is_superadmin`, controlado por comando, e não precisa de perfil. As permissões `PERFIL.*` e `CONFIGURACAO.EDITAR` são reservadas ao superadmin. Regra de continuidade administrativa. Sem `django.contrib.admin`.

**Motivo registrado.** O admin do Django autoriza por `is_staff`, `is_superuser` e `auth.Permission`, o que criaria um segundo sistema de autorização e contornaria as operações que garantem as invariantes.

**Consequência.** Nenhum perfil é fixo no código: os criados pela carga inicial são dados e se comportam como os demais. Permissão nova nasce sem concessão, e o superadmin a concede pela tela de perfis. O superadmin não depende de perfil.

## 4. E-mails pelo outbox transacional

**Decisão.** O e-mail é gravado como intenção (`OutboxEntry`) na transação da operação e enviado por um worker com novas tentativas. O conteúdo é montado no envio; nenhum token é gravado. Vale também para a recuperação de senha, para que a requisição não fale com o SMTP.

**Motivo registrado.** Permitir que a prévia da importação desfaça os envios junto com os cadastros, e tirar o envio da requisição. Celery e Redis ficaram fora de escopo.

**Consequência.** Entrega pelo menos uma vez: uma queda entre o envio e o commit pode repetir o e-mail.

## 5. Prévia da importação por executar e desfazer

**Decisão.** A prévia roda as operações reais do domínio num savepoint, cada linha no seu, e faz rollback. A confirmação reexecuta e só aplica se o plano for idêntico ao da prévia.

**Motivo registrado.** Validar separado de aplicar poria a regra em dois lugares e exigiria simular a continuidade administrativa, contra o P2. Erros que só o banco detecta aparecem já na prévia.

## 6. Fila de trabalho no PostgreSQL, sem broker

**Decisão.** Importações e e-mails usam a própria tabela como fila, com `select_for_update(skip_locked=True)`, e um worker por tipo (`process_outbox`, `process_imports`).

**Motivo registrado.** O pedido e a tarefa são a mesma linha, gravada no mesmo commit; nenhum broker dispensaria a trava da importação e os campos de execução no banco, e uma queda entre o commit e a publicação no Celery deixaria operação sem tarefa. O volume (poucas importações por semestre) não justifica Celery. Threads no processo web foram descartadas por não terem recuperação.

## 7. Auditoria em tabela única, só de inclusão

**Decisão.** `AuditLog` único, com códigos de ação, módulo e origem de um catálogo, gravado na transação da operação, com o ator num `ContextVar`. O model recusa alteração e exclusão.

**Motivo registrado.** Pedido de tabela centralizada; uma tabela por módulo exigiria estrutura nova a cada módulo. `GenericForeignKey` foi recusada porque prenderia o log ao `ContentType` e o log também registra o que não é model (autenticação, acesso a telas).

## 8. Docente sem chave para usuário; correspondência pelo `username`

**Decisão.** `Teacher` guarda o nome como a planilha traz. A correspondência com o usuário é `User.username` igual a `Teacher.name`, sem diferenciar a caixa, calculada a cada uso (`teacher_of`). Nenhuma similaridade.

**Motivo registrado.** Nem todo docente é usuário e vice-versa. A lista real tem nomes com prefixo comum (`Gera Jr.` e `Gera Magela`), em que qualquer heurística atribuiria aula a outra pessoa. Ignorar acentos exigiria `unaccent` e índice próprio, sem justificativa para os poucos casos.

**Consequência.** Escopo de disciplinas e turmas e cancelamento de ocorrência dependem do `username` estar preenchido e igual ao nome da planilha. A solicitação de agendamento não depende: basta `AGENDA.SOLICITAR`, e a turma é opcional.

## 9. Ocupação calculada e vigência na própria alocação

**Decisão.** A alocação é a regra semanal; as ocorrências de um intervalo são calculadas a cada leitura, com o período do semestre, a vigência e as exceções. A alteração de recorrência encerra a alocação na véspera e cria outra versão (`valid_from`, `valid_until`), sem tabela de versões.

**Motivo registrado.** Tabela de versões separada exigiria mudar todas as leituras. As versões não se sobrepõem, então nenhuma data tem duas aulas da mesma regra.

## 10. Solicitação e agendamento separados, sobreposição barrada no banco

**Decisão.** `BookingRequest` (pedido e decisão) e `Booking` (uso aprovado) em tabelas próprias, sem tocar em `Allocation`. `ExclusionConstraint` com `btree_gist` impede agendamentos sobrepostos no mesmo espaço; aprovação e aceite travam o espaço antes de conferir o conflito com o ensalamento.

**Motivo registrado.** O original e a alternativa aparecem lado a lado sem tabela de eventos. O ensalamento não pode ser coberto por restrição de banco por ser regra semanal, e a importação continua sem detecção de conflito (risco registrado: agendamento aprovado antes de uma reimportação que ocupe o mesmo horário continua existindo).

## 11. Notificações com model próprio e Channels em memória

**Decisão.** Model próprio no app `notices`, uma linha por destinatário. Tempo real por Django Channels com `InMemoryChannelLayer`; o evento só avisa que algo mudou e a página busca o estado por HTTP.

**Motivo registrado.** A `django-notifications-hq` (1.8.3) não roda com Python 3.13 e Django 5.2 (verificado em 24/09/2026). O motivo da escolha do `InMemoryChannelLayer` não está registrado além de dispensar infraestrutura; a limitação a um processo foi reconhecida quando as importações passaram para o worker, e por isso o andamento delas usa polling.

**Revisão em 08/10/2026.** Com `DJANGO_REDIS_URL`, a camada passou a ser o `RedisChannelLayer`, no Redis já usado pelo cache público, para que as notificações criadas pelo `import_worker` (troca de perfil na importação de usuários) cheguem ao sino. Um segundo Redis foi descartado; a política `allkeys-lru` e os 64 MB não mudaram, e por isso as chaves do Channels podem ser descartadas sob pressão de memória. Sem a URL, a camada continua em memória, com o aviso `notices.W001`. O cache `default` dos limites do allauth continua `LocMemCache`.

## 12. Cache das telas públicas no Redis com invalidação por geração

**Decisão.** Alias `public` com `RedisCache` nativo do Django, só para `/` e `/horario-original/`. Invalidação global incrementando `public:generation` depois do commit de qualquer escrita relevante. O cache `default` continua `LocMemCache`.

**Motivo registrado.** Quase toda escrita afeta vários caches; um mapa fino de dependências erraria por omissão. As escritas são raras perto das leituras, então invalidar tudo custa pouco. `delete` por chave, `cache.clear()` e só TTL foram descartados. O `default` não mudou porque guarda os limites de tentativas do allauth.

## 13. Servidor SMTP configurado no banco, senha cifrada

**Decisão.** `SystemSetting` genérico, uma linha por tipo, com esquema próprio. A senha SMTP é cifrada com Fernet e chave de `DJANGO_CREDENTIALS_KEY`. Sem configuração, nenhum e-mail sai e o outbox retém os envios sem gastar tentativas.

**Motivo registrado.** Uma única fonte para as credenciais, alterável sem reiniciar containers (lida a cada lote). Configuração global porque o sistema atende um campus.

## 14. Interface sem dependências externas em tempo de execução

**Decisão.** Templates do Django com Tailwind CSS compilado num container próprio; htmx, ícones Lucide e fonte Open Sans copiados para o projeto. Tokens fechados e regras de texto verificadas por testes.

**Motivo registrado.** Consistência visual exigida pelo TCC (P8). Fontes e scripts por CDN dependeriam de rede externa, que pode ser instável, e enviariam o IP de cada acesso a terceiros. A rede só é usada na construção da imagem do `tailwind`. Os detalhes estão na seção 9 das [convenções](../desenvolvimento/convencoes.md#9-interface-e-texto).

## 15. Comandos destrutivos só no banco local comprovado

**Decisão.** `clear_data`, `delete_users` e `set_passwords` só rodam quando `settings.ENVIRONMENT` é exatamente `local`, lido de `DJANGO_ENVIRONMENT`. Ausente, vazio, outro valor ou valor ambíguo recusam com `CommandError`, na primeira linha do `handle()`, antes de qualquer consulta, prompt ou escrita. A função, na época `require_local_environment`, hoje é `accounts.utils.require_safe_database` (ver a revisão abaixo).

**Motivo registrado.** Os três comandos apagam dados ou trocam todas as senhas, inclusive dos superadmins, e o repositório não tinha como distinguir a máquina de desenvolvimento de outras instalações. `DEBUG` não serve como evidência, porque o padrão do `compose.yaml` é `1` e uma instalação mal configurada o herdaria. O padrão da variável é vazio, então a falta de configuração nega.

**Consequência.** Na máquina de desenvolvimento, `DJANGO_ENVIRONMENT=local` precisa estar no `.env`. Em 08/10/2026 o `flush` ganhou a mesma trava, por um comando do projeto que o substitui; o banco de teste criado pelo runner (`config/test_runner.py`) fica dispensado, porque o `TransactionTestCase` o usa a cada teste.

**Revisão em 08/10/2026.** O ambiente identificava a instalação, e não o banco: com `local` no `.env` e `POSTGRES_HOST` apontando para outro servidor, os quatro comandos rodavam. A trava passou a ser `accounts.utils.require_safe_database`, que exige também `DJANGO_LOCAL_DATABASE` igual a `host:porta/nome` da conexão e, no banco conectado, o mesmo nome e a marca `ifagenda.environment = 'local'` (`make mark-local-db`). A marca fica no próprio banco, e não em convenção de nome, para que um banco operacional nunca seja tomado por local. O runner continua liberando só os bancos que criou. Detalhes em [configuração](../operacao/configuracao.md#identificação-da-instalação-e-do-banco-local).
