"""Leitura da disciplina, dos docentes e da sala do texto de uma célula de atividade.

O texto da célula não tem separador confiável entre as três informações: o nome da
disciplina pode ter parênteses próprios e a sala pode faltar. Por isso a leitura acontece
do fim para o começo, comparando o que está entre parênteses com os catálogos da aba de
validação de dados (D3 da Change importar-ensalamento-da-planilha).

A correspondência é exata, ignorando somente a diferença entre maiúsculas e minúsculas e a
normalização de espaços. Os acentos são preservados, e não há similaridade, prefixo nem
correspondência parcial em nenhum ponto. Um nome fora do catálogo é erro da linha, e nada
é criado a partir do texto da célula.
"""

import re
from dataclasses import dataclass, field

from schedule.utils import normalize_name

PARENTHESES = re.compile(r'\(([^()]*)\)')
TEACHER_SEPARATORS = re.compile(r'\s*/\s*|\s*,\s*|\s+e\s+')
SUBJECT_BORDERS = ' -:;,/'
ACTIVITY_COLUMN = 'Atividade'

UNKNOWN_SPACE = 'sala_desconhecida'
UNKNOWN_TEACHER = 'docente_desconhecido'
WITHOUT_SUBJECT = 'sem_disciplina'
WITHOUT_PARENTHESES = 'sem_parenteses'


@dataclass(frozen=True)
class Catalog:
    """Catálogos de docentes e de salas, para a correspondência exata sem diferenciar a caixa."""

    teachers: dict
    spaces: dict

    @classmethod
    def build(cls, teacher_names, space_names):
        return cls(
            teachers={name.casefold(): name for name in teacher_names},
            spaces={name.casefold(): name for name in space_names},
        )

    def space(self, value):
        return self.spaces.get(value.casefold())

    def teacher(self, value):
        return self.teachers.get(value.casefold())


@dataclass
class Activity:
    """Uma atividade lida de uma célula: disciplina, docentes, sala e os problemas dela."""

    subject_name: str | None = None
    teacher_names: list = field(default_factory=list)
    space_name: str | None = None
    problems: list = field(default_factory=list)


def normalized_text(content):
    """Texto da célula sem quebras de linha e sem espaços repetidos."""
    return ' '.join(str(content or '').replace('\n', ' ').split())


def split_activities(content):
    """Separa a célula pelas barras que estiverem fora de parênteses.

    A separação só vale quando cada trecho tem pelo menos um nome entre parênteses: sem
    isso, a barra faz parte do texto e a célula é uma atividade só. Por isso uma célula
    como `UCE 2 (Eduardo Garrido/ Thaís/ Antônio )(HV 3)` não é separada (D2, D3).
    """
    parts, depth, current = [], 0, ''
    for char in content:
        if char == '(':
            depth += 1
        elif char == ')':
            depth = max(depth - 1, 0)
        if char == '/' and depth == 0:
            parts.append(current)
            current = ''
            continue
        current += char
    parts.append(current)
    parts = [normalized_text(part) for part in parts]
    parts = [part for part in parts if part]
    if len(parts) > 1 and all(PARENTHESES.search(part) for part in parts):
        return parts
    return [normalized_text(content)]


def teacher_names_of(group):
    """Nomes de docente de um trecho entre parênteses, separados por barra, vírgula ou "e"."""
    names = (normalize_name(name) for name in TEACHER_SEPARATORS.split(group))
    return [name for name in names if name is not None]


def subject_name_of(text, cut):
    """Nome da disciplina: o texto antes do trecho entre parênteses do docente ou da sala.

    Os parênteses internos do nome da disciplina são preservados, e só os separadores das
    bordas são retirados.
    """
    return normalize_name(text[:cut].strip(SUBJECT_BORDERS))


def resolve(text, catalog):
    """Lê uma atividade já separada, devolvendo o que foi reconhecido e os problemas."""
    activity = Activity()
    groups = list(PARENTHESES.finditer(text))
    if not groups:
        activity.problems.append((WITHOUT_PARENTHESES, 'A atividade não informa o docente nem a sala entre parênteses.'))
        activity.subject_name = normalize_name(text)
        return activity
    last = groups[-1]
    previous = groups[-2] if len(groups) > 1 else None
    last_value = normalize_name(last.group(1)) or ''
    space_name = catalog.space(last_value)
    if space_name is not None:
        activity.space_name = space_name
        teacher_group = previous
    elif previous is not None and all(catalog.teacher(name) for name in teacher_names_of(previous.group(1))):
        activity.problems.append((
            UNKNOWN_SPACE,
            f'A sala "{last_value}" não está na lista de salas da aba "Validação de Dados". '
            'Acrescente a sala à planilha.',
        ))
        teacher_group = previous
    else:
        teacher_group = last
    if teacher_group is None:
        activity.subject_name = subject_name_of(text, last.start())
    else:
        activity.subject_name = subject_name_of(text, teacher_group.start())
        unknown = []
        for name in teacher_names_of(teacher_group.group(1)):
            known = catalog.teacher(name)
            if known is None:
                unknown.append(name)
            else:
                activity.teacher_names.append(known)
        if unknown:
            activity.problems.append((UNKNOWN_TEACHER, unknown_teacher_message(unknown)))
    if activity.subject_name is None:
        activity.problems.append((WITHOUT_SUBJECT, 'A atividade não tem disciplina antes do nome entre parênteses.'))
    return activity


def unknown_teacher_message(names):
    listed = ', '.join(f'"{name}"' for name in names)
    if len(names) == 1:
        return (
            f'O docente {listed} não está na lista de docentes da aba "Validação de Dados". '
            'Acrescente o docente à planilha.'
        )
    return (
        f'Os docentes {listed} não estão na lista de docentes da aba "Validação de Dados". '
        'Acrescente os docentes à planilha.'
    )


def read(content, catalog):
    """Atividades de uma célula, na ordem em que aparecem no texto."""
    return [resolve(text, catalog) for text in split_activities(content)]
