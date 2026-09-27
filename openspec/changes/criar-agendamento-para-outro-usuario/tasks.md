## 1. Permissão

- [x] 1.1 Criar `BOOKING_CREATE = 'AGENDA.CRIAR'` em `accounts/permissions.py`, dentro de `BOOKING_PERMISSIONS`
- [x] 1.2 Criar a migration `accounts/0014_booking_create_permission`, concedendo só ao `ADMINISTRADOR`
- [x] 1.3 Atualizar `accounts/tests/test_catalog.py` (36 permissões, `AGENDA.CRIAR` no `ADMINISTRADOR` e fora do `DOCENTE`, migration idempotente e sem alterar outras concessões)

## 2. Modelo

- [x] 2.1 Criar `BookingRequest.created_by` (migration `bookings/0004_booking_request_created_by`)
- [x] 2.2 Estender `check_assignment` com curso e disciplina, e `prepare` e `submit` com o solicitante, o curso e a disciplina
- [x] 2.3 Enviar a disciplina também no fluxo "Solicitar agendamento"
- [x] 2.4 Registrar `solicitante` e `criada_por` na auditoria da criação
- [x] 2.5 Criar a consulta dos usuários ativos que correspondem a um docente com vínculo atual no semestre

## 3. Interface

- [x] 3.1 Separar o docente do `BookingRequestForm` num método e criar `BookingOnBehalfForm` com usuário e curso
- [x] 3.2 Limpar os campos seguintes pelo `HX-Trigger-Name`
- [x] 3.3 Criar `BookingOnBehalfCreateView`, a rota `agenda/criar/` e os templates do modal e da página
- [x] 3.4 Mostrar "Solicitante" e "Criada por" na revisão, no detalhe e na análise
- [x] 3.5 Entradas pela Grade, pelo cabeçalho da Agenda e pelo modal "Solicitar agendamento"

## 4. Verificação

- [x] 4.1 Testes do model: permissão, cadeia, IDs incompatíveis, `created_by`, auditoria e rollback
- [x] 4.2 Testes da tela: acesso, opções de cada nível, limpeza dos campos, revisão, envio e regras atuais da Agenda
- [x] 4.3 Rodar `make test` e `openspec validate --all --strict`
- [x] 4.4 Conferir o fluxo no navegador (banco `visual_check`), no computador e no celular
