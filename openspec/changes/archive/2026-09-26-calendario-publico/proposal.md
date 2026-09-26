## Why

O TCC prevê uma consulta pública, sem autenticação, dos horários do campus (RF11, RNF03 e o ator "Visualizador" do diagrama de casos de uso). Hoje o ensalamento só é visto na Grade autenticada (`ensalamento/`), que exige `ENSALAMENTO.VISUALIZAR`, mostra uma sala por vez e está ligada às fontes de ocupação que, no futuro, vão incluir reservas.

Alunos e docentes consultam o horário principalmente pelo celular e precisam procurar por sala, por docente ou por curso, o que a Grade atual não oferece. Esta Change cria uma página pública, isolada da área autenticada, que só lê o ensalamento acadêmico confirmado e mostra o mínimo necessário para montar o calendário.

## What Changes

- **Rota pública própria**, `calendario/`, só GET, sem `login_required`, sem `permission_required` e sem `audit_resource`, atendida por uma view nova, `PublicCalendarView`. Nenhuma view autenticada perde a autenticação e nenhuma permissão nova é criada.
- **Consulta pública própria** (`schedule/public.py`), restrita a `Allocation`, com os filtros aplicados no banco, no máximo 8 consultas por requisição, sem passar por `occupancy()` nem por `grid_sources()`, para que reservas, exceções ou outras fontes futuras nunca apareçam na página pública.
- **Filtros** pela URL, combinados por "e": semestre letivo, sala, docente, curso, nível (Graduação ou Ensino médio), data inicial e data final. Os valores são nomes e códigos, nunca IDs.
- **Docente** vindo só de `Teacher` com alocação no semestre, nunca da tabela de usuários. O card mostra o nome e, quando existe um usuário ativo cujo `username` corresponde exatamente ao nome do docente, o e-mail desse usuário.
- **Filtro principal obrigatório**: as aulas só são consultadas com sala, docente ou curso escolhido.
- **Datas obrigatórias**, com a data final igual ou posterior à inicial e no máximo 31 dias de intervalo.
- **Calendário na estrutura da Grade** (`build_week`, `Week`, `Day`, classes `timetable-*`), com um card próprio que mostra a sala, o docente e o e-mail e nunca mostra "Choque".
- **Layout público** (`ui/layouts/public.html`), só com o cabeçalho, os filtros e o calendário, sem menu, usuário, notificações, modal nem token CSRF, e com `noindex`.
- **Mobile como requisito principal**: filtros empilhados, controles de toque, datas nativas e o mesmo calendário em grade, com a rolagem horizontal só dentro da área do calendário.

### Fora do escopo

- Reserva, solicitação, agendamento, edição, cancelamento, login, cadastro e qualquer ação administrativa.
- Reservas, exceções ou outras fontes de ocupação na página pública.
- Permissão para acessar o calendário público.
- Filtro por período ou ano da turma ("4º período", "1º ano"), por turma e por disciplina.
- Níveis além de Graduação e Ensino médio.
- Cache, rate limit e qualquer infraestrutura de proxy; ficam como recomendação para a implantação.
- Mudança no model, migration, índice novo e mudança no `grid.html` autenticado.

## Capabilities

### New Capabilities

- `calendario-publico`: a consulta pública do ensalamento, com a rota, o isolamento da área autenticada, os dados expostos, os filtros, as datas, a montagem do calendário, o celular, os estados vazios, os limites e o desempenho.

### Modified Capabilities

- `controle-acesso`: o requisito da autenticação exigida passa a listar o calendário público entre as rotas públicas, que não são funcionalidade protegida por permissão.

## Impact

- **`schedule/public.py`** (novo): opções, consulta, e-mails dos docentes e montagem do calendário público.
- **`schedule/public_views.py`** (novo): `PublicCalendarView`.
- **`schedule/forms.py`**: `PublicCalendarFilterForm`.
- **`schedule/urls.py`**: a rota `calendario/`, sem `login_required`.
- **`schedule/templates/schedule/public/`** (novo): a página e o card público.
- **`ui/templates/ui/layouts/public.html`** (novo) e ajustes no `ui/styles/app.css` para os filtros e o calendário público no celular.
- **Sem migration** e sem mudança em view, formulário ou template autenticados.
- **Testes** em `schedule/tests/test_public_calendar.py`.
