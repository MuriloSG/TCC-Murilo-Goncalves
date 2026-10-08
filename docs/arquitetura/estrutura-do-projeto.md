# Estrutura do projeto

```text
.
├── compose.yaml            serviços web, worker, import_worker, db, redis e tailwind
├── Dockerfile              estágio tailwind (Node 22) e imagem da aplicação (Python 3.13)
├── Makefile                atalhos dos comandos do ambiente
├── requirements.txt        dependências Python, versões fixas
├── package.json            dependências da compilação do CSS
├── manage.py
├── config/                 settings.py, urls.py, asgi.py, wsgi.py, formats/pt_BR
├── accounts/               usuários, perfis, permissões, autenticação, comandos
├── ui/                     layouts, componentes, tokens, ícones, menu, regras de texto e visual
├── audit/                  registro e consulta da auditoria
├── outbox/                 fila e worker de e-mails
├── system_settings/        configuração do servidor SMTP
├── notices/                notificações e canal WebSocket
├── imports/                motor de importação de planilhas e worker
├── schedule/               ensalamento, espaços, disciplinas, turmas, Grade, calendário público
├── bookings/               Agenda: solicitações e agendamentos
├── panel/                  painel administrativo
├── reports/                mapa de calor e relatório de solicitações
├── docs/                   esta documentação
├── sources/                texto do TCC, logotipos e planilhas de referência
└── .claude/                configuração local do Claude Code
```

## Organização de cada app

| Arquivo | Conteúdo |
|---|---|
| `models.py` | Entidades e as operações de negócio, nos models e managers |
| `views.py` | CBVs. Cada uma declara `permission_required` e, quando a tela entra na auditoria, `audit_resource` |
| `urls.py` | Rotas, com `login_required` em toda rota autenticada |
| `forms.py` | Formulários com os campos aceitos declarados |
| `utils.py` | Funções auxiliares reaproveitadas pelo app |
| `templates/<app>/` | Templates; os que abrem em modal têm a versão `_modal.html` |
| `tests/test_*.py` | Testes do app |
| `management/commands/` | Comandos de gerenciamento |
| `migrations/` | Uma migration inicial por app, mais as posteriores (as anteriores foram consolidadas no commit `49ec2b3`) |

## Módulos que não seguem o nome padrão

| Módulo | Conteúdo |
|---|---|
| `accounts/permissions.py` | Catálogo único das permissões de todos os módulos |
| `accounts/imports.py` | `UserImport`, a importação de usuários |
| `accounts/adapters.py`, `accounts/tokens.py` | Adaptador do allauth e gerador do token de senha |
| `accounts/emails.py`, `accounts/notifications.py` | Tratador do e-mail `LINK_SENHA` e gerador da notificação de perfil alterado |
| `audit/catalog.py`, `audit/context.py` | Catálogo de ações, módulos e origens; ator da ação em `ContextVar` |
| `outbox/handlers.py`, `outbox/worker.py` | Registro de tratadores e processamento dos envios |
| `notices/catalog.py`, `notices/events.py`, `notices/realtime.py`, `notices/consumers.py` | Tipos de notificação, registro de eventos, aviso pós-commit e consumer WebSocket |
| `imports/definitions.py`, `imports/execution.py`, `imports/reader.py`, `imports/workbook.py`, `imports/worker.py`, `imports/registry.py` | Contrato da importação, execução da prévia e da confirmação, leitura CSV, leitura XLSX, worker e registro |
| `schedule/imports.py`, `schedule/sheets.py`, `schedule/activities.py` | Importação do ensalamento, leitura das abas e da célula de atividade |
| `schedule/spaces.py`, `schedule/similarity.py` | Classificação dos nomes de espaço da importação e sugestão de parecidos |
| `schedule/timetable.py`, `schedule/occupancy.py` | Montagem da Grade e cálculo das ocorrências |
| `schedule/public.py`, `schedule/public_views.py`, `schedule/public_cache.py` | Calendário público, horário original e cache |
| `bookings/occupancy.py` | Conflito de horário e a fonte de ocupação dos agendamentos |
| `bookings/notifications.py` | Notificações das transições da Agenda |
| `panel/indicators.py`, `reports/heatmap.py`, `reports/requests.py` | Cálculo dos indicadores e relatórios |
| `ui/navigation.py` | Menu lateral e página inicial depois do login |
| `ui/text_rules.py`, `ui/class_rules.py`, `ui/contrast.py` | Regras verificadas pelas varreduras de texto, de classes e de contraste |

## Interface

- `ui/styles/app.css`: tokens (`@theme`), componentes (`@layer components`) e o tema escuro do calendário público.
- `ui/static/ui/css/app.css`: CSS gerado pelo `tailwind`, fora do Git (`.gitignore`).
- `ui/static/ui/js/`: scripts próprios (modal, select, máscaras, calendário, menu, notificações, carregamento global, tema) e `htmx.min.js`.
- `ui/static/ui/fonts/` e `ui/templates/ui/icons/`: Open Sans e ícones Lucide, com as licenças ao lado.
- Layouts: `ui/layouts/app.html` (autenticado), `ui/layouts/auth.html` (login e senha) e `ui/layouts/public.html` (telas públicas).

## Comandos de gerenciamento

| Comando | App | Uso |
|---|---|---|
| `create_superadmin` | `accounts` | Cria o primeiro superadmin, com o perfil `ADMINISTRADOR` |
| `set_superadmin <email> --grant/--revoke` | `accounts` | Concede ou retira o superadmin |
| `clear_data [--yes]` | `accounts` | `TRUNCATE` de todas as tabelas, exceto usuários, perfis, permissões, sessões e e-mails do allauth. Ignora a proteção da auditoria |
| `delete_users [--yes]` | `accounts` | Exclui os usuários que não são superadmin e os registros que dependem deles. Exige um superadmin ativo |
| `set_passwords [--password X] [--yes]` | `accounts` | Define a mesma senha (padrão `DEFAULT_PASSWORD` do comando) para todos os usuários |

`clear_data`, `delete_users` e `set_passwords` só rodam com `DJANGO_ENVIRONMENT=local` (`accounts.utils.require_local_environment`).
| `process_outbox` | `outbox` | Laço do worker de e-mails |
| `process_imports` | `imports` | Laço do worker de importações |

## `sources/`

| Arquivo | Uso |
|---|---|
| `TCC_REVISADO (1).pdf` | Fonte de escopo e requisitos; princípios em [visão geral](../sistema/visao-geral.md#princípios-do-tcc) |
| `planilha_example.xlsx` | Planilha real do campus, lida por `schedule/tests/test_spreadsheet.py` |
| `planilha_example_sugerida.xlsx`, `planilha_example_sugerida_corrigida.xlsx` | Versões da planilha no formato sugerido ao campus, lidas por `schedule/tests/test_import.py` e `test_space_import.py`. As duas têm só as abas lidas pela importação, inclusive a opcional `usuários - sistema` |
| `importacao-usuarios-ensalamento.csv` | Arquivo de exemplo para a importação de usuários, sem uso nos testes |
| `Salinas/` | Logotipos do campus em JPG, TIF e CDR |
