## 0. Antes de implementar

- [x] 0.1 Pedir ao autor a imagem de referência da tela e registrar no `design.md` o que foi adaptado e o que foi retirado

## 1. Permissão e menu

- [x] 1.1 `PAINEL_VIEW = 'PAINEL.VISUALIZAR'` e o rótulo `PAINEL` em `accounts/permissions.py`, fora das reservadas ao superadmin
- [x] 1.2 Migration de dados que cria a permissão e a concede a `ADMINISTRADOR` sem tocar nas demais
- [x] 1.3 Item "Painel" no início do `MENU` de `ui/navigation.py`
- [x] 1.4 Testes: catálogo, migration sobre perfil alterado, redirecionamento de `inicio/` com e sem a permissão

## 2. App `panel` e rota

- [x] 2.1 App `panel` com `PanelView`, `login_required` em `painel/` e `permission_required`
- [x] 2.2 Filtro de semestre e escolha Hoje ou Semana, com valor inválido valendo o padrão
- [x] 2.3 Testes das quatro situações da rota (anônimo, sem permissão, com permissão, superadmin) e de cada bloco escondido sem a permissão do módulo, sem calcular os dados dele

## 3. Solicitações para decidir

- [x] 3.1 Contagens no banco e lista das cinco pendentes futuras
- [x] 3.2 Testes de estados, horário passado no fuso do campus, ordem, limite e estado vazio

## 4. Ocupação dos espaços

- [x] 4.1 Ocorrências de todos os espaços num intervalo em `schedule`, sobre `occurs_on` e `AllocationException.objects.cancelled`
- [x] 4.2 União dos intervalos por espaço e data, com os agendamentos, e a lista "Sem ocupação"
- [x] 4.3 Testes: aula compartilhada, cancelada, encerrada, agendamento sobreposto, fim de semana, inativo, semestre sem período, fora de semestre e quantidade fixa de consultas

## 5. Pendências da grade e importações

- [x] 5.1 Aulas vigentes sem espaço e sem docente, agrupadas por turma, disciplina, dia e faixa
- [x] 5.2 Possíveis conflitos de docente e agendamentos em choque com aula
- [x] 5.3 Importações do ensalamento sem conclusão
- [x] 5.4 Testes de cada regra, inclusive faixas encostadas, vigências que não se cruzam e importação de usuários fora

## 6. Template

- [x] 6.0 Escala `bar-w-*` e `bar-h-*` e os componentes dos cartões e das barras no `app.css`
- [x] 6.1 Template sobre `ui/layouts/app.html` com os componentes do `ui`, estados vazios e links condicionados a `perms`
- [x] 6.2 Testes do app `ui` (texto, classes e contraste) e conferência visual no banco `visual_check` em 360 px e na largura de desktop
