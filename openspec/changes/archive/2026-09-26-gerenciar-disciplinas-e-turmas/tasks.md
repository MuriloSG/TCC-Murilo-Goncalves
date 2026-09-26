## 1. Preparação

- [x] 1.1 Confirmar com o autor as decisões do `design.md`: sem vínculo manual, sem permissão global nova, renomeação bloqueada com uso e disciplina identificada só pelo nome
- [ ] 1.2 Pedir ao autor as imagens de referência das listas, dos detalhes e dos modais (§9.8). Nesta etapa as telas seguem o padrão existente da lista de Espaços e do detalhe de Perfis

## 2. Permissões

- [x] 2.1 Acrescentar as constantes `SUBJECT_*` e `CLASS_GROUP_*`, os rótulos "Disciplinas" e "Turmas" e os conjuntos a `accounts/permissions.py` (D3)
- [x] 2.2 Criar a migration de dados `accounts/0013_academic_permissions`, concedendo as oito permissões ao `ADMINISTRADOR` sem alterar as demais

## 3. Escopo e operações no model

- [x] 3.1 Criar `teacher_scope`, `SubjectQuerySet.visible_to` e `ClassGroupQuerySet.visible_to`, com superadmin global e escopo pelo docente do usuário, e a busca de cada um (D1, D2)
- [x] 3.2 Criar `register` e `update_details` de disciplina e turma, sem vínculo, com o curso imutável e a renomeação recusada com uso (D7, D8)
- [x] 3.3 Criar `delete_subject` e `delete_class_group`, com `AcademicRecordInUse` (D9)
- [x] 3.4 Acrescentar os módulos `DISCIPLINA` e `TURMA` e os rótulos `curso` e `rotulo` a `audit/catalog.py` e gravar os registros em cada operação (D11)

## 4. Telas

- [x] 4.1 Acrescentar `get_target_queryset` a `OperationFormView` e `ConfirmedActionView` (D4)
- [x] 4.2 Criar os formulários de filtros, de disciplina e de turma (curso `readonly` na edição)
- [x] 4.3 Criar as views de lista, detalhe, cadastro, edição e exclusão de disciplinas e turmas, as rotas com `login_required`, os templates e os itens do menu

## 5. Testes

- [x] 5.1 Testar escopo (docente com vínculo atual e histórico, usuário sem docente, superadmin), as quatro situações de acesso de cada rota, o acesso fora do escopo por URL e por POST com 404, listagem, busca, filtro, paginação e contagens, detalhe, cadastro válido, inválido e duplicado, edição, renomeação recusada com uso, curso forjado, exclusão livre e recusada, e auditoria
- [x] 5.2 Testar a regressão da importação: reaproveitamento do cadastro manual, vínculo histórico que vira atual e Agenda sem combinação do cadastro manual
- [x] 5.3 Rodar a suíte completa com `make test`

## 6. Conferência visual

- [ ] 6.1 Conferir as telas no banco `visual_check` com o Playwright em container, em largura de desktop e de celular
