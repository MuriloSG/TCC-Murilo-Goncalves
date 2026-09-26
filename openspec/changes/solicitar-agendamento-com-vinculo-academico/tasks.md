## 1. Modelo

- [x] 1.1 Criar `BookingRequest.teaching_assignment` (migration `0003_booking_request_teaching_assignment`)
- [x] 1.2 Implementar `teacher_of`, `check_assignment`, `check_period` e `BookingRequestManager.prepare`, e usar `prepare` em `submit`
- [x] 1.3 Registrar semestre, docente, disciplina e turma na auditoria da criação

## 2. Interface

- [x] 2.1 Formulário com disciplina e turmas do docente logado, espaço, data, horário e descrição, com o semestre da Agenda calculado pela data e as opções recarregadas pelo htmx
- [x] 2.2 Revisão antes do envio no mesmo modal
- [x] 2.3 Vínculo acadêmico no detalhe da solicitação

## 3. Verificação

- [x] 3.1 Testes do model: turma do próprio docente, de outro docente, de outro semestre, vínculo histórico, usuário que não é docente, semestre sem período, data fora do período, pendente sem bloqueio, ensalamento inalterado e rollback
- [x] 3.2 Testes da tela: disciplinas e turmas do docente logado, semestre pela data, aviso para quem não é docente, revisão e envio, IDs adulterados, semestre adulterado, espaço inválido, conflito com o ensalamento, descrição obrigatória e permissão
- [x] 3.3 Rodar `make test` e `openspec validate --all --strict`
- [x] 3.4 Conferir o fluxo no navegador, no computador e no celular
