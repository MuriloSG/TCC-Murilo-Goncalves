"""Importação do ensalamento pela planilha institucional.

A leitura produz uma linha por valor dos catálogos da aba de validação de dados e uma linha
por atividade lida das células das duas abas de horário (D2 e D4). As linhas dos catálogos
vêm primeiro, porque são elas que criam os espaços e os docentes que as atividades
referenciam, e porque é delas que a execução monta o catálogo do arquivo.

A execução de uma linha só usa os valores gravados dela, e nunca o arquivo: é isso que
permite à confirmação reexecutar tudo depois, sem a planilha, e chegar ao mesmo plano. O
código do semestre vem do campo próprio do envio e está nos valores de todas as linhas
(D16).

Nada é excluído por uma importação, e nenhuma operação de domínio grava auditoria própria:
o registro é o resumo da importação (D13 e D15).
"""

import contextvars
from contextlib import contextmanager

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from audit import catalog
from imports.definitions import (
    Column,
    ImportDefinition,
    RowError,
    RowFilter,
    RowPlan,
    errors_from_validation,
)
from imports.reader import listing
from imports.workbook import WorkbookSource
from schedule.activities import ACTIVITY_COLUMN, Catalog, resolve, split_activities
from schedule.models import (
    SEMESTER_CODE_MESSAGE,
    SEMESTER_CODE_PATTERN,
    Allocation,
    ClassGroup,
    Course,
    Semester,
    Space,
    Subject,
    Teacher,
    TimeSlot,
)
from schedule.sheets import (
    ACTIVITY_KIND,
    CATALOG_SHEET,
    SECONDARY_SHEET,
    SHEET_LAYOUTS,
    SPACE_KIND,
    TEACHER_KIND,
    UNDERGRADUATE_SHEET,
    catalog_entries,
    parse_slot,
    parse_weekday,
    sheet_cells,
    split_header,
    strip_parentheses,
)
from schedule.sheets import text as sheet_text

SEMESTER_COLUMN = 'Semestre'
KIND_COLUMN = 'Tipo'
CELL_COLUMN = 'Célula'
NAME_COLUMN = 'Nome'
DAY_COLUMN = 'Dia'
SLOT_COLUMN = 'Horário'
GROUP_COLUMN = 'Turma'
COURSE_COLUMN = 'Curso'

COURSE_WITHOUT_TITLE = 'curso_sem_titulo'
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_ROWS = 5000

STAGES = {layout.title: layout.stage for layout in SHEET_LAYOUTS}

RUN = contextvars.ContextVar('schedule_import_run')


class RunState:
    """Estado de uma execução: o catálogo do arquivo, o semestre e o que a execução criou.

    Fica num contextvar, e não na definição, porque a definição é um objeto único
    compartilhado pelas telas e não pode guardar dados de uma execução.

    `created` guarda as chaves criadas pelas linhas desta execução. Uma linha que encontra
    um registro criado por uma linha anterior da mesma execução não pode usar a chave como
    alvo do plano: a chave da prévia desaparece no rollback, e a da confirmação é outra, o
    que faria o plano divergir sempre. Nesse caso a linha fica sem alvo, e a decisão
    continua determinística, porque a relação entre as duas linhas é a mesma nas duas
    execuções.

    `duplicates` guarda as células que descrevem a mesma alocação, para que todas recebam o
    erro de duplicidade em vez de a segunda atualizar o que a primeira criou.
    """

    def __init__(self):
        self.catalog = Catalog.build((), ())
        self.semester = None
        self.created = set()
        self.duplicates = {}


def semester_field():
    return forms.CharField(
        label='Semestre',
        max_length=6,
        help_text='Semestre a que os dados da planilha pertencem, no formato 2026/1.',
        validators=[RegexValidator(SEMESTER_CODE_PATTERN, message=SEMESTER_CODE_MESSAGE)],
        error_messages={'required': 'Informe o semestre da planilha.'},
    )


def activity_identity(values, file_catalog):
    """Identidade da alocação que a linha descreve, ou None quando a atividade tem problema.

    É a identidade do model: turma, dia da semana, faixa de horário e disciplina. O semestre
    fica de fora porque é o mesmo em toda a importação.
    """
    activity = resolve(sheet_text(values.get(ACTIVITY_COLUMN)), file_catalog)
    if activity.problems:
        return None
    label, short_name = split_header(values.get(GROUP_COLUMN))
    course_name = sheet_text(values.get(COURSE_COLUMN)) or short_name
    return (
        course_name,
        label,
        parse_weekday(values.get(DAY_COLUMN)),
        sheet_text(values.get(SLOT_COLUMN)),
        activity.subject_name,
    )


def repeated_activities(rows, file_catalog):
    """Células que descrevem a mesma alocação, por identidade, quando há mais de uma."""
    cells = {}
    for row in rows:
        if row.values.get(KIND_COLUMN) != ACTIVITY_KIND:
            continue
        identity = activity_identity(row.values, file_catalog)
        if identity is None:
            continue
        cells.setdefault(identity, []).append(row.values.get(CELL_COLUMN))
    return {identity: found for identity, found in cells.items() if len(found) > 1}


def duplicate_error(cells):
    return RowError(
        ACTIVITY_COLUMN,
        'duplicate',
        f'A mesma turma tem esta disciplina nesta faixa de horário deste dia nas células {listing(cells)}. '
        'Deixe só uma delas na planilha.',
    )


def sheet_of(values):
    """Aba de origem da linha, lida da referência da célula."""
    return sheet_text(values.get(CELL_COLUMN)).partition('!')[0]


def catalog_row(entry):
    return {
        SEMESTER_COLUMN: '',
        KIND_COLUMN: entry['kind'],
        CELL_COLUMN: entry['reference'],
        NAME_COLUMN: entry['value'],
        DAY_COLUMN: '',
        SLOT_COLUMN: '',
        GROUP_COLUMN: '',
        COURSE_COLUMN: '',
        ACTIVITY_COLUMN: '',
    }


def activity_row(cell, content, reference):
    return {
        SEMESTER_COLUMN: '',
        KIND_COLUMN: ACTIVITY_KIND,
        CELL_COLUMN: reference,
        NAME_COLUMN: '',
        DAY_COLUMN: cell['day_text'],
        SLOT_COLUMN: cell['slot_text'],
        GROUP_COLUMN: cell['group'].header_text,
        COURSE_COLUMN: cell['group'].banner_text,
        ACTIVITY_COLUMN: content,
    }


class SpaceAllocationImport(ImportDefinition):
    """Importação do ensalamento de um semestre."""

    kind = 'ENSALAMENTO'
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    columns = (
        Column(SEMESTER_COLUMN),
        Column(KIND_COLUMN),
        Column(CELL_COLUMN),
        Column(NAME_COLUMN, required=False),
        Column(DAY_COLUMN, required=False),
        Column(SLOT_COLUMN, required=False),
        Column(GROUP_COLUMN, required=False),
        Column(COURSE_COLUMN, required=False),
        Column(ACTIVITY_COLUMN, required=False),
    )
    identifier = CELL_COLUMN
    upload_fields = {SEMESTER_COLUMN: semester_field()}
    row_filters = (
        RowFilter('salas', 'Salas', KIND_COLUMN, SPACE_KIND, (CELL_COLUMN, NAME_COLUMN)),
        RowFilter('docentes', 'Docentes', KIND_COLUMN, TEACHER_KIND, (CELL_COLUMN, NAME_COLUMN)),
        RowFilter(
            'atividades',
            'Atividades',
            KIND_COLUMN,
            ACTIVITY_KIND,
            (CELL_COLUMN, DAY_COLUMN, SLOT_COLUMN, GROUP_COLUMN, COURSE_COLUMN, ACTIVITY_COLUMN),
        ),
    )
    sheets = (UNDERGRADUATE_SHEET, SECONDARY_SHEET, CATALOG_SHEET)
    has_template = False
    max_file_size = MAX_FILE_SIZE
    max_rows = MAX_ROWS
    action_labels = {'create': 'Cadastro', 'update': 'Atualização', 'unchanged': 'Sem alteração'}
    field_labels = {
        'name': 'Nome',
        'space': 'Espaço',
        'teachers': 'Docentes',
    }
    warning_labels = {
        COURSE_WITHOUT_TITLE: 'O nome do curso veio do cabeçalho da turma, porque a planilha não traz o título.',
    }
    columns_by_field = {
        'name': NAME_COLUMN,
        'space': ACTIVITY_COLUMN,
        'teachers': ACTIVITY_COLUMN,
        'label': GROUP_COLUMN,
        'code': SEMESTER_COLUMN,
    }

    def source(self):
        return WorkbookSource()

    def read_cells(self, workbook):
        """Linhas da importação: primeiro os catálogos, depois as atividades."""
        for entry in catalog_entries(workbook):
            yield catalog_row(entry)
        for layout in SHEET_LAYOUTS:
            for cell in sheet_cells(workbook[layout.title], layout):
                parts = split_activities(cell['content'])
                for position, content in enumerate(parts, start=1):
                    ordinal = f'#{position}' if len(parts) > 1 else ''
                    yield activity_row(cell, content, cell['reference'] + ordinal)

    @contextmanager
    def execution(self):
        token = RUN.set(RunState())
        try:
            yield
        finally:
            RUN.reset(token)

    def lock(self, rows, executor):
        """Monta o catálogo do arquivo, resolve o semestre e trava as alocações dele.

        O catálogo sai das próprias linhas, e não do arquivo, porque a confirmação não tem o
        arquivo. A trava das alocações do semestre serializa duas importações concorrentes.
        """
        state = RUN.get()
        state.catalog = Catalog.build(
            [self.catalog_name(row.values) for row in rows if row.values.get(KIND_COLUMN) == TEACHER_KIND],
            [self.catalog_name(row.values) for row in rows if row.values.get(KIND_COLUMN) == SPACE_KIND],
        )
        code = next((row.values.get(SEMESTER_COLUMN) for row in rows if row.values.get(SEMESTER_COLUMN)), '')
        state.semester, _ = Semester.objects.resolve(code)
        state.duplicates = repeated_activities(rows, state.catalog)
        list(
            Allocation.objects.filter(semester=state.semester)
            .order_by('pk')
            .select_for_update()
            .values_list('pk', flat=True)
        )

    def catalog_name(self, values):
        """Nome de um valor de catálogo, com os parênteses da sala retirados."""
        name = sheet_text(values.get(NAME_COLUMN))
        if values.get(KIND_COLUMN) == SPACE_KIND:
            return strip_parentheses(name)
        return name

    def execute_row(self, values, executor):
        row_kind = values.get(KIND_COLUMN)
        if row_kind == SPACE_KIND:
            return self.execute_catalog(Space, self.catalog_name(values))
        if row_kind == TEACHER_KIND:
            return self.execute_catalog(Teacher, self.catalog_name(values))
        return self.execute_activity(values)

    def execute_catalog(self, model, name):
        """Cria o espaço ou o docente da lista, ou o deixa como está."""
        state = RUN.get()
        try:
            record, created = model.objects.resolve(name)
        except ValidationError as error:
            return RowPlan(errors=errors_from_validation(error, self.columns_by_field))
        key = (model.__name__, record.pk)
        if created:
            state.created.add(key)
            return RowPlan(action='create', changes={'name': [None, record.name]}, created=record.pk)
        target = None if key in state.created else record.pk
        return RowPlan(action='unchanged', target=target)

    def execute_activity(self, values):
        """Cria ou atualiza a alocação da atividade da linha."""
        state = RUN.get()
        plan = RowPlan()
        weekday = parse_weekday(values.get(DAY_COLUMN))
        slot_times = parse_slot(values.get(SLOT_COLUMN))
        label, short_name = split_header(values.get(GROUP_COLUMN))
        banner = sheet_text(values.get(COURSE_COLUMN))
        course_name = banner or short_name
        if not banner:
            plan.warnings.append(COURSE_WITHOUT_TITLE)
        activity = resolve(sheet_text(values.get(ACTIVITY_COLUMN)), state.catalog)
        plan.errors = [RowError(ACTIVITY_COLUMN, code, message) for code, message in activity.problems]
        if plan.errors:
            return plan
        identity = activity_identity(values, state.catalog)
        if identity in state.duplicates:
            plan.errors.append(duplicate_error(state.duplicates[identity]))
            return plan
        try:
            course, _ = Course.objects.resolve(course_name, stage=STAGES[sheet_of(values)])
            group, _ = ClassGroup.objects.resolve(course, label)
            subject, _ = Subject.objects.resolve(activity.subject_name)
            slot, _ = TimeSlot.objects.resolve(state.semester, *slot_times)
            space = Space.objects.get(name__iexact=activity.space_name) if activity.space_name else None
            teachers = [Teacher.objects.get(name__iexact=name) for name in activity.teacher_names]
            allocation, action, changes = Allocation.objects.apply(
                semester=state.semester,
                class_group=group,
                subject=subject,
                weekday=weekday,
                time_slot=slot,
                space=space,
                teachers=teachers,
            )
        except ValidationError as error:
            plan.errors = errors_from_validation(error, self.columns_by_field)
            return plan
        plan.action = action
        plan.changes = changes
        key = (Allocation.__name__, allocation.pk)
        if action == 'create':
            state.created.add(key)
            plan.created = allocation.pk
        else:
            plan.target = None if key in state.created else allocation.pk
        return plan

    def audit_metadata(self, rows):
        """Semestre da importação, para o resumo auditado (D15)."""
        codes = {values.get(SEMESTER_COLUMN) for values in (row.values for row in rows)}
        codes.discard('')
        codes.discard(None)
        return {'semestre': codes.pop() if len(codes) == 1 else None}


def concluded_message(summary):
    """Mensagem da importação de ensalamento concluída, com os totais."""
    created, updated, unchanged = summary['create'], summary['update'], summary['unchanged']
    parts = []
    if created:
        parts.append(f'{created} registro{"s" if created > 1 else ""} cadastrado{"s" if created > 1 else ""}')
    if updated:
        parts.append(f'{updated} atualizado{"s" if updated > 1 else ""}')
    if unchanged:
        parts.append(f'{unchanged} sem alteração')
    if not parts:
        return 'Importação concluída. Nenhum registro foi cadastrado ou alterado.'
    return f'Importação do ensalamento concluída. {", ".join(parts)}.'
