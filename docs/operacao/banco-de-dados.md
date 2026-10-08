# Banco de dados

PostgreSQL 17 (`postgres:17` no `compose.yaml`), acessado só pelo ORM. É a única fonte de verdade: o Redis guarda apenas cache das telas públicas, e as filas de e-mail e de importação são tabelas.

## Recursos do PostgreSQL usados

O sistema depende do PostgreSQL e não roda em outro banco:

| Recurso | Uso |
|---|---|
| Extensão `btree_gist` | Criada pela migration `bookings/0001_initial` (`BtreeGistExtension`). O usuário do banco precisa de permissão para `CREATE EXTENSION` |
| `ExclusionConstraint` com `tstzrange` | `booking_no_overlap`: agendamentos do mesmo espaço não se sobrepõem |
| Índices únicos sobre `Lower(...)` | Unicidade sem diferenciar a caixa: e-mail, nome de usuário, nomes de perfil, espaço, outros nomes, docente, curso, disciplina, turma, decisão de espaço |
| Índice único parcial | `outbox_entry_pending_unique`, só para envios `A_ENVIAR` |
| `UniqueConstraint(nulls_distinct=False)` | `allocation_unique`, que trata `valid_from` nulo como valor (PostgreSQL 15 ou superior) |
| `CheckConstraint` | Períodos, faixas, intervalos de solicitação e agendamento, formato de códigos, `import_operation_matches_status` |
| `SELECT ... FOR UPDATE`, `SKIP LOCKED`, `NOWAIT` | Travas das operações de negócio e reserva de trabalho pelos workers |
| `SET lock_timeout` | Execução das importações (`IMPORT_LOCK_TIMEOUT`) |
| `JSONField` | Valores de auditoria, linhas e plano das importações, configuração SMTP |

## Migrations

- As migrations foram consolidadas antes do primeiro deploy (commit `49ec2b3`). Estado atual: `0001_initial` em cada app, mais `accounts/0002_system_roles_and_permissions`, `bookings/0002_student_count`, `bookings/0003_cancellation` e `imports/0002_processar_em_segundo_plano`.
- `accounts/0002` cria o catálogo de permissões e os perfis `ADMINISTRADOR` e `DOCENTE`, com as concessões iniciais. Os códigos estão escritos na migration, sem importar `accounts/permissions.py`.
- As migrations não rodam na subida dos containers. Rode `make migrate` depois de cada atualização.
- Em hosts Linux, migrations geradas no container ficam com dono root; ver [`README.md`](../../README.md#permissões-de-arquivos-em-hosts-linux).

## Dados e volume

- Os dados ficam no volume `postgres_data`. `make down` preserva; `make reset-db` apaga.
- O banco não publica porta no host. Acesso por `make psql`.
- Testes usam um banco temporário criado pelo test runner.

## Comandos que alteram dados em massa

Só rodam com `DJANGO_ENVIRONMENT=local` ([configuração](configuracao.md#identificação-da-instalação)); fora disso são recusados antes de acessar o banco. Pedem confirmação, exceto com `--yes`.

| Comando | Efeito |
|---|---|
| `make clear-data` (`clear_data`) | `TRUNCATE ... RESTART IDENTITY CASCADE` em todas as tabelas, exceto `accounts`, `account` (allauth), `auth`, `contenttypes` e `sessions`. Apaga também a auditoria e invalida o cache público |
| `make delete-users` (`delete_users`) | Exclui os usuários que não são superadmin e, em cascata, o que depende deles (solicitações, importações enviadas). Referências anuláveis, como o usuário de um registro de auditoria, passam a nulo. Exige superadmin ativo |
| `make set-passwords` (`set_passwords`) | Define a mesma senha para todos os usuários, inclusive superadmins e inativos |

## Lacunas

- Não há rotina de backup nem de restauração no repositório.
- O comando nativo `flush` do Django apaga todas as tabelas e não tem a trava de ambiente, porque o `TransactionTestCase` o chama a cada teste. Não há alvo do `Makefile` nem script que o chame.
- Não há política de retenção para `AuditLog`, `Notification`, `OutboxEntry` e importações antigas; as tabelas só crescem.
