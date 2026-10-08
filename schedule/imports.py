"""Importação do ensalamento pela planilha institucional.

A leitura produz uma linha por valor dos catálogos da aba de validação de dados e uma linha
por atividade lida das células das duas abas de horário (D2 e D4). As linhas dos catálogos
vêm primeiro, porque são elas que criam os espaços e os docentes que as atividades
referenciam, e porque é delas que a execução monta o catálogo do arquivo.

A execução de uma linha só usa os valores gravados dela, e nunca o arquivo: é isso que
permite à confirmação reexecutar tudo depois, sem a planilha, e chegar ao mesmo plano. O
código do semestre vem do campo próprio do envio e está nos valores de todas as linhas
(D16). O início e o fim do semestre também são campos próprios do envio, gravados nas linhas,
e o período é aplicado ao semestre na execução, em `lock()` (D3 da Change
visualizar-ocupacao-por-semana-e-mes).

Nada é excluído por uma importação, e nenhuma operação de domínio grava auditoria própria,
salvo as do cadastro de espaços: o registro é o resumo da importação (D13 e D15). Os espaços
seguem a classificação de `schedule.spaces`, aplicada ao cadastro em `lock()`, antes das
linhas; toda sala da lista entra na classificação, com ou sem aula, e o nome que precisa de
decisão vira pendência (D5 e D8 da Change manipulacao-dos-espacos e Change
importar-salas-sem-aula).

A aba opcional `usuários - sistema`, quando existe, produz uma linha por usuário, lida antes
dos catálogos: a execução cadastra os usuários que ainda não existem, pelas operações da
importação de usuários, e não altera os existentes. Sem a aba não há linha de usuário, e a
execução vai direto aos catálogos. Os usuários ficam na mesma transação e no mesmo savepoint
do ensalamento, para que a prévia os desfaça e a confirmação só os grave junto com ele (D1,
D2 e D6 da Change importar-usuarios-com-o-ensalamento).
"""

import contextvars
from contextlib import contextmanager
from datetime import date

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.validators import RegexValidator
from django.utils import formats

from accounts.imports import UserImport
from accounts.models import User, normalize_username
from audit import catalog
from imports.definitions import (
    Column,
    ImportDefinition,
    RowError,
    RowFilter,
    RowPlan,
    errors_from_validation,
)
from audit.models import AuditLog
from imports.models import Import, ImportRow
from imports.reader import listing
from imports.workbook import WorkbookSource
from schedule.activities import ACTIVITY_COLUMN, Catalog, resolve, split_activities
from schedule.models import (
    SEMESTER_CODE_MESSAGE,
    SEMESTER_CODE_PATTERN,
    Allocation,
    ClassGroup,
    ClassOffering,
    Course,
    Semester,
    SPACE_PERMISSION_MESSAGE,
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
    USER_COLUMNS,
    USER_EMAIL_COLUMN,
    USER_KIND,
    USER_ROLE_COLUMN,
    USER_USERNAME_COLUMN,
    USERS_SHEET,
    catalog_entries,
    parse_slot,
    parse_weekday,
    sheet_cells,
    split_header,
    strip_parentheses,
    user_entries,
)
from schedule.sheets import text as sheet_text
from schedule.spaces import ASSOCIATE, CREATE, PENDING, classify, classify_import, key_of
from schedule.spaces import apply as apply_spaces
from ui.forms import DateInput

SEMESTER_COLUMN = 'Semestre'
START_COLUMN = 'Início'
END_COLUMN = 'Fim'
KIND_COLUMN = 'Tipo'
CELL_COLUMN = 'Célula'
NAME_COLUMN = 'Nome'
DAY_COLUMN = 'Dia'
SLOT_COLUMN = 'Horário'
GROUP_COLUMN = 'Turma'
COURSE_COLUMN = 'Curso'

COURSE_WITHOUT_TITLE = 'curso_sem_titulo'
ASSOCIATED_TO_NEW = 'outro_nome_de_espaco_novo'
RECURRENCE_CHANGED = 'recorrencia_alterada'
SPACE_PENDING = 'espaco_a_decidir'
USER_WITH_OTHER_DATA = 'usuario_com_outros_dados'
INACTIVE_USER = 'usuario_inativo'
REQUIRED_USER_COLUMNS = (USER_EMAIL_COLUMN, NAME_COLUMN, USER_ROLE_COLUMN)
USERS = UserImport()
ACTIVE_LABELS = {True: 'ATIVO', False: 'INATIVO'}
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_ROWS = 5000

EMPTY_USER_VALUES = {USER_EMAIL_COLUMN: '', USER_ROLE_COLUMN: '', USER_USERNAME_COLUMN: ''}

STAGES = {layout.title: layout.stage for layout in SHEET_LAYOUTS}

RUN = contextvars.ContextVar('schedule_import_run')
PERIOD_CHANGE = contextvars.ContextVar('schedule_import_period_change', default=None)


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

    `resolution` é a classificação dos espaços, `applied` o que ela aplicou ao cadastro e
    `reported` os nomes da lista de salas cuja linha já recebeu a ação.

    `user_duplicates` guarda, pela célula de origem, os erros de e-mail ou de nome de usuário
    repetido na aba de usuários (D8 da Change importar-usuarios-com-o-ensalamento).

    `records` guarda os cursos, turmas, disciplinas, faixas e docentes já resolvidos, pela
    grafia exata da busca, para que a mesma grafia não volte ao banco na mesma execução;
    `users` guarda os usuários da aba lidos na trava, pelo e-mail gravado; `allocations`
    guarda as alocações do semestre lidas na trava, pela identidade; e
    `offerings` os pares de disciplina e turma das linhas mantidas, sincronizados em
    `finish()`. O que uma linha acrescenta a eles fica em `row` e só passa a valer quando a
    linha é mantida: o registro criado por uma linha desfeita deixa de existir no banco
    (D1, D2, D3 e D5 da Change otimizar-consultas-do-sistema).
    """

    def __init__(self, importation=None):
        self.importation = importation
        self.catalog = Catalog.build((), ())
        self.semester = None
        self.created = set()
        self.duplicates = {}
        self.resolution = None
        self.applied = None
        self.reported = set()
        self.user_duplicates = {}
        self.records = {}
        self.users = {}
        self.allocations = {}
        self.offerings = set()
        self.row = RowMemory()

    def remembered(self, key, find):
        """Registro da grafia, buscado no banco só na primeira vez; `find` devolve o registro e se o criou."""
        if key in self.records:
            return self.records[key]
        if key in self.row.records:
            return self.row.records[key]
        record, created = find()
        (self.row.records if created else self.records)[key] = record
        return record

    def versions(self, identity):
        return self.allocations.get(identity, []) + self.row.allocations.get(identity, [])

    def keep_row(self):
        """Incorpora o que a linha mantida acrescentou."""
        self.records |= self.row.records
        for identity, items in self.row.allocations.items():
            self.allocations.setdefault(identity, []).extend(items)
        self.offerings |= self.row.offerings
        self.row = RowMemory()


class RowMemory:
    """O que a linha em execução acrescentou à memória da execução, ainda provisório."""

    def __init__(self):
        self.records = {}
        self.allocations = {}
        self.offerings = set()


def identity_of(allocation):
    return (allocation.class_group_id, allocation.subject_id, allocation.weekday, allocation.time_slot_id)


def version_order(allocation):
    """Ordem de `valid_from, pk` do banco, com a vigência vazia por último."""
    return (allocation.valid_from is None, allocation.valid_from or date.min, allocation.pk)


def semester_field():
    return forms.CharField(
        label='Semestre',
        max_length=6,
        help_text='Semestre a que os dados da planilha pertencem, no formato 2026/1.',
        validators=[RegexValidator(SEMESTER_CODE_PATTERN, message=SEMESTER_CODE_MESSAGE)],
        widget=forms.TextInput(
            attrs={'placeholder': '2026/1', 'inputmode': 'numeric', 'autocomplete': 'off', 'data-mask': 'semester'},
        ),
        error_messages={'required': 'Informe o semestre da planilha.'},
    )


def period_field(label, help_text):
    """Data do período no envio. A obrigatoriedade depende do semestre e é conferida em
    `clean_upload`; por isso o campo é `conditional`, e o rótulo não diz "(opcional)".
    """
    field = forms.DateField(
        label=label,
        required=False,
        help_text=help_text,
        widget=DateInput(),
    )
    field.conditional = True
    return field


def period_of(values):
    """Início e fim gravados nos valores da linha, ou None quando ficaram em branco."""
    return tuple(date.fromisoformat(values[column]) if values.get(column) else None for column in (START_COLUMN, END_COLUMN))


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
        **EMPTY_USER_VALUES,
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
        **EMPTY_USER_VALUES,
    }


def user_row(entry):
    """Linha de um usuário da aba opcional, com as colunas do ensalamento vazias."""
    return {
        SEMESTER_COLUMN: '',
        KIND_COLUMN: USER_KIND,
        CELL_COLUMN: entry['reference'],
        DAY_COLUMN: '',
        SLOT_COLUMN: '',
        GROUP_COLUMN: '',
        COURSE_COLUMN: '',
        ACTIVITY_COLUMN: '',
    } | {label: entry['values'].get(label, '') for label in USER_COLUMNS}


def repeated_users(rows):
    """Erros de duplicidade da aba de usuários, pela célula de origem (D8).

    O e-mail é comparado normalizado e o nome de usuário sem diferenciar a caixa. Todas as
    linhas envolvidas recebem o erro, calculado das linhas, e não do arquivo, para que a
    confirmação chegue ao mesmo resultado da prévia.
    """
    user_rows = [row for row in rows if row.values.get(KIND_COLUMN) == USER_KIND]
    keys = (
        (USER_EMAIL_COLUMN, lambda value: User.objects.normalize_email(value),
         'O e-mail aparece também nas células {cells}. Deixe só uma linha por usuário.'),
        (USER_USERNAME_COLUMN, lambda value: (normalize_username(value) or '').casefold(),
         'O nome de usuário aparece também nas células {cells}. Use um nome de usuário por usuário.'),
    )
    errors = {}
    for column, normalize, message in keys:
        groups = {}
        for row in user_rows:
            key = normalize(row.values.get(column, ''))
            if key:
                groups.setdefault(key, []).append(row)
        for repeated in groups.values():
            if len(repeated) < 2:
                continue
            for row in repeated:
                others = [other.values.get(CELL_COLUMN) for other in repeated if other is not row]
                errors.setdefault(row.values.get(CELL_COLUMN), []).append(
                    RowError(column, 'duplicate', message.format(cells=listing(others)))
                )
    return errors


class SpaceAllocationImport(ImportDefinition):
    """Importação do ensalamento de um semestre."""

    kind = 'ENSALAMENTO'
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    columns = (
        Column(SEMESTER_COLUMN),
        Column(START_COLUMN, required=False),
        Column(END_COLUMN, required=False),
        Column(KIND_COLUMN),
        Column(CELL_COLUMN),
        Column(NAME_COLUMN, required=False),
        Column(DAY_COLUMN, required=False),
        Column(SLOT_COLUMN, required=False),
        Column(GROUP_COLUMN, required=False),
        Column(COURSE_COLUMN, required=False),
        Column(ACTIVITY_COLUMN, required=False),
        Column(USER_EMAIL_COLUMN, required=False),
        Column(USER_ROLE_COLUMN, required=False),
        Column(USER_USERNAME_COLUMN, required=False),
    )
    identifier = CELL_COLUMN
    upload_fields = {
        SEMESTER_COLUMN: semester_field(),
        START_COLUMN: period_field('Início do semestre', 'Primeiro dia letivo. Obrigatório na primeira importação do semestre; num semestre que já tem período, em branco mantém o atual.'),
        END_COLUMN: period_field('Fim do semestre', 'Último dia letivo, informado junto com o início.'),
    }
    row_filters = (
        RowFilter(
            'usuarios',
            'Usuários',
            KIND_COLUMN,
            USER_KIND,
            (CELL_COLUMN, USER_EMAIL_COLUMN, NAME_COLUMN, USER_ROLE_COLUMN, USER_USERNAME_COLUMN),
        ),
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
    optional_sheets = (USERS_SHEET,)
    has_template = False
    max_file_size = MAX_FILE_SIZE
    max_rows = MAX_ROWS
    action_labels = {'create': 'Cadastro', 'update': 'Atualização', 'unchanged': 'Sem alteração'}
    field_labels = {
        'name': 'Nome',
        'space': 'Espaço',
        'teachers': 'Docentes',
        'outros_nomes': 'Outros nomes',
        'situacao': 'Situação',
        'novo_espaco': 'Espaço cadastrado',
        'email': 'E-mail',
        'role': 'Perfil',
        'username': 'Nome de usuário',
    }
    warning_labels = {
        COURSE_WITHOUT_TITLE: 'O nome do curso veio do cabeçalho da turma, porque a planilha não traz o título.',
        ASSOCIATED_TO_NEW: 'O nome será guardado como outro nome de um espaço cadastrado por esta importação.',
        RECURRENCE_CHANGED: 'Esta aula foi definida no sistema e não foi atualizada pela planilha.',
        USER_WITH_OTHER_DATA: (
            'Usuário já cadastrado com outros dados. A importação do ensalamento não altera o cadastro. '
            'Use a tela de usuários ou a importação de usuários.'
        ),
        INACTIVE_USER: 'Usuário inativo. A importação do ensalamento não o reativa.',
    }
    pending_labels = {
        SPACE_PENDING: 'O espaço {key} precisa de decisão no quadro de espaços desta importação.',
    }
    columns_by_field = {
        'name': NAME_COLUMN,
        'space': ACTIVITY_COLUMN,
        'teachers': ACTIVITY_COLUMN,
        'label': GROUP_COLUMN,
        'code': SEMESTER_COLUMN,
        'start_date': START_COLUMN,
        'end_date': END_COLUMN,
        'email': USER_EMAIL_COLUMN,
        'role': USER_ROLE_COLUMN,
        'username': USER_USERNAME_COLUMN,
    }

    def source(self):
        return WorkbookSource()

    def clean_upload(self, values):
        """Datas do período conferidas pelo model, antes de ler o arquivo (D3).

        As recusas voltam pelo rótulo da coluna lógica, para que o formulário as ponha no
        campo certo.
        """
        try:
            Semester.objects.check_period(values.get(SEMESTER_COLUMN), values.get(START_COLUMN), values.get(END_COLUMN))
        except ValidationError as error:
            fields = {'start_date': START_COLUMN, 'end_date': END_COLUMN}
            raise ValidationError({fields.get(name, NON_FIELD_ERRORS): errors for name, errors in error.error_dict.items()}) from error

    def upload_display(self, label, value):
        """Datas do período em dd/mm/aaaa; em branco, o período atual foi mantido."""
        if label in (START_COLUMN, END_COLUMN):
            return formats.date_format(date.fromisoformat(value), 'SHORT_DATE_FORMAT') if value else 'Mantido'
        return value

    def read_cells(self, workbook):
        """Linhas da importação: os usuários da aba opcional, os catálogos e as atividades (D1)."""
        for entry in user_entries(workbook):
            yield user_row(entry)
        for entry in catalog_entries(workbook):
            yield catalog_row(entry)
        for layout in SHEET_LAYOUTS:
            for cell in sheet_cells(workbook[layout.title], layout):
                parts = split_activities(cell['content'])
                for position, content in enumerate(parts, start=1):
                    ordinal = f'#{position}' if len(parts) > 1 else ''
                    yield activity_row(cell, content, cell['reference'] + ordinal)

    @contextmanager
    def execution(self, importation=None):
        token = RUN.set(RunState(importation))
        try:
            yield
        finally:
            RUN.reset(token)

    def lock(self, rows, executor):
        """Classifica e aplica os espaços, resolve o semestre e trava as alocações dele.

        A classificação sai das próprias linhas, e não do arquivo, porque a confirmação não tem
        o arquivo, e o catálogo da leitura das células é o dela: a lista da planilha somada
        aos nomes do cadastro. As alterações do cadastro acontecem aqui, antes das linhas,
        pelas operações de `Space`. A trava das alocações do semestre serializa duas
        importações concorrentes.
        """
        state = RUN.get()
        state.resolution = classify([row.values for row in rows], state.importation)
        state.catalog = state.resolution.catalog
        state.applied = apply_spaces(state.resolution, state.importation)
        state.created |= {(Space.__name__, pk) for pk in state.applied.created}
        code = next((row.values.get(SEMESTER_COLUMN) for row in rows if row.values.get(SEMESTER_COLUMN)), '')
        state.semester, _ = Semester.objects.resolve(code)
        self.apply_period(state.semester, rows)
        state.duplicates = repeated_activities(rows, state.catalog)
        state.user_duplicates = repeated_users(rows)
        self.lock_users(rows)
        self.lock_allocations(state)

    def lock_allocations(self, state):
        """Trava as alocações do semestre e as guarda pela identidade, com o espaço e os docentes.

        A trava continua só nas linhas de alocação: o espaço e os docentes vêm de consultas
        próprias do `prefetch_related`, sem `FOR UPDATE` (D3).
        """
        allocations = (
            Allocation.objects.filter(semester=state.semester)
            .order_by('pk')
            .select_for_update()
            .prefetch_related('space', 'teachers')
        )
        for allocation in allocations:
            allocation.semester = state.semester
            state.allocations.setdefault(identity_of(allocation), []).append(allocation)
        for versions in state.allocations.values():
            versions.sort(key=version_order)

    def lock_users(self, rows):
        """Trava os usuários com os e-mails da aba, e nada consulta quando ela não existe (D12).

        Os usuários travados ficam na execução pelo e-mail gravado, com o perfil, e a trava
        continua só nas linhas de usuário (A8 da Change otimizar-consultas-do-sistema).
        """
        emails = [
            User.objects.normalize_email(row.values.get(USER_EMAIL_COLUMN))
            for row in rows
            if row.values.get(KIND_COLUMN) == USER_KIND
        ]
        if not emails:
            return
        users = User.objects.filter(email__in=emails).order_by('pk').select_for_update().prefetch_related('roles')
        RUN.get().users = {user.email: user for user in users}

    def apply_period(self, semester, rows):
        """Aplica ao semestre o período gravado nas linhas, e guarda a mudança para a auditoria.

        Roda dentro da transação da execução: a prévia desfaz, a confirmação grava com as
        alocações. Em branco, o período atual é preservado. A mudança fica num contextvar
        próprio, e não no estado da execução, porque o resumo auditado é montado depois
        que a execução termina.
        """
        start, end = period_of(rows[0].values) if rows else (None, None)
        previous = (semester.start_date, semester.end_date)
        changed = start is not None and semester.define_period(start, end)
        replaced = changed and previous[0] is not None
        PERIOD_CHANGE.set((semester.code, start, end, previous) if replaced else None)

    def catalog_name(self, values):
        """Nome de um valor de catálogo, com os parênteses da sala retirados."""
        name = sheet_text(values.get(NAME_COLUMN))
        if values.get(KIND_COLUMN) == SPACE_KIND:
            return strip_parentheses(name)
        return name

    def execute_row(self, values, executor):
        """Executa a linha e incorpora à memória da execução o que ela acrescentou, se for mantida.

        O motor desfaz a linha com erro ou pendência; a linha que lança exceção também é desfeita,
        e o que ela acrescentou é descartado quando a próxima começa.
        """
        state = RUN.get()
        state.row = RowMemory()
        plan = self.plan_row(values, executor)
        if not plan.errors and not plan.pending:
            state.keep_row()
        return plan

    def plan_row(self, values, executor):
        row_kind = values.get(KIND_COLUMN)
        if row_kind == USER_KIND:
            return self.execute_user(values, executor)
        if row_kind == SPACE_KIND:
            return self.execute_space(self.catalog_name(values))
        if row_kind == TEACHER_KIND:
            return self.execute_catalog(Teacher, self.catalog_name(values))
        return self.execute_activity(values)

    def execute_user(self, values, executor):
        """Cadastra o usuário que ainda não existe, e deixa o existente como está (D3, D6 e D7).

        A validação e o cadastro são os da importação de usuários. O usuário é reconhecido pelo
        e-mail. A célula obrigatória é conferida aqui porque a fonte em grade não a confere.
        """
        errors = [
            RowError(column, 'required', f'Preencha a coluna {column}.')
            for column in REQUIRED_USER_COLUMNS
            if not sheet_text(values.get(column))
        ]
        errors += RUN.get().user_duplicates.get(values.get(CELL_COLUMN), [])
        if errors:
            return RowPlan(errors=errors)
        cleaned, errors = USERS.clean_values(values)
        user = RUN.get().users.get(cleaned['email']) or User.objects.filter(email__iexact=cleaned['email']).first()
        if user is None:
            return USERS.create(cleaned, errors, executor)
        if errors:
            return RowPlan(target=user.pk, errors=errors)
        return RowPlan(action='unchanged', target=user.pk, warnings=self.user_warnings(user, cleaned))

    def user_warnings(self, user, cleaned):
        """Avisos do usuário existente: outros dados no cadastro e situação inativa (D7).

        O perfil é lido dos perfis carregados com o usuário, sem nova consulta: o usuário tem um
        perfil só, pela restrição `user_role_one_per_user`.
        """
        warnings = []
        role = next(iter(user.roles.all()), None)
        differs = (
            cleaned.get('name') != user.name
            or cleaned['username'] != user.username
            or cleaned['role'] != role
        )
        if differs:
            warnings.append(USER_WITH_OTHER_DATA)
        if not user.is_active:
            warnings.append(INACTIVE_USER)
        return warnings

    def execute_space(self, name):
        """Plano da linha da lista de salas, pelo que a classificação decidiu para o nome.

        O nome fora da classificação identifica um espaço inativo sem aula e fica sem ação.
        """
        state = RUN.get()
        key = key_of(name)
        entry = state.resolution.found.get(key)
        if entry is None:
            return RowPlan()
        if entry.outcome == PENDING:
            return RowPlan(pending=[{'code': SPACE_PENDING, 'key': entry.name}])
        space = state.applied.spaces[key]
        if key in state.reported:
            return RowPlan(action='unchanged', target=None if space.pk in state.applied.created else space.pk)
        state.reported.add(key)
        if entry.outcome == CREATE:
            changes = {'name': [None, space.name]}
            if space.other_names:
                changes['outros_nomes'] = [None, space.other_names]
            return RowPlan(action='create', changes=changes, created=space.pk)
        if entry.outcome == ASSOCIATE and entry.target_key is not None:
            return RowPlan(warnings=[ASSOCIATED_TO_NEW])
        changes = self.space_changes(space, state.applied)
        if changes:
            return RowPlan(action='update', target=space.pk, changes=changes)
        return RowPlan(action='unchanged', target=space.pk)

    def space_changes(self, space, applied):
        """Outros nomes e situação do espaço existente antes e depois desta execução.

        O espaço que a execução não alterou não tem mudança, e não é lido de novo (A7 da
        Change otimizar-consultas-do-sistema).
        """
        if space.pk not in applied.altered:
            return {}
        previous_names, was_active = applied.previous_names.get(space.pk, (space.other_names, space.is_active))
        space.refresh_from_db()
        changes = {}
        if previous_names != space.other_names:
            changes['outros_nomes'] = [previous_names, space.other_names]
        if was_active != space.is_active:
            changes['situacao'] = [ACTIVE_LABELS[was_active], ACTIVE_LABELS[space.is_active]]
        return changes

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
        space_key = key_of(activity.space_name or activity.cell_space_name or '')
        entry = state.resolution.found.get(space_key)
        if entry is not None and entry.outcome == PENDING:
            plan.pending = [{'code': SPACE_PENDING, 'key': entry.name}]
            return plan
        identity = activity_identity(values, state.catalog)
        if identity in state.duplicates:
            plan.errors.append(duplicate_error(state.duplicates[identity]))
            return plan
        try:
            course = state.remembered(
                (Course, course_name), lambda: Course.objects.resolve(course_name, stage=STAGES[sheet_of(values)]),
            )
            group = state.remembered((ClassGroup, course.pk, label), lambda: ClassGroup.objects.resolve(course, label))
            subject = state.remembered((Subject, activity.subject_name), lambda: Subject.objects.resolve(activity.subject_name))
            slot = state.remembered((TimeSlot, slot_times), lambda: TimeSlot.objects.resolve(state.semester, *slot_times))
            space = state.applied.spaces.get(space_key) if entry is not None else None
            teachers = [
                state.remembered((Teacher, name), lambda name=name: (Teacher.objects.get(name__iexact=name), False))
                for name in activity.teacher_names
            ]
            identity = (group.pk, subject.pk, weekday, slot.pk)
            allocation, action, changes = Allocation.objects.apply(
                semester=state.semester,
                class_group=group,
                subject=subject,
                weekday=weekday,
                time_slot=slot,
                space=space,
                teachers=teachers,
                versions=state.versions(identity),
            )
        except ValidationError as error:
            plan.errors = errors_from_validation(error, self.columns_by_field)
            return plan
        if action == 'create':
            state.row.allocations[identity] = [allocation]
        state.row.offerings.add((subject.pk, group.pk))
        plan.action = action
        plan.changes = changes | self.new_space_change(entry, space)
        if allocation.is_versioned:
            plan.warnings.append(RECURRENCE_CHANGED)
        key = (Allocation.__name__, allocation.pk)
        if action == 'create':
            state.created.add(key)
            plan.created = allocation.pk
        else:
            plan.target = None if key in state.created else allocation.pk
        return plan

    def finish(self, executor):
        """Sincroniza uma vez as ofertas e os vínculos de docente das linhas mantidas (D5)."""
        state = RUN.get()
        ClassOffering.objects.record_many(state.semester, state.offerings)

    def check_confirmation(self, importation, executor):
        """Permissões de espaço de quem confirma, pelo que a confirmação alterará no cadastro (D11)."""
        required = classify_import(importation).required_permissions()
        if any(not executor.has_perm(code) for code in required):
            raise ValidationError(SPACE_PERMISSION_MESSAGE, code='space_permission')

    def new_space_change(self, entry, space):
        """Cadastro do espaço citado só nas células, no plano da primeira aula que o usa.

        O nome da lista tem a linha de sala para mostrar o cadastro; o nome só das células não
        tem, e sem esta mudança o plano não mudaria quando o espaço passasse a existir por
        outro caminho entre a prévia e a confirmação.
        """
        state = RUN.get()
        if entry is None or entry.from_list or space is None or space.pk not in state.applied.created:
            return {}
        if entry.key in state.reported:
            return {}
        state.reported.add(entry.key)
        return {'novo_espaco': [None, space.name]}

    def audit_metadata(self, rows):
        """Semestre e período da importação, para o resumo auditado (D15 e D3).

        O período anterior entra quando a execução que acabou de rodar o substituiu. A
        mudança é conferida pelo semestre e pelas datas, e consumida na leitura, para que
        um valor de outra execução da mesma thread não apareça no descarte ou na exclusão.
        """
        codes = {values.get(SEMESTER_COLUMN) for values in (row.values for row in rows)}
        codes.discard('')
        codes.discard(None)
        first = rows[0].values if rows else {}
        metadata = {
            'semestre': codes.pop() if len(codes) == 1 else None,
            'inicio': first.get(START_COLUMN) or None,
            'fim': first.get(END_COLUMN) or None,
        }
        change = PERIOD_CHANGE.get()
        PERIOD_CHANGE.set(None)
        if change is not None and change[:3] == (metadata['semestre'], *period_of(first)):
            previous = change[3]
            metadata |= {'inicio_anterior': previous[0].isoformat(), 'fim_anterior': previous[1].isoformat()}
        parent = getattr(rows[0], 'parent_id', None) if rows else None
        if parent is not None and Import.objects.filter(pk=parent, status=Import.Status.CONCLUDED).exists():
            metadata |= space_totals(parent)
            users = created_users(parent)
            if users:
                metadata['usuarios_cadastrados'] = users
        return metadata


def created_users(importation_pk):
    """Usuários cadastrados pelas linhas da aba de usuários de uma importação."""
    return ImportRow.objects.filter(
        parent_id=importation_pk, values__Tipo=USER_KIND, action=ImportRow.Action.CREATE,
    ).count()


def space_totals(importation_pk):
    """Totais de espaços da confirmação, contados dos registros de espaço que ela gravou (D13).

    Ficam fora dos campos da importação: vêm das alterações do cadastro aplicadas pela
    confirmação, que registram a chave da importação nas informações adicionais.
    """
    records = AuditLog.objects.filter(resource=catalog.SPACE, metadata__importacao=importation_pk)
    associated = sum(
        1 for record in records.filter(action=catalog.UPDATE)
        if len(record.new_values.get('outros_nomes') or []) > len(record.old_values.get('outros_nomes') or [])
    )
    return {
        'espacos_cadastrados': records.filter(action=catalog.CREATE).count(),
        'outros_nomes_associados': associated,
        'espacos_reativados': records.filter(action=catalog.ACTIVATE).count(),
    }


def space_totals_text(importation):
    """Trecho da mensagem de conclusão com os espaços alterados, sem as quantidades zero."""
    record = AuditLog.objects.filter(
        resource=catalog.SPACE_ALLOCATION_IMPORT, action=catalog.IMPORT, resource_id=str(importation.pk),
    ).order_by('-pk').first()
    totals = record.metadata if record else {}
    parts = []
    created = totals.get('espacos_cadastrados') or 0
    associated = totals.get('outros_nomes_associados') or 0
    reactivated = totals.get('espacos_reativados') or 0
    if created:
        parts.append(f'{created} espaço{"s" if created > 1 else ""} cadastrado{"s" if created > 1 else ""}')
    if associated:
        parts.append(f'{associated} outro{"s" if associated > 1 else ""} nome{"s" if associated > 1 else ""} associado{"s" if associated > 1 else ""}')
    if reactivated:
        parts.append(f'{reactivated} espaço{"s" if reactivated > 1 else ""} reativado{"s" if reactivated > 1 else ""}')
    return parts


def concluded_message(summary, importation=None):
    """Mensagem da importação de ensalamento concluída, com os totais e os espaços alterados."""
    created, updated, unchanged = summary['create'], summary['update'], summary['unchanged']
    parts = []
    if created:
        parts.append(f'{created} registro{"s" if created > 1 else ""} cadastrado{"s" if created > 1 else ""}')
    if updated:
        parts.append(f'{updated} atualizado{"s" if updated > 1 else ""}')
    if unchanged:
        parts.append(f'{unchanged} sem alteração')
    users = 0
    if importation is not None:
        parts.extend(space_totals_text(importation))
        users = created_users(importation.pk)
        if users:
            parts.append(f'{users} usuário{"s" if users > 1 else ""} cadastrado{"s" if users > 1 else ""}')
    if not parts:
        return 'Importação concluída. Nenhum registro foi cadastrado ou alterado.'
    message = f'Importação do ensalamento concluída. {", ".join(parts)}.'
    if users:
        message += ' O link para definir a senha será enviado aos usuários cadastrados.'
    return message
