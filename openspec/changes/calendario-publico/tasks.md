## 1. Referência visual

- [x] 1.1 Pedir ao autor a imagem de referência da tela (seção 9.8 das convenções) e registrar no `design.md` o que foi adaptado e retirado
- [x] 1.2 Commit

## 2. Consulta do calendário público

- [x] 2.1 Criar `schedule/public.py` com `PublicEntry` e as opções do semestre (salas ativas e inativas com aula, docentes do ensalamento, cursos com turma alocada, níveis de `Stage`) (D5, D6)
- [x] 2.2 Criar a consulta filtrada das aulas com `select_related`, `prefetch_related` e `only`, restrita a `Allocation`, sem `occupancy()` nem `grid_sources()` (D3, D10)
- [x] 2.3 Criar a consulta dos e-mails pela correspondência exata do `username`, só de usuários ativos, só com `username` e `email`, só para os docentes das aulas encontradas (D4)
- [x] 2.4 Montar o calendário com `build_week` e as funções de datas da Grade, com as aulas por faixa ordenadas por sala, curso e turma, "turmas juntas" pela mesma sala, disciplina e docentes, sem "Choque" (D9)
- [x] 2.5 Implementar o filtro principal obrigatório, as datas obrigatórias, as recusas, o limite de 31 dias, o intervalo fora do semestre, a semana típica do semestre sem período e a navegação (D7, D8)
- [x] 2.6 Testar cada filtro, as combinações, o valor desconhecido, a caixa do nome, a sala inativa com e sem aula, o curso sem aula fora das opções, a aula sem sala e cada recusa de data
- [x] 2.7 Testar os docentes: superadmin e administrador fora das opções, docente sem usuário só com o nome, usuário inativo sem e-mail, correspondência sem diferenciar a caixa e sem aproximação
- [x] 2.8 Testar com `assertNumQueries` no máximo 8 consultas, iguais numa semana e em 31 dias, por sala, por docente e por curso, e nenhuma consulta de alocação sem filtro principal ou com data recusada
- [x] 2.9 Testar que uma fonte de ocupação de teste acrescentada a `grid_sources()` não aparece no calendário público
- [x] 2.10 Conferir os planos das consultas com `EXPLAIN` no PostgreSQL e registrar no `design.md` (D10)
- [x] 2.11 Commit

## 3. Rota, view e formulário públicos

- [x] 3.1 Criar `PublicCalendarFilterForm` com os campos, o tamanho máximo, o formato e o descarte dos valores inválidos (D6, D11)
- [x] 3.2 Criar `schedule/public_views.py` com `PublicCalendarView`, sem `permission_required`, sem `audit_resource`, sem ler `request.user`, só GET e HEAD (D1, D2)
- [x] 3.3 Acrescentar a rota `calendario/` ao `schedule/urls.py`, sem `login_required`, sem mexer nas demais rotas
- [x] 3.4 Testar: visitante recebe 200 em `calendario/`; visitante é levado ao login em `ensalamento/`; autenticado sem permissão recebe 403 em `ensalamento/` e o mesmo conteúdo em `calendario/`; POST recebe 405; nenhuma auditoria gravada; nenhum cookie definido
- [x] 3.5 Testar que o HTML não tem IDs, nome civil, perfil, permissões, outros nomes do espaço, origem, importação, auditoria, "Choque" nem token CSRF, e tem `noindex`
- [x] 3.6 Commit

## 4. Layout e tela

- [x] 4.1 Criar `ui/layouts/public.html` com o cabeçalho, os filtros, o link "Entrar" e `noindex`, sem menu, sidebar, usuário, notificações, modal e `hx-headers`; conferir que `notifications.js` não abre conexão nesta página (D12)
- [x] 4.2 Criar `schedule/templates/schedule/public/calendar.html` com os estados vazios, os erros de data, o aviso do semestre sem período e a Grade, com marcação própria e as classes `timetable-*`, sem alterar o `grid.html` (D9, D14)
- [x] 4.3 Criar o card público com disciplina, curso e turma, sala ou "Sem sala definida", docentes e e-mails (D5)
- [x] 4.4 Testar os textos da tela com as regras do app `ui` (texto e classes)
- [x] 4.5 Commit

## 5. Celular

- [x] 5.1 Filtros empilhados abaixo de 640 px, datas lado a lado, grupo "Filtros" com o resumo, alvos de 44 px (D13)
- [x] 5.2 Grade com rolagem horizontal só dentro da área, coluna de horários e linha dos dias fixas, largura mínima da coluna de dia e rolagem até "Hoje" (D13)
- [x] 5.3 Atualização pelo htmx nos selects, botão "Mostrar" para as datas, `aria-busy` durante a requisição e funcionamento sem JavaScript
- [x] 5.4 Conferir no navegador, com o banco `visual_check` e o Playwright em container, a 360 px, 390 px, 768 px e 1280 px: sem rolagem horizontal da página, filtros usáveis, uma semana e 31 dias
- [x] 5.5 Commit

## 6. Fechamento

- [x] 6.1 Rodar `make test` com a suíte inteira passando
- [x] 6.2 Rodar `openspec validate --all --strict`
- [x] 6.3 Registrar a rota pública, o layout público e a recomendação de rate limit e cache no proxy em `openspec/conventions.md`
- [x] 6.4 Commit
