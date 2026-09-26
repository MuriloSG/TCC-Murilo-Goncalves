## 1. Modelo

- [x] 1.1 Criar `valid_from` e `valid_until` em `Allocation`, a restrição de identidade com `valid_from` e a `CheckConstraint` da vigência (migration `0006_allocation_validity`)
- [x] 1.2 Considerar a vigência em `occurs_on` e em `active_on`
- [x] 1.3 Preservar as alocações versionadas em `AllocationManager.apply` e avisar a linha da importação
- [x] 1.4 Implementar `plan_recurrence` e `change_recurrence`, com data, horário do bloco, exceções, conflitos, transação e auditoria

## 2. Permissão e auditoria

- [x] 2.1 Criar `ENSALAMENTO.ALTERAR_RECORRENCIA` e concedê-la ao `ADMINISTRADOR` (migration `0012_change_recurrence_permission`)
- [x] 2.2 Acrescentar o módulo `ENSALAMENTO` e os rótulos dos campos novos ao catálogo da auditoria

## 3. Interface

- [x] 3.1 Ação "Alterar recorrência" no card da Grade datada, de hoje em diante, para quem tem a permissão
- [x] 3.2 Modal com formulário, resumo "Antes / A partir de / Depois" e confirmação
- [x] 3.3 Incluir a vigência nas colunas carregadas pelo calendário público

## 4. Verificação

- [x] 4.1 Testes do modelo, da permissão, dos conflitos, das exceções, da transação, da auditoria, da Grade, do calendário público, da Agenda e da reimportação
- [x] 4.2 Rodar `make test` e `openspec validate --strict`
- [x] 4.3 Conferir a tela no navegador, no computador e no celular
