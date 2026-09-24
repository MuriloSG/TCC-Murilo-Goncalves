## Why

O sistema não guarda nenhum histórico do que é feito nele. Hoje é impossível saber quem cadastrou, editou, desativou ou importou um usuário, quem alterou as permissões de um perfil, quem entrou no sistema e quando, ou quantas tentativas de login foram recusadas. Com a gestão de usuários, os perfis e a importação por planilha já em uso, e com as reservas por vir, o autor pediu um mecanismo centralizado de auditoria que registre as ações desde a autenticação até o encerramento da sessão, e que aceite as ações dos próximos módulos sem estrutura nova.

## What Changes

- **App `audit`** com uma tabela única de registros (`AuditLog`) e um ponto único de gravação (`AuditLog.objects.record`). Nenhuma funcionalidade grava log por conta própria.
- **Ator da ação num contexto de execução**, definido pelo middleware para as requisições, e marcado como sistema nos comandos e no worker. O registro guarda o usuário responsável, o endereço IP, o cliente e a origem da operação (interface, sistema ou importação).
- **Auditoria da autenticação:** login realizado, login recusado (com o e-mail informado e sem a senha), logout, solicitação de recuperação de senha e redefinição de senha.
- **Auditoria do acesso às funcionalidades:** cada tela auditável declara o recurso, e o middleware registra o acesso. Arquivos estáticos, fragmentos do htmx e requisições internas de renderização ficam de fora.
- **Auditoria das alterações de dados** nas operações do model que já concentram as regras de negócio: cadastro, edição, troca de perfil, desativação e reativação de usuário; criação, edição, alteração de permissões e exclusão de perfil; prévia, confirmação e descarte de importações; download do modelo de importação.
- **Auditoria das ações automáticas:** o worker do outbox registra o envio e a falha definitiva de cada e-mail, sem usuário responsável.
- **Valores anteriores e posteriores** das alterações, só com os campos que mudaram. Senhas, tokens e demais segredos nunca chegam ao registro, garantido no ponto único de gravação.
- **Integridade:** os registros só podem ser inseridos. A aplicação recusa alteração e exclusão de registros de auditoria, e não oferece nenhuma ação de interface para isso.
- **Consulta** em uma tela nova, "Auditoria", protegida pela permissão nova `AUDITORIA.VISUALIZAR`, com filtros por usuário, ação, recurso, identificador do recurso, período e origem, ordem do mais recente para o mais antigo, paginação e detalhe de cada registro em modal.

### Fora do escopo

- Expurgo, arquivamento ou limite de retenção dos registros.
- Exportação dos registros de auditoria para arquivo.
- Registro das recusas de acesso (403) e do bloqueio por excesso de tentativas de login, que o allauth recusa antes de avaliar as credenciais.
- Alteração de senha pelo próprio usuário autenticado e alterações de configurações do sistema, fluxos que ainda não existem. Quando existirem, entram como ações novas no mesmo mecanismo.
- Auditoria das consultas públicas de disponibilidade, que ainda não existem.

## Capabilities

### New Capabilities

- `auditoria`: mecanismo centralizado de registro das ações, conteúdo e integridade de cada registro, ações auditadas em cada módulo existente e consulta dos registros.

### Modified Capabilities

- `controle-acesso`: o catálogo passa a ter a permissão `AUDITORIA.VISUALIZAR`, concedida ao perfil `ADMINISTRADOR` pela migration, e a correspondência entre operações e permissões passa a cobrir a consulta da auditoria.
- `interface`: a lista de registros de auditoria entra na relação de listas paginadas.

## Impact

- **`audit` (novo):** `models.py` (`AuditLog` e o `record`), `catalog.py` (ações, recursos e rótulos), `context.py` (ator da ação), `middleware.py` (ator e registro do acesso), `signals.py` (autenticação), `forms.py`, `views.py`, `urls.py`, templates da consulta, migration inicial e testes.
- **`accounts`:** chamadas do registro nas operações de `User` e `Role`, recusa de login no `AccountAdapter`, solicitação de recuperação no `PasswordResetForm`, `audit_resource` nas views, permissão `AUDITORIA.VISUALIZAR` no catálogo e migration de dados que a concede ao `ADMINISTRADOR`.
- **`imports`:** registro da prévia, da confirmação, do descarte e do download do modelo, e origem "importação" nas linhas executadas.
- **`outbox`:** registro do envio e da falha definitiva pelo worker, com ator do sistema.
- **`ui`:** item "Auditoria" na navegação e ícone novo da biblioteca Lucide.
- **`config`:** `audit` em `INSTALLED_APPS` e `AuditMiddleware` no fim da lista de middlewares.
- **Sem dependência nova** e sem alteração nas tabelas existentes.

## Alinhamento com o TCC

- **RNF01 e P5:** a auditoria completa o controle de acesso ao permitir verificar quem executou cada operação protegida e quem tentou entrar sem conseguir.
- **P2 e P4:** o registro tem um único ponto de gravação e as ações ficam nas operações do model, sem lógica de log espalhada pelas views.
- **RNF05 e P7:** a consulta usa o mesmo padrão de lista, filtros e paginação das demais telas, com os termos do domínio.
- **P9:** cada ação auditada e a integridade dos registros são verificadas por testes.
