## 1. Modelo

- [ ] 1.1 Extrair `check_start` da conferência da data e generalizar `RecurrencePlan`, `check_duplicates` e `check_conflicts` para um plano sem alocação atual, sem mudar o comportamento da alteração
- [ ] 1.2 Criar `RecurrenceCreation`, com a gravação das alocações do bloco, a oferta e a auditoria
- [ ] 1.3 Implementar `plan_creation` e `create_recurrence` no `AllocationManager`, com permissão, vigência, duração, conflitos e transação
- [ ] 1.4 Conferir que a reimportação preserva a alocação criada no sistema e avisa a linha

## 2. Permissão e auditoria

- [ ] 2.1 Criar `ENSALAMENTO.CRIAR_RECORRENCIA` e concedê-la ao `ADMINISTRADOR` (migration `0013_create_recurrence_permission`)
- [ ] 2.2 Acrescentar os rótulos dos campos da criação ao catálogo da auditoria

## 3. Interface

- [ ] 3.1 Formulário com semestre, turma, disciplina, docentes, espaço, data de início, fim opcional, horário e duração, com os campos de escolha única no componente de busca quando ele estiver disponível
- [ ] 3.2 View e rota `ensalamento/recorrencias/criar/`, com o modal, o resumo e a confirmação
- [ ] 3.3 Gatilho na faixa disponível da Grade datada, com os dados da célula preenchidos, e botão "Cadastrar aula" no cabeçalho da Grade, para quem tem a permissão
- [ ] 3.4 Estado de foco e teclado do gatilho da célula, e o texto em `sr-only` da célula preservado

## 4. Verificação

- [ ] 4.1 Testes do modelo, da permissão (incluindo o superadmin sem a permissão concedida), dos conflitos, da duração, da vigência, da transação, da auditoria, da Grade e da reimportação
- [ ] 4.2 Rodar `make test` e `openspec validate --strict`
- [ ] 4.3 Conferir a tela no navegador, no computador e no celular
