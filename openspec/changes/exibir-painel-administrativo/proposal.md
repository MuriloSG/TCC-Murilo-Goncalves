## Why

Depois do login, o administrador cai no primeiro módulo do menu (`HomeView` e `first_url_for`), em geral a Grade do Ensalamento. Para saber se há solicitação de agendamento esperando decisão, aula sem sala, importação parada ou espaço ocioso na semana, ele precisa abrir a Agenda, a Grade sala por sala e a lista de importações. Nenhuma tela reúne o que pede ação.

O levantamento de indicadores da Direção de Ensino (`levantamento_indicadores_direcao_ensino_revisado.pdf`) lista 24 indicadores. Esta Change implementa a primeira versão do painel com os que os dados atuais sustentam sem cálculo enganoso e que levam a uma ação no sistema. Os demais ficam registrados no `design.md` como adiados, com o motivo.

## What Changes

- Nova rota autenticada `painel/`, com a permissão nova `PAINEL.VISUALIZAR`, concedida pela migration ao perfil de sistema `ADMINISTRADOR`.
- O item "Painel" entra em primeiro lugar no menu. Quem tem a permissão passa a abrir o painel depois do login, pela regra já existente do primeiro item liberado.
- O painel tem quatro blocos, e cada um só aparece a quem tem também a permissão do módulo de onde vêm os dados:
  - **Solicitações para decidir** (`AGENDA.ANALISAR`): contagem das pendentes, das pendentes com horário já passado e das alternativas sugeridas esperando resposta, e a lista das cinco pendentes mais próximas de acontecer.
  - **Ocupação dos espaços** (`ENSALAMENTO.VISUALIZAR`): horas ocupadas por espaço, hoje ou na semana atual, escolhidas por um campo de seleção, com aulas não canceladas e agendamentos aprovados, sem contar duas vezes o mesmo intervalo; e os espaços ativos sem ocupação no período.
  - **Pendências da grade** (`ENSALAMENTO.VISUALIZAR`): aulas sem espaço, aulas sem docente e possíveis conflitos de docente no semestre escolhido, e agendamentos em choque com uma aula.
  - **Importações sem conclusão** (`ENSALAMENTO.IMPORTAR`): importações do ensalamento que não foram confirmadas nem descartadas.
- Filtro de semestre para os dados acadêmicos, com o semestre do dia como padrão. Hoje e a semana atual são sempre datas do calendário, e não do filtro.
- Nenhum percentual de ocupação: o sistema não registra a disponibilidade total de cada espaço.

### Fora do escopo

- Indicadores adiados ou descartados listados no `design.md` (comparação entre semestres, carga por docente, distribuição por curso, tempo médio de decisão, mapa de calor, conflitos de turma, entre outros).
- Gráficos, exportação, atualização automática em tempo real e relatórios administrativos (usuários, auditoria, e-mails).
- Qualquer ação executada a partir do painel. O painel só leva às telas que já executam cada ação, com as permissões delas.
- Alteração de modelos existentes. Não há migration de esquema, só a de dados da permissão.

## Capabilities

### New Capabilities

- `painel-administrativo`: o painel, seus blocos, regras de cálculo, filtros e estados vazios.

### Modified Capabilities

- `controle-acesso`: a permissão `PAINEL.VISUALIZAR` e a regra de que ela não concede acesso aos dados dos módulos.
- `interface`: o item "Painel" no menu.

## Impact

- App novo `panel` (views, consultas, template, testes), criado só com o que esta Change usa.
- `accounts/permissions.py` e uma migration de dados para `PAINEL.VISUALIZAR`.
- `ui/navigation.py`: item "Painel" no início do `MENU`.
- `schedule`: uma consulta das ocorrências de todos os espaços num intervalo, com o mesmo filtro de cancelamento de `AllocationException.objects.cancelled` e a mesma regra de `Allocation.occurs_on`.
- Reaproveita `BookingRequest.Status`, `BookingRequest.OPEN`, `Allocation.objects.active_on`, `imported_semesters`, `current_semester_code`, `listed_spaces`, `natural_key` e as rotas existentes da Agenda, do Ensalamento e das importações.
- Tela nova: a referência visual é pedida ao autor antes da implementação (seção 9.8 das convenções).
