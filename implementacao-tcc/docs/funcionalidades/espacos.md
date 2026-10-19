# Espaços

Cadastro dos espaços físicos (salas, laboratórios). Implementação: `Space`, `SpaceName` e `SpaceManager` em `schedule/models.py`; telas em `schedule/views.py`. Regras em [regras de negócio](../regras/regras-de-negocio.md#espaços).

| Ação | Rota | Permissão | Operação |
|---|---|---|---|
| Listar, buscar e filtrar | `/espacos/` | `ESPACO.VISUALIZAR` | `Space.objects.search(term, status, origin)` |
| Cadastrar | `/espacos/novo/` | `ESPACO.CRIAR` | `Space.objects.register` |
| Editar nome e outros nomes | `/espacos/<pk>/editar/` | `ESPACO.EDITAR` | `Space.update_details` |
| Desativar e reativar | `/espacos/<pk>/desativar/`, `/reativar/` | `ESPACO.ALTERAR_SITUACAO` | `Space.deactivate`, `Space.reactivate` |
| Excluir | `/espacos/<pk>/excluir/` | `ESPACO.EXCLUIR` | `Space.delete_space` |

## Dados

- **Nome atual** e **outros nomes**: grafias usadas na planilha. Todas ficam em `SpaceName`, únicas sem diferenciar a caixa em todo o cadastro. Uma grafia identifica um espaço só.
- **Origem**: `MANUAL` (cadastrado pela tela) ou `PLANILHA` (cadastrado pela confirmação de uma importação, com a importação de origem). Não muda depois da criação.
- **Situação**: ativo ou inativo.

O espaço não tem capacidade, tipo nem localização.

## Comportamento

- A busca encontra pelo nome atual ou por outro nome. A lista é ordenada pela ordem natural do nome e paginada de 5 em 5.
- Ao trocar o nome, o anterior vira outro nome, para que a próxima importação continue reconhecendo a grafia antiga.
- Desativar não altera as alocações. O espaço inativo deixa de ser oferecido em novas aulas e solicitações, mas continua na Grade do semestre em que tem aula.
- Excluir só é permitido sem aulas no ensalamento. Espaço com solicitação de agendamento também não é excluído (o `PROTECT` vira a mensagem "Desative o espaço"). A exclusão leva os outros nomes e as decisões de importação que o citam.
- Com `AUDITORIA.VISUALIZAR`, cada linha tem a ação "Ver auditoria", filtrada pelo espaço.
- Na importação do ensalamento, o cadastro também é alterado pelas decisões de espaço. Ver [ensalamento](ensalamento.md#espaços-encontrados).

## Testes

`schedule/tests/test_spaces.py`, `test_space_views.py`, `test_space_import.py`, `test_space_panel.py`, `test_similarity.py`.

O que cada classe garante está no catálogo de testes do app [`schedule`](../desenvolvimento/testes/schedule.md#espaços).
