## 1. Modelo

- [x] 1.1 Remover a `CheckConstraint` da vigência, admitindo o fim anterior ao início como recorrência sem ocorrência (migration `0009_allocation_validity_without_occurrence`)
- [x] 1.2 Implementar `plan_ending` e `end_recurrence`, com a conferência da data, a contagem das ocorrências removidas, a transação e a auditoria
- [x] 1.3 Conferir que a reimportação preserva a aula encerrada e avisa a linha

## 2. Permissão e auditoria

- [x] 2.1 Criar `ENSALAMENTO.ENCERRAR_RECORRENCIA` e concedê-la ao `ADMINISTRADOR` (migration `0016_end_recurrence_permission`)
- [x] 2.2 Acrescentar os rótulos dos campos do encerramento ao catálogo da auditoria

## 3. Interface

- [x] 3.1 Ação "Encerrar recorrência" no card da Grade datada, de hoje em diante, para quem tem a permissão
- [x] 3.2 Confirmação com a quantidade de aulas encerradas, a data e o que continua existindo
- [x] 3.3 Mensagem de sucesso e volta para a Grade na semana da data

## 4. Verificação

- [x] 4.1 Testes do modelo, da permissão (incluindo o superadmin sem a permissão concedida), da aula que ainda não começou, das exceções, da transação, da auditoria, da Grade, do calendário público, da Agenda e da reimportação
- [ ] 4.2 Rodar `make test` e `openspec validate --strict`
- [ ] 4.3 Conferir a tela no navegador, no computador e no celular
