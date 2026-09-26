## 1. Referência visual

- [ ] 1.1 Pedir ao autor a imagem de referência da Agenda, do modal de solicitação e das listas de solicitações (seção 9.8 das convenções) e registrar no `design.md` o que foi adaptado e retirado (D14)
- [ ] 1.2 Commit

## 2. Permissões e app

- [x] 2.1 Criar o app `bookings` e acrescentar ao catálogo `accounts/permissions.py`, onde ficam as permissões de todos os módulos, `AGENDA.VISUALIZAR`, `AGENDA.SOLICITAR`, `AGENDA.ANALISAR` e o rótulo do recurso `AGENDA` (D2)
- [x] 2.2 Migration de dados com as três permissões, `ADMINISTRADOR` com as três e `DOCENTE` com `AGENDA.VISUALIZAR` e `AGENDA.SOLICITAR`, sem alterar as demais concessões
- [x] 2.3 Testar o catálogo, as concessões e que nenhuma delas é reservada ao superadmin
- [x] 2.4 Commit

## 3. Models e estados

- [x] 3.1 Migration da extensão `btree_gist` (D3)
- [x] 3.2 Criar `BookingRequest` e `Booking` com as restrições, a `ExclusionConstraint` e os índices (D3, D13)
- [x] 3.3 Criar `bookings/occupancy.py` com `conflicts()` em duas consultas, intervalo `[início, fim)` (D5)
- [x] 3.4 Criar as operações `submit`, `approve`, `reject`, `suggest`, `accept_suggestion` e `decline_suggestion`, com `transaction.atomic`, `select_for_update` da solicitação e do espaço, verificação de estado e ator e `InvalidTransition` (D4, D6)
- [x] 3.5 Testar cada transição válida, cada transição inválida, os campos obrigatórios, o passado, fim antes do início, espaço inativo, bordas `14:00–15:00`/`15:00–16:00`, conflito com alocação e com agendamento
- [x] 3.6 Testar em `TransactionTestCase` duas aprovações sobrepostas simultâneas: só uma cria agendamento
- [x] 3.7 Commit

## 4. Auditoria

- [x] 4.1 Acrescentar os recursos `SOLICITACAO_AGENDAMENTO` e `AGENDAMENTO` e as ações `APROVAR`, `REJEITAR`, `SUGERIR`, `ACEITAR` e `RECUSAR` ao `audit/catalog.py` (D9)
- [x] 4.2 Registrar cada transição e a criação do agendamento nas operações do model
- [x] 4.3 Testar um registro por transição e nenhum registro nas recusas
- [x] 4.4 Commit

## 5. Grade da Agenda

- [x] 5.1 Criar `BookingSource` e `agenda_sources()`, sem mudar `grid_sources()` (D7)
- [x] 5.2 Criar `AgendaGridView`, a rota `agenda/`, o template e os cards com os selos "Ensalamento" e "Agendamento", reaproveitando `timetable.py` e as classes `timetable-*`, sem alterar o `grid.html` (D7)
- [x] 5.3 Acrescentar o item "Agenda" ao menu, visível com `AGENDA.VISUALIZAR`
- [x] 5.4 Testar as quatro situações de acesso, o agendamento aprovado na Grade, a solicitação pendente fora da Grade, a Grade do Ensalamento sem agendamentos e a quantidade fixa de consultas
- [x] 5.5 Commit

## 6. Solicitação

- [ ] 6.1 Criar o formulário e o modal "Solicitar agendamento" com os campos preenchidos pela faixa (D8)
- [ ] 6.2 Criar "Minhas solicitações", o detalhe com original e alternativa, e as ações "Aceitar alternativa" e "Recusar alternativa" (D1)
- [ ] 6.3 Testar as quatro situações de acesso de cada rota, a descrição obrigatória, o horário ocupado e o 404 em solicitação de outro usuário
- [ ] 6.4 Commit

## 7. Análise

- [ ] 7.1 Criar "Solicitações para análise", o detalhe e as ações "Aprovar", "Rejeitar" e "Sugerir alternativa" em modal (D1)
- [ ] 7.2 Testar as quatro situações de acesso de cada rota, a aprovação com o horário ocupado depois da solicitação, o motivo obrigatório da rejeição e a ausência de dados pessoais além do nome e do e-mail do solicitante
- [ ] 7.3 Testar a quantidade fixa de consultas das listas
- [ ] 7.4 Commit

## 8. Fechamento

- [ ] 8.1 Conferir as telas no navegador com o banco `visual_check` e o Playwright em container, a 360 px e 1280 px
- [ ] 8.2 Conferir os planos com `EXPLAIN` e registrar no `design.md` (D13)
- [ ] 8.3 Atualizar o glossário da seção 9.4 das convenções e dos testes do app `ui` (D12)
- [ ] 8.4 Rodar `make test` e `openspec validate --all --strict`
- [ ] 8.5 Commit
