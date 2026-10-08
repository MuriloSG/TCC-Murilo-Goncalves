# Disciplinas e turmas

Consulta e manutenção dos cadastros acadêmicos que o ensalamento usa. Implementação: `Subject`, `ClassGroup`, `ClassOffering`, `TeachingAssignment` e `teacher_scope` em `schedule/models.py`; telas em `schedule/views.py`. Regras em [regras de negócio](../regras/regras-de-negocio.md#disciplinas-turmas-e-vínculos).

| Ação | Disciplinas | Turmas | Permissão |
|---|---|---|---|
| Listar e buscar | `/disciplinas/` | `/turmas/` (busca por rótulo ou curso, filtro por curso) | `DISCIPLINA.VISUALIZAR`, `TURMA.VISUALIZAR` |
| Detalhe com as ofertas por semestre | `/disciplinas/<pk>/` | `/turmas/<pk>/` | as mesmas |
| Cadastrar | `/disciplinas/nova/` (nome) | `/turmas/nova/` (curso e rótulo) | `DISCIPLINA.CRIAR`, `TURMA.CRIAR` |
| Editar | nome | rótulo | `DISCIPLINA.EDITAR`, `TURMA.EDITAR` |
| Excluir | sem ofertas e sem aulas | sem ofertas e sem aulas | `DISCIPLINA.EXCLUIR`, `TURMA.EXCLUIR` |

## Cursos

| Ação | Rota | Permissão |
|---|---|---|
| Listar, buscar pelo nome e filtrar pela etapa | `/cursos/` | `CURSO.VISUALIZAR` |
| Detalhe com as turmas, as ofertas e as aulas de cada uma | `/cursos/<pk>/` | `CURSO.VISUALIZAR` |
| Cadastrar (nome e etapa) | `/cursos/novo/` | `CURSO.CRIAR` |
| Editar nome e etapa, só sem turma com oferta ou aula | `/cursos/<pk>/editar/` | `CURSO.EDITAR` |
| Excluir, só sem turmas | `/cursos/<pk>/excluir/` | `CURSO.EXCLUIR` |

Cursos não têm escopo de docente: quem tem a permissão vê todos. Toda alteração é auditada no módulo `CURSO`. Implementação: `Course` em `schedule/models.py`; testes em `schedule/tests/test_course_views.py` e `test_models.py`.

## Escopo

As listas e os detalhes mostram só o escopo do usuário (`visible_to`):

- Superadmin ativo: todos os registros.
- Demais usuários: as disciplinas e turmas das ofertas em que o docente correspondente ao usuário tem vínculo, atual ou histórico. Sem docente correspondente, o escopo é vazio, inclusive para quem tem o perfil `ADMINISTRADOR`.
- Registro fora do escopo responde 404.
- Regra vigente, coberta por `schedule/tests/test_academic_views.py`. Consequência: disciplina ou turma cadastrada pela tela, ainda sem oferta, só aparece para o superadmin.

A correspondência entre usuário e docente é `Teacher.name` igual a `User.username`, sem diferenciar a caixa (`teacher_of`).

## Cursos, ofertas e vínculos

- Cursos (`Course`) são criados pela importação do ensalamento, com a etapa (`GRADUACAO` ou `ENSINO_MEDIO`) da aba de origem, ou pela tela de Cursos.
- A importação reaproveita o curso pelo nome (`NamedManager.resolve`): as bordas são aparadas, os espaços repetidos são reduzidos e a caixa é ignorada, mas os acentos contam. "Agroindústria" e "AGROINDUSTRIA" são dois cursos, e não há correspondência aproximada. Cadastre o curso com a grafia do título da planilha.
- Curso reaproveitado mantém a etapa cadastrada; se a aba indicar outra, a linha recebe aviso e é processada.
- A disciplina é única pelo nome em todo o sistema, sem separação por curso. A turma é única pelo rótulo dentro do curso.
- A oferta (`ClassOffering`) é criada pela importação, pelo cadastro de aula e pela alteração de recorrência, e nunca é excluída automaticamente.
- O vínculo do docente (`TeachingAssignment`) é sincronizado com as alocações atuais (sem `valid_until`) da mesma tripla semestre, disciplina e turma. Docente que sai das alocações atuais fica com `is_current=False`; volta a `True` se reaparecer. A Agenda oferece só os vínculos atuais.

## Testes

`schedule/tests/test_academic_views.py`, `test_class_offering.py`, `test_course_views.py`.
