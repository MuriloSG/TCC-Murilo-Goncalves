# Auditoria

Registro único das ações do sistema. Implementação: app `audit`. Regras em [regras de negócio](../regras/regras-de-negocio.md#auditoria).

## Registro

`AuditLog` guarda: usuário (pode ser vazio), ação, módulo (`resource`), identificador do registro, data e hora, origem, IP, cliente (user agent), `old_values`, `new_values` e `metadata`.

- Gravação só por `AuditLog.objects.record(action, resource, ...)` ou `record_changes(resource, id, antes, depois)`, que grava só os campos que mudaram e nada quando nada mudou.
- O registro fica na transação de quem chama: uma operação desfeita leva o registro junto.
- Ação e módulo precisam estar em `audit/catalog.py`; fora dele, `UnknownAuditCode`.
- Campos cujo nome contém `senha`, `password`, `token`, `secret`, `chave`, `hash` ou `key` são descartados (`sanitize`).
- `AuditLog.save` recusa alteração e `AuditLog.delete` recusa exclusão (`AuditLogProtected`). Não há tela, rota ou comando que altere registros. O comando de desenvolvimento `clear_data` apaga a tabela por `TRUNCATE`, fora do model.

## Ator e origem

O ator fica num `ContextVar` (`audit/context.py`):

| Origem | Quando |
|---|---|
| `INTERFACE` | Requisição HTTP (`AuditMiddleware`) e operações executadas pelo `import_worker` em nome de quem pediu |
| `IMPORTACAO` | Operações de domínio dentro da execução de uma importação (`imports/execution.py`) |
| `SISTEMA` | Padrão, sem requisição: comandos de gerenciamento e o worker de e-mails, sem usuário |

## O que é registrado

| Ação | Módulos |
|---|---|
| Entrada, entrada recusada, saída | `AUTENTICACAO` (sinais do Django e do allauth; a recusa, no `AccountAdapter`) |
| Recuperação solicitada, senha redefinida | `AUTENTICACAO` |
| Acesso a uma tela | O `audit_resource` da view, só em GET com resposta 200 e fora do htmx |
| Cadastro, alteração, exclusão, desativação, reativação | `USUARIO`, `PERFIL`, `ESPACO`, `DISCIPLINA`, `TURMA`, `CONFIGURACAO` |
| Prévia gerada (`CRIAR`), confirmação concluída (`IMPORTAR`), descarte, exclusão, falha no processamento, decisão de espaço gravada ou desfeita (`ALTERAR`) | `IMPORTACAO_USUARIO`, `IMPORTACAO_ENSALAMENTO`, com o resumo da importação e não cada linha |
| Download do modelo da planilha (`EXPORTAR`) | o módulo da importação |
| Cadastro, alteração e encerramento de aula; cancelamento de ocorrência | `ENSALAMENTO`, `EXCECAO_ENSALAMENTO` |
| Solicitação, aprovação, rejeição, sugestão, aceite, recusa, cancelamento | `SOLICITACAO_AGENDAMENTO`; criação e exclusão do agendamento em `AGENDAMENTO` |
| Publicação de notificação | `NOTIFICACAO` |
| Envio e falha de e-mail pelo worker | `EMAIL` |

Telas sem `audit_resource` (painel, relatórios, calendário público, sino de notificações) não registram acesso.

## Consulta

| Tela | Rota | Permissão |
|---|---|---|
| Lista com filtros | `/auditoria/` | `AUDITORIA.VISUALIZAR` |
| Detalhe com campos alterados e informações adicionais | `/auditoria/<pk>/` | `AUDITORIA.VISUALIZAR` |
| Opções do filtro de usuário, paginadas no servidor | `/auditoria/opcoes/usuarios/` | `AUDITORIA.VISUALIZAR` |

Filtros: usuário, ação, módulo (`recurso`), identificador do registro (`registro`), período e origem. Ordem do mais recente para o mais antigo. A lista de espaços e as de disciplinas e turmas têm atalho "Ver auditoria" filtrado pelo registro.

## Testes

`audit/tests/`: `test_records.py`, `test_changes.py`, `test_access.py`, `test_authentication.py`, `test_query.py`, `test_options.py`. Cada app testa a auditoria das próprias operações.
