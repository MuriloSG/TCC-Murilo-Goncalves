from html import escape
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

DEFAULT_OUTPUT = 'docs/diagramas'

PROJECT_APPS = ['accounts', 'schedule', 'bookings', 'imports', 'notices', 'audit', 'outbox', 'system_settings']

IDENTIFIER_COLOR = '#3b4fa8'

CONCEPTUAL_HEADER = '''  layout=neato; overlap=true; splines=line; bgcolor=white; pad=0.4;
  fontname="Helvetica"; fontsize=10; labelloc=b; labeljust=l;
  node [fontname="Helvetica", fontsize=10];
  edge [color="#222222"];'''

PHYSICAL_HEADER = '''  layout=neato; overlap=true; splines=line; bgcolor=white; pad=0.4;
  fontname="Helvetica"; fontsize=10; labelloc=b; labeljust=l;
  node [fontname="Helvetica", fontsize=10];
  edge [color="#222222"];'''

CONCEPTUAL_ENTITIES = {
    'Usuario': ('Usuário', ['id', 'nome', 'email', 'nome_de_usuario', 'ativo', 'superadmin']),
    'Perfil': ('Perfil', ['id', 'codigo', 'nome', 'descricao']),
    'Permissao': ('Permissão', ['id', 'codigo', 'descricao']),
    'Semestre': ('Semestre', ['id', 'codigo', 'inicio', 'fim']),
    'Faixa': ('Faixa de horário', ['id', 'inicio', 'fim']),
    'Curso': ('Curso', ['id', 'nome', 'modalidade']),
    'Turma': ('Turma', ['id', 'rotulo']),
    'Disciplina': ('Disciplina', ['id', 'nome']),
    'Docente': ('Docente', ['id', 'nome']),
    'Oferta': ('Oferta de disciplina', ['id']),
    'Vinculo': ('Vínculo docente', ['id', 'atual']),
    'Espaco': ('Espaço', ['id', 'nome', 'origem', 'ativo']),
    'OutroNome': ('Outro nome', ['id', 'nome']),
    'Ensalamento': ('Ensalamento', ['id', 'dia_da_semana', 'origem', 'vigente_de', 'vigente_ate']),
    'Ocorrencia': ('Ocorrência cancelada', ['id', 'data', 'tipo']),
    'Solicitacao': ('Solicitação', [
        'id', 'data', 'inicio', 'fim', 'descricao', 'quantidade_de_alunos', 'situacao',
        'motivo_da_recusa', 'alternativa_sugerida', 'motivo_do_cancelamento',
    ]),
    'Agendamento': ('Agendamento', ['id', 'inicio', 'fim', 'descricao', 'quantidade_de_alunos']),
    'Importacao': ('Importação', ['id', 'tipo', 'situacao', 'arquivo', 'resultado']),
    'Linha': ('Linha da importação', ['id', 'numero', 'valores', 'acao', 'erros']),
    'Decisao': ('Decisão de espaço', ['id', 'nome_encontrado', 'decisao', 'nome_alvo']),
    'Aviso': ('Aviso', ['id', 'tipo', 'titulo', 'mensagem', 'destino']),
    'Notificacao': ('Notificação', ['id', 'titulo', 'mensagem', 'link', 'lida_em']),
    'Auditoria': ('Registro de auditoria', ['id', 'acao', 'recurso', 'valores', 'origem', 'ip']),
}

CONCEPTUAL_FOOTNOTES = ['Solicitacao', 'Usuario']

# Célula (coluna, linha) de cada entidade, agrupada por módulo: acadêmico à esquerda,
# espaços e reservas no centro, usuários e administração à direita. A linha 0 fica embaixo.
CONCEPTUAL_GRID = {
    'Oferta': (0, 4), 'Curso': (1, 4), 'Turma': (1, 3), 'Disciplina': (1, 1), 'Semestre': (0, 1),
    'Faixa': (1, 0), 'Vinculo': (2, 5), 'Docente': (2, 3), 'Ensalamento': (2, 0),
    'Ocorrencia': (6, 1.25), 'Espaco': (3, 1), 'OutroNome': (3, 0), 'Solicitacao': (3, 3),
    'Agendamento': (4, 2), 'Decisao': (4, 1),
    'Usuario': (4, 4), 'Perfil': (5, 4), 'Permissao': (5, 3), 'Auditoria': (5, 5),
    'Importacao': (5, 2), 'Linha': (5, 1), 'Aviso': (3, 5), 'Notificacao': (4, 5),
}

# Célula do losango dos relacionamentos que não ficam no meio da linha. Sem ele, a linha reta cruzaria outra;
# com o losango aqui, ela dobra nele e passa pela borda do diagrama.
CONCEPTUAL_DIAMONDS = {('Ensalamento', 'tem', 'Ocorrencia'): (4, -0.5)}

# Geometria em polegadas: tamanho da célula, retângulo da entidade, losango e rótulo de cardinalidade.
CELL_WIDTH, CELL_HEIGHT = 6.2, 3.4
BOX_WIDTH = 140 / 72
ATTRIBUTE_ROW = 13 / 72
CHAR_WIDTH = 6.2 / 72
DIAMOND_WIDTH, DIAMOND_HEIGHT = 1.5, 0.55
LABEL_WIDTH, LABEL_HEIGHT = 0.4, 0.17
PARALLEL_OFFSET = 0.7  # afastamento do losango quando duas entidades têm mais de um relacionamento

# Colunas do DER físico, da esquerda para a direita, com as tabelas de cima para baixo. A ordem foi
# escolhida para que nenhuma linha atravesse uma tabela nem cruze outra; uma tabela nova precisa entrar aqui.
PHYSICAL_COLUMNS = [
    ['schedule_semester', 'schedule_classgroup', 'schedule_allocation', 'schedule_timeslot'],
    ['schedule_classoffering', 'schedule_course', 'schedule_subject', 'schedule_allocation_teachers'],
    ['schedule_teachingassignment', 'outbox_outboxentry', 'schedule_teacher', 'schedule_space', 'schedule_spacename'],
    ['bookings_bookingrequest', 'bookings_booking', 'imports_import', 'imports_importrow', 'schedule_spacedecision', 'schedule_allocationexception'],
    ['audit_auditlog', 'system_settings_systemsetting', 'accounts_user'],
    ['notices_notification', 'notices_notice', 'accounts_userrole', 'accounts_role', 'accounts_rolepermission', 'accounts_permission'],
]

# Geometria do DER físico em polegadas: linhas da tabela, espaço entre colunas e entre tabelas.
TABLE_TITLE, TABLE_ROW = 20 / 72, 18 / 72
UPPER_CHAR_WIDTH = 7.2 / 72
COLUMN_GAP, TABLE_GAP = 2.0, 0.6
BRACKET_OFFSET, BRACKET_STEP = 0.3, 0.22  # colchete das ligações entre tabelas da mesma coluna
BRACKET_CLEARANCE = 0.15  # folga vertical para dois colchetes dividirem o mesmo afastamento
SLOT_BETWEEN_ROWS = 0.06  # preferência pela ponta no meio da linha da tabela
TRACK_STEP, TRACK_MARGIN = 0.16, 0.6  # trilhas verticais no vão entre colunas e folga até os colchetes
TRACK_CLEARANCE = 0.12  # folga vertical para duas linhas dividirem a mesma trilha
MIN_JOG = 0.15  # menor degrau aceito numa linha; abaixo disso a ponta se alinha e a linha fica reta
SLOT_CLEARANCE = 0.1  # distância mínima entre duas pontas na mesma borda de tabela

# Espaço extra, em polegadas, acima de uma tabela na sua coluna.
PHYSICAL_SPACING = {'audit_auditlog': 1.5, 'bookings_booking': 0.25, 'schedule_allocation': 1.0, 'schedule_allocation_teachers': 0.5, 'schedule_allocationexception': 0.5, 'schedule_classgroup': 1.0, 'schedule_classoffering': 1.0, 'schedule_course': 0.25, 'schedule_semester': 0.5}

# Ligações na mesma coluna cujo colchete contorna a coluna pela esquerda; as demais vão pela direita.
PHYSICAL_LEFT_BRACKETS = {
    'accounts_rolepermission.permission_id',
    'accounts_rolepermission.role_id',
    'accounts_userrole.role_id',
    'bookings_booking.request_id',
    'imports_importrow.parent_id',
    'schedule_allocation.semester_id',
    'schedule_allocation.time_slot_id',
    'schedule_spacedecision.importation_id',
    'schedule_teachingassignment.teacher_id',
    'schedule_timeslot.semester_id',
}

CONCEPTUAL_RELATIONSHIPS = [
    ('Usuario', '(0,n)', 'tem', 'Perfil', '(0,1)'),
    ('Perfil', '(0,n)', 'concede', 'Permissao', '(0,n)'),
    ('Semestre', '(1,1)', 'define', 'Faixa', '(0,n)'),
    ('Curso', '(1,1)', 'possui', 'Turma', '(0,n)'),
    ('Espaco', '(1,1)', 'também se chama', 'OutroNome', '(0,n)'),
    ('Semestre', '(1,1)', 'oferta', 'Oferta', '(0,n)'),
    ('Disciplina', '(1,1)', 'é ofertada em', 'Oferta', '(0,n)'),
    ('Turma', '(1,1)', 'cursa', 'Oferta', '(0,n)'),
    ('Oferta', '(1,1)', 'tem docente', 'Vinculo', '(0,n)'),
    ('Docente', '(1,1)', 'assume', 'Vinculo', '(0,n)'),
    ('Semestre', '(1,1)', 'contém', 'Ensalamento', '(0,n)'),
    ('Turma', '(1,1)', 'assiste', 'Ensalamento', '(0,n)'),
    ('Disciplina', '(1,1)', 'é lecionada em', 'Ensalamento', '(0,n)'),
    ('Faixa', '(1,1)', 'ocupa', 'Ensalamento', '(0,n)'),
    ('Espaco', '(0,1)', 'recebe', 'Ensalamento', '(0,n)'),
    ('Docente', '(0,n)', 'ministra', 'Ensalamento', '(0,n)'),
    ('Ensalamento', '(1,1)', 'tem', 'Ocorrencia', '(0,n)'),
    ('Usuario', '(1,1)', 'cancela', 'Ocorrencia', '(0,n)'),
    ('Usuario', '(1,1)', 'solicita', 'Solicitacao', '(0,n)'),
    ('Usuario', '(0,1)', 'analisa', 'Solicitacao', '(0,n)'),
    ('Espaco', '(1,1)', 'é solicitado em', 'Solicitacao', '(0,n)'),
    ('Vinculo', '(0,1)', 'justifica', 'Solicitacao', '(0,n)'),
    ('Solicitacao', '(1,1)', 'gera', 'Agendamento', '(0,1)'),
    ('Espaco', '(1,1)', 'é reservado em', 'Agendamento', '(0,n)'),
    ('Usuario', '(1,1)', 'envia', 'Importacao', '(0,n)'),
    ('Importacao', '(1,1)', 'contém', 'Linha', '(0,n)'),
    ('Importacao', '(1,1)', 'pede', 'Decisao', '(0,n)'),
    ('Espaco', '(0,1)', 'aponta para', 'Decisao', '(0,n)'),
    ('Usuario', '(0,1)', 'publica', 'Aviso', '(0,n)'),
    ('Aviso', '(0,1)', 'gera', 'Notificacao', '(0,n)'),
    ('Usuario', '(1,1)', 'recebe', 'Notificacao', '(0,n)'),
    ('Usuario', '(0,1)', 'executa', 'Auditoria', '(0,n)'),
]

RESTRICTIONS_HEADER = """# Restrições do DER físico

Gerado por `make er-diagram` (comando `export_er_diagram`). Não edite à mão.

Constraints e índices que o diagrama não representa, com o SQL que o Django executa no PostgreSQL.

| Tabela | Nome | SQL |
|---|---|---|"""


# Posição fixa no Graphviz: "x,y!" em polegadas. O "!" fica numa constante para não ser lido como texto de interface.
PIN = '!'


def pinned(x, y):
    return f'"{x:.3f},{y:.3f}{PIN}"'


def attribute_row(name, identifier):
    """Atributo no estilo do brModelo: traço, círculo (cheio no identificador) e nome."""
    color = IDENTIFIER_COLOR if identifier else '#222222'
    circle = '●' if identifier else '○'
    label = f'<B>{escape(name)}</B>' if identifier else escape(name)
    return f'<TR><TD ALIGN="LEFT" HEIGHT="13">─<FONT COLOR="{color}">{circle}</FONT> {label}</TD></TR>'


class Entity:
    """Geometria da entidade: retângulo com o nome e, à direita, a coluna de atributos (ou o asterisco)."""

    def __init__(self, key):
        self.key = key
        self.name, self.attributes = CONCEPTUAL_ENTITIES[key]
        self.footnote = key in CONCEPTUAL_FOOTNOTES
        column, row = CONCEPTUAL_GRID[key]
        self.x, self.y = column * CELL_WIDTH, row * CELL_HEIGHT  # centro do retângulo
        rows = 1 if self.footnote else len(self.attributes)
        self.height = max(0.5, rows * ATTRIBUTE_ROW + 8 / 72)
        longest = 1 if self.footnote else max(len(attribute) for attribute in self.attributes) + 3
        self.side = longest * CHAR_WIDTH + 6 / 72

    def rect(self):
        """Retângulo ocupado pela entidade inteira, atributos incluídos (x0, y0, x1, y1)."""
        return (self.x - BOX_WIDTH / 2, self.y - self.height / 2, self.x + BOX_WIDTH / 2 + self.side, self.y + self.height / 2)

    def exit_point(self, tx, ty):
        """Onde a linha em direção a (tx, ty) sai da entidade, sem passar por cima dos atributos."""
        dx, dy = tx - self.x, ty - self.y
        half_width, half_height = BOX_WIDTH / 2, self.height / 2
        to_side = half_width / abs(dx) if dx else float('inf')
        to_top = half_height / abs(dy) if dy else float('inf')
        if dx <= 0 or to_top <= to_side:
            t = min(to_side, to_top)
            return self.x + dx * t, self.y + dy * t
        if (half_width + self.side) / dx <= to_top:  # passa por toda a coluna de atributos: sai à direita dela
            t = (half_width + self.side) / dx
            return self.x + dx * t, self.y + dy * t
        return self.x + half_width, self.y + (half_height if dy > 0 else -half_height)  # sai pelo canto

    def node(self):
        box = (
            f'<TD BORDER="1" WIDTH="{BOX_WIDTH * 72:.0f}" HEIGHT="{self.height * 72:.0f}">'
            f'<B>{escape(self.name)}</B></TD>'
        )
        size = f'WIDTH="{self.side * 72:.0f}" HEIGHT="{self.height * 72:.0f}"'
        if self.footnote:
            side = f'<TD {size} ALIGN="LEFT" VALIGN="TOP">*</TD>'
        else:
            rows = ''.join(attribute_row(attribute, attribute == 'id') for attribute in self.attributes)
            side = (
                f'<TD {size} BORDER="1" SIDES="L" ALIGN="LEFT">'
                f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0">{rows}</TABLE></TD>'
            )
        center = self.x + self.side / 2  # o nó é centrado na tabela inteira, não no retângulo do nome
        return (
            f'  {self.key} [shape=plain, pos={pinned(center, self.y)}, '
            f'label=<<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0"><TR>{box}{side}</TR></TABLE>>];'
        )


def overlaps(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def segment_hits_rect(start, end, rect):
    """Teste de interseção entre segmento e retângulo (Liang-Barsky)."""
    t0, t1 = 0.0, 1.0
    dx, dy = end[0] - start[0], end[1] - start[1]
    for p, q in ((-dx, start[0] - rect[0]), (dx, rect[2] - start[0]), (-dy, start[1] - rect[1]), (dy, rect[3] - start[1])):
        if p == 0:
            if q < 0:
                return False
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return False
    return True


def centered_rect(x, y, width, height):
    return (x - width / 2, y - height / 2, x + width / 2, y + height / 2)


def conceptual_layout():
    """Losangos no meio das linhas e pontas das linhas na borda das entidades."""
    entities = {key: Entity(key) for key in CONCEPTUAL_ENTITIES}
    pairs = [frozenset((left, right)) for left, _, _, right, _ in CONCEPTUAL_RELATIONSHIPS]
    relationships = []
    for index, (left, left_cardinality, verb, right, right_cardinality) in enumerate(CONCEPTUAL_RELATIONSHIPS):
        a, b = entities[left], entities[right]
        start, end = a.exit_point(b.x, b.y), b.exit_point(a.x, a.y)
        x, y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        total = pairs.count(pairs[index])
        if (left, verb, right) in CONCEPTUAL_DIAMONDS:  # losango fora do meio: a linha dobra nele e contorna o diagrama
            column, row = CONCEPTUAL_DIAMONDS[left, verb, right]
            x, y = column * CELL_WIDTH, row * CELL_HEIGHT
            start, end = a.exit_point(x, y), b.exit_point(x, y)
        elif total > 1:  # relacionamentos paralelos: afasta o losango e recalcula as pontas na direção dele
            length = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
            shift = (pairs[:index].count(pairs[index]) - (total - 1) / 2) * 2 * PARALLEL_OFFSET
            x, y = x - (end[1] - start[1]) / length * shift, y + (end[0] - start[0]) / length * shift
            start, end = a.exit_point(x, y), b.exit_point(x, y)
        relationships.append((index, verb, (x, y), [(left, start, left_cardinality), (right, end, right_cardinality)]))
    return entities, relationships


def place_labels(ends, obstacles, segments):
    """Rótulo junto de cada ponta de linha, na primeira posição que não encosta em nada.

    `ends` traz (ponta, ponto para onde a linha segue, texto). Sem posição livre, fica a que menos encosta.
    """
    placed = []
    for point, toward, text in ends:
        dx, dy = toward[0] - point[0], toward[1] - point[1]
        length = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / length, dy / length
        clearance = abs(uy) * LABEL_WIDTH / 2 + abs(ux) * LABEL_HEIGHT / 2 + 0.05
        candidates = [
            (point[0] + ux * along - uy * side * clearance, point[1] + uy * along + ux * side * clearance)
            for along in (0.3, 0.45, 0.6, 0.8, 1.0, 1.25, 1.5)
            for side in (1, -1)
        ]

        def conflicts(center):
            rect = centered_rect(*center, LABEL_WIDTH, LABEL_HEIGHT)
            margin = centered_rect(*center, LABEL_WIDTH + 0.06, LABEL_HEIGHT + 0.06)
            return (
                sum(overlaps(rect, other, 0.04) for other in obstacles + placed)
                + sum(segment_hits_rect(a, b, margin) for a, b in segments)
            )

        chosen = min(candidates, key=conflicts)
        placed.append(centered_rect(*chosen, LABEL_WIDTH, LABEL_HEIGHT))
        yield chosen, text


def place_cardinalities(entities, relationships):
    """Cardinalidades do DER conceitual, junto das pontas das linhas entre entidades e losangos."""
    obstacles = [entity.rect() for entity in entities.values()]
    obstacles += [centered_rect(x, y, DIAMOND_WIDTH * 0.8, DIAMOND_HEIGHT * 0.8) for _, _, (x, y), _ in relationships]
    segments = [(point, diamond) for _, _, diamond, ends in relationships for _, point, _ in ends]
    ends = [(point, diamond, cardinality) for _, _, diamond, ends in relationships for _, point, cardinality in ends]
    return place_labels(ends, obstacles, segments)


def render_conceptual():
    """DOT do DER conceitual na notação de Peter Chen, como no brModelo.

    As posições são calculadas aqui: cada linha sai da borda da entidade (nunca por cima dos atributos)
    e cada cardinalidade fica perto da sua ponta, num lugar livre de outras linhas, rótulos e entidades.
    """
    entities, relationships = conceptual_layout()
    lines = ['graph conceitual {', CONCEPTUAL_HEADER]
    lines += [entity.node() for entity in entities.values()]
    for index, verb, (x, y), ends in relationships:
        lines.append(
            f'  r{index} [shape=diamond, label="{verb}", pos={pinned(x, y)}, fontsize=9, '
            f'width={DIAMOND_WIDTH}, height={DIAMOND_HEIGHT}, fixedsize=true];'
        )
        for side, (_, (px, py), _) in zip('ab', ends):
            lines.append(f'  p{index}{side} [shape=point, width=0.01, height=0.01, style=invis, pos={pinned(px, py)}];')
        lines.append(f'  p{index}a -- r{index} -- p{index}b;')
    labels = place_cardinalities(entities, relationships)
    for number, ((x, y), cardinality) in enumerate(labels):
        lines.append(f'  c{number} [shape=plain, label="{cardinality}", fontsize=9, pos={pinned(x, y)}];')
    footnotes = ''.join(
        f'* {CONCEPTUAL_ENTITIES[key][0]}({", ".join(CONCEPTUAL_ENTITIES[key][1])})\\l' for key in CONCEPTUAL_FOOTNOTES
    )
    lines.append(f'  label="{footnotes}";')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def project_models():
    """Models concretos das apps do projeto, incluindo as tabelas de ligação, em ordem de nome de tabela."""
    return sorted(
        (
            model
            for label in PROJECT_APPS
            for model in apps.get_app_config(label).get_models(include_auto_created=True)
            if not model._meta.proxy
        ),
        key=lambda model: model._meta.db_table,
    )


def foreign_keys(model):
    """FKs e OneToOne declaradas na própria tabela."""
    return [field for field in model._meta.local_fields if field.is_relation and (field.many_to_one or field.one_to_one)]


def column_type(field):
    """Tipo da coluna no PostgreSQL, em maiúsculas."""
    db_type = field.rel_db_type(connection) if field.is_relation else field.db_type(connection)
    return (db_type or '').upper()


def column_cells(field):
    """Marcador e nome, tipo, nulo e chaves de uma coluna, como texto."""
    keys = ', '.join(
        key for key, present in [
            ('PK', field.primary_key), ('FK', field.is_relation), ('UK', field.unique and not field.primary_key),
        ] if present
    )
    return field.column, column_type(field), 'NULL' if field.null else 'NOT NULL', keys


class Table:
    """Geometria de uma tabela do DER físico. `x` e `y` são o canto superior esquerdo, com `y` crescendo para baixo."""

    def __init__(self, model):
        self.name = model._meta.db_table
        self.fields = list(model._meta.local_fields)
        cells = [column_cells(field) for field in self.fields]
        self.widths = [
            (max(len(cell[0]) for cell in cells) + 3) * CHAR_WIDTH + 6 / 72,
            max(len(cell[1]) for cell in cells) * UPPER_CHAR_WIDTH + 8 / 72,
            max(len(cell[2]) for cell in cells) * UPPER_CHAR_WIDTH + 8 / 72,
            max(max(len(cell[3]) for cell in cells), 2) * UPPER_CHAR_WIDTH + 8 / 72,
        ]
        title = len(self.name) * 6.8 / 72 + 14 / 72
        if sum(self.widths) < title:
            self.widths[0] += title - sum(self.widths)
        self.width = sum(self.widths)
        self.height = TABLE_TITLE + len(self.fields) * TABLE_ROW
        self.x = self.y = 0.0

    def rect(self):
        """Retângulo no sistema do Graphviz (y para cima): (x0, y0, x1, y1)."""
        return (self.x, -(self.y + self.height), self.x + self.width, -self.y)

    def center(self):
        return self.x + self.width / 2, -(self.y + self.height / 2)

    def node(self):
        sizes = [f'WIDTH="{width * 72:.0f}" HEIGHT="{TABLE_ROW * 72:.0f}"' for width in self.widths]
        rows = []
        for field in self.fields:
            name, kind, nullable, keys = (escape(text) for text in column_cells(field))
            if field.primary_key:
                marker, name = f'<FONT COLOR="{IDENTIFIER_COLOR}">●</FONT>', f'<B>{name}</B>'
            else:
                marker = '◆' if field.is_relation else '○'
            texts = [f'{marker} {name}', kind, nullable, keys]
            rows.append('<TR>' + ''.join(f'<TD ALIGN="LEFT" {size}>{text}</TD>' for size, text in zip(sizes, texts)) + '</TR>')
        title = f'<TR><TD COLSPAN="4" BORDER="1" SIDES="B" HEIGHT="{TABLE_TITLE * 72:.0f}"><B>{self.name}</B></TD></TR>'
        table = f'<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">{title}{"".join(rows)}</TABLE>'
        return f'  {self.name} [shape=plain, pos={pinned(*self.center())}, label=<{table}>];'


def cardinalities(field):
    """(mín,máx) do lado da tabela filha e do lado da tabela referenciada."""
    child = '(0,1)' if field.one_to_one or field.unique else '(0,n)'
    parent = '(0,1)' if field.null else '(1,1)'
    return child, parent


def physical_layout(models):
    """Posiciona as tabelas em `PHYSICAL_COLUMNS` e calcula o traçado de cada linha de chave estrangeira."""
    tables = {model._meta.db_table: Table(model) for model in models}
    laid_out = [name for column in PHYSICAL_COLUMNS for name in column]
    missing, extra = set(tables) - set(laid_out), set(laid_out) - set(tables)
    if missing or extra:
        raise CommandError(f'Atualize PHYSICAL_COLUMNS. Faltam: {sorted(missing)}. Sobram: {sorted(extra)}.')
    keys = [(model, field) for model in models for field in foreign_keys(model)]
    fks = [
        (model._meta.db_table, tables[model._meta.db_table].fields.index(field), field.related_model._meta.db_table, field.column)
        for model, field in keys
    ]
    sizes = {name: (table.width, table.height) for name, table in tables.items()}
    corners, routes = physical_geometry(PHYSICAL_COLUMNS, PHYSICAL_SPACING, PHYSICAL_LEFT_BRACKETS, sizes, fks)
    for name, (x, y) in corners.items():
        tables[name].x, tables[name].y = x, y
    links = [
        {
            'child': tables[model._meta.db_table], 'field': field, 'parent': tables[field.related_model._meta.db_table],
            'points': [(x, -y) for x, y in route],  # o Graphviz usa y para cima
        }
        for (model, field), route in zip(keys, routes)
    ]
    return tables, links


def physical_geometry(columns, spacing, left_brackets, sizes, fks):
    """Canto de cada tabela e traçado de cada FK, em polegadas e com y crescendo para baixo.

    `sizes` traz (largura, altura) por tabela e `fks` traz (filha, posição da coluna da FK, referenciada, coluna).
    Todas as linhas são ortogonais. Entre colunas, a linha sai na altura da FK pelo lado voltado para a tabela
    referenciada, sobe ou desce numa trilha só dela no vão entre as colunas e entra na tabela referenciada na
    horizontal. Na mesma coluna, ela contorna a coluna por fora, como um colchete: pela direita, ou pela esquerda
    se estiver em `left_brackets` ("tabela.coluna").
    """
    column_of, spans = {}, {}
    for index, column in enumerate(columns):
        y = 0.0
        for name in column:
            y += spacing.get(name, 0.0)
            spans[name], column_of[name] = (y, y + sizes[name][1]), index
            y += sizes[name][1] + TABLE_GAP
    plan = plan_links(columns, column_of, spans, left_brackets, fks)
    edges, gaps, x = [], [], 0.0
    for index, column in enumerate(columns):
        edges.append((x, x + max(sizes[name][0] for name in column)))
        right, left = plan['channels'].get((index, True), 0.0), plan['channels'].get((index + 1, False), 0.0)
        count = plan['tracks'].get(index, 0)
        width = max(COLUMN_GAP, right + left + 2 * TRACK_MARGIN + max(count - 1, 0) * TRACK_STEP)
        # As trilhas ficam centradas no espaço que sobra entre os colchetes das duas colunas.
        first = edges[-1][1] + right + (width - right - left - max(count - 1, 0) * TRACK_STEP) / 2
        gaps.append(first)
        x = edges[-1][1] + width
    corners = {name: (edges[column_of[name]][0], top) for name, (top, _) in spans.items()}

    def side(name, right):
        return corners[name][0] + (sizes[name][0] if right else 0.0)

    routes = []
    for index, (child, _, parent, _) in enumerate(fks):
        child_right, parent_right = plan['sides'][index]
        start = (side(child, child_right), plan['starts'][index])
        end = (side(parent, parent_right), plan['ends'][index])
        if column_of[child] == column_of[parent]:
            column = column_of[child]
            offset = BRACKET_OFFSET + plan['brackets'][index] * BRACKET_STEP
            bend = edges[column][1] + offset if child_right else edges[column][0] - offset
            points = [start, (bend, start[1]), (bend, end[1]), end]
        else:
            reverse = column_of[child] > column_of[parent]
            first, last = (end, start) if reverse else (start, end)
            points = [first]
            for gap, low, high in plan['pieces'][index]:
                if low != high:
                    track = gaps[gap] + plan['track_of'][index, gap] * TRACK_STEP
                    points += [(track, low), (track, high)]
            points.append(last)
            if reverse:
                points.reverse()
        routes.append([point for number, point in enumerate(points) if number == 0 or point != points[number - 1]])
    return corners, routes


def plan_links(columns, column_of, spans, left_brackets, fks):
    """Parte vertical do traçado: alturas das pontas, lados, trilhas dos colchetes e trilhas nos vãos."""
    sides, starts, approach = [], [], []
    for child, row, parent, column in fks:
        if column_of[child] == column_of[parent]:
            right = f'{child}.{column}' not in left_brackets
            sides.append((right, right))
        else:
            right = column_of[parent] > column_of[child]
            sides.append((right, not right))
        starts.append(spans[child][0] + TABLE_TITLE + (row + 0.5) * TABLE_ROW)
        between = range(min(column_of[child], column_of[parent]) + 1, max(column_of[child], column_of[parent]))
        approach.append(corridor(starts[-1], [columns[number] for number in between], spans) if between else starts[-1])
    exits = {}
    for index, (child, row, _, _) in enumerate(fks):
        exits.setdefault((child, sides[index][0]), set()).add(row)
    groups = {}
    for index, (_, _, parent, _) in enumerate(fks):
        groups.setdefault((parent, sides[index][1]), []).append(index)
    ends = [None] * len(fks)
    for (parent, right), group in groups.items():
        top, bottom = spans[parent]

        def order(index):
            # Pela borda, de cima para baixo: colchetes vindos de cima (o mais próximo primeiro), linhas de
            # outras colunas (na ordem de chegada) e colchetes vindos de baixo (o mais distante primeiro).
            if column_of[fks[index][0]] == column_of[parent]:
                return (0, -starts[index]) if starts[index] < top else (2, -starts[index])
            return (1, approach[index])

        group.sort(key=order)
        rows = round((bottom - top - TABLE_TITLE) / TABLE_ROW)
        used = exits.get((parent, right), set())
        # Pontas possíveis: o meio de cada linha da tabela (menos as que já têm FK saindo) e a divisa entre linhas.
        slots = [
            (top + TABLE_TITLE + step * TABLE_ROW / 2, step % 2 == 0)
            for step in range(1, 2 * rows) if step % 2 == 0 or (step - 1) // 2 not in used
        ]
        wanted = [approach[index] for index in group]
        for index, y in zip(group, assign_slots(wanted, [(top, bottom)] * len(group), slots, top, bottom)):
            ends[index] = y
        # Ponta a menos de MIN_JOG da altura de chegada vira linha reta: um degrau tão pequeno parece uma falha.
        leaving = [top + TABLE_TITLE + (row + 0.5) * TABLE_ROW for row in used]
        for index in group:
            target = approach[index]
            others = [ends[other] for other in group if other != index] + leaving
            if (
                0 < abs(ends[index] - target) < MIN_JOG and top + TABLE_TITLE + 0.05 < target < bottom - 0.05
                and all(abs(target - other) > SLOT_CLEARANCE for other in others)
            ):
                ends[index] = target
    brackets, channels, nests = {}, {}, {}
    for index, (child, _, parent, _) in enumerate(fks):
        if column_of[child] == column_of[parent]:
            nests.setdefault((column_of[child], sides[index][0]), []).append(index)
    for key, group in nests.items():
        # Colchetes aninhados: o de menor vão fica mais perto da coluna, para um não cortar o outro.
        group.sort(key=lambda index: (abs(ends[index] - starts[index]), index))
        for index in group:
            low, high = sorted((starts[index], ends[index]))
            inner = [
                brackets[other] for other in group if other in brackets
                and min(starts[other], ends[other]) < high + BRACKET_CLEARANCE
                and low < max(starts[other], ends[other]) + BRACKET_CLEARANCE
            ]
            brackets[index] = max(inner) + 1 if inner else 0
        channels[key] = BRACKET_OFFSET + max(brackets[index] for index in group) * BRACKET_STEP
    pieces, by_gap = {}, {}
    for index, (child, _, parent, _) in enumerate(fks):
        if column_of[child] == column_of[parent]:
            continue
        reverse = column_of[child] > column_of[parent]
        left, right = (parent, child) if reverse else (child, parent)
        left_y, right_y = (ends[index], starts[index]) if reverse else (starts[index], ends[index])
        first, last = column_of[left], column_of[right] - 1
        pieces[index] = [
            (gap, left_y if gap == first else approach[index], right_y if gap == last else approach[index])
            for gap in range(first, last + 1)
        ]
        for gap, low, high in pieces[index]:
            if low != high:
                by_gap.setdefault(gap, []).append((index, low, high))
    track_of, tracks = {}, {}
    for gap, items in by_gap.items():
        assigned = assign_tracks(items)
        tracks[gap] = max(assigned.values()) + 1
        track_of.update({(index, gap): track for index, track in assigned.items()})
    return {
        'sides': sides, 'starts': starts, 'ends': ends, 'brackets': brackets, 'channels': channels,
        'pieces': pieces, 'track_of': track_of, 'tracks': tracks,
    }


def corridor(y, columns, spans):
    """Altura livre de tabelas em todas as `columns`, a mais próxima de `y`, para a linha atravessá-las."""
    blocked = sorted(
        (spans[name][0] - TABLE_GAP / 4, spans[name][1] + TABLE_GAP / 4) for column in columns for name in column
    )
    candidates = [y] + [edge for interval in blocked for edge in (interval[0] - 0.01, interval[1] + 0.01)]
    free = [value for value in candidates if not any(low < value < high for low, high in blocked)]
    return min(free, key=lambda value: (abs(value - y), value))


def assign_tracks(items):
    """Trilha (0 é a mais à esquerda) de cada trecho vertical num vão, sem cruzamentos que possam ser evitados.

    `items` traz (ligação, altura na borda esquerda do vão, altura na borda direita). Duas linhas só se cruzam
    se a horizontal de uma passar pela vertical da outra; quando só uma das ordens evita isso, ela é obrigatória.
    """
    def inside(value, a, b):
        low, high = sorted((a, b))
        return low + 1e-6 < value < high - 1e-6

    def left_of(a, b):
        return not inside(a[2], b[1], b[2]) and not inside(b[1], a[1], a[2])

    before = {item[0]: set() for item in items}
    for number, a in enumerate(items):
        for b in items[number + 1:]:
            ab, ba = left_of(a, b), left_of(b, a)
            if ab and not ba:
                before[b[0]].add(a[0])
            elif ba and not ab:
                before[a[0]].add(b[0])
    span = {index: sorted((low, high)) for index, low, high in items}
    track, pending = {}, sorted(items, key=lambda item: (min(item[1], item[2]), item[0]))
    while pending:
        ready = [item for item in pending if before[item[0]] <= set(track)]
        item = ready[0] if ready else min(pending, key=lambda item: len(before[item[0]] - set(track)))
        pending.remove(item)
        index = item[0]
        low, high = span[index]
        taken = {
            track[other] for other in track
            if span[other][0] < high + TRACK_CLEARANCE and low < span[other][1] + TRACK_CLEARANCE
        }
        value = max((track[other] + 1 for other in before[index] if other in track), default=0)
        while value in taken:
            value += 1
        track[index] = value
    return track


def assign_slots(wanted, bounds, slots, top, bottom):
    """Escolhe, na ordem, uma ponta para cada linha, entre os limites dela e o mais perto da altura de onde vem."""
    inf = float('inf')
    for limits in (bounds, [(top, bottom)] * len(wanted)):  # sem solução nos limites, ignora os limites
        cost = [[0.0] * (len(slots) + 1)] + [[inf] * (len(slots) + 1) for _ in wanted]
        for i, (y, (low, high)) in enumerate(zip(wanted, limits), 1):
            for j, (slot, between) in enumerate(slots, 1):
                here = abs(slot - y) + (SLOT_BETWEEN_ROWS if between else 0) if low < slot < high else inf
                cost[i][j] = min(cost[i][j - 1], cost[i - 1][j - 1] + here)
        if cost[-1][-1] < inf:
            break
    else:  # mais linhas que pontas: distribui igualmente pela borda
        top, bottom = top + TABLE_TITLE + 0.08, bottom - 0.08
        return [top + (bottom - top) * number / (len(wanted) + 1) for number in range(1, len(wanted) + 1)]
    chosen, j = [], len(slots)
    for i in range(len(wanted), 0, -1):
        while cost[i][j] == cost[i][j - 1]:
            j -= 1
        chosen.append(slots[j - 1][0])
        j -= 1
    return chosen[::-1]


def route_problems(routes, fks, rects):
    """Cruzamentos e sobreposições entre linhas mais trechos que passam por cima de uma tabela."""
    cuts = sum(
        segment_hits_rect(a, b, (x0 - 0.05, y0 - 0.05, x1 + 0.05, y1 + 0.05))
        for route, (child, _, parent, _) in zip(routes, fks)
        for a, b in zip(route, route[1:])
        for name, (x0, y0, x1, y1) in rects.items() if name not in (child, parent)
    )
    return len(crossing_pairs(routes)) + cuts


def crossing_pairs(routes):
    """Pares de linhas diferentes que se cruzam ou correm uma sobre a outra (o toque nas pontas não conta)."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    def shared(a, b, c, d):
        # Trechos na mesma reta horizontal ou vertical que dividem mais que um ponto.
        for axis in (0, 1):
            if a[axis] == b[axis] == c[axis] == d[axis]:
                other = 1 - axis
                low = max(min(a[other], b[other]), min(c[other], d[other]))
                high = min(max(a[other], b[other]), max(c[other], d[other]))
                return high - low > 1e-6
        return False

    segments = [(a, b, index) for index, route in enumerate(routes) for a, b in zip(route, route[1:])]
    found = []
    for number, (a, b, first) in enumerate(segments):
        for c, d, second in segments[number + 1:]:
            if first == second:
                continue
            if shared(a, b, c, d) or (
                not {a, b} & {c, d} and ccw(c, d, a) * ccw(c, d, b) < 0 and ccw(a, b, c) * ccw(a, b, d) < 0
            ):
                found.append((first, second))
    return found


def crossing_lines(links):
    return crossing_pairs([link['points'] for link in links])


def physical_labels(tables, links):
    obstacles = [table.rect() for table in tables.values()]
    segments = [pair for link in links for pair in zip(link['points'], link['points'][1:])]
    ends = []
    for link in links:
        child_card, parent_card = cardinalities(link['field'])
        points = link['points']
        ends += [(points[0], points[1], child_card), (points[-1], points[-2], parent_card)]
    return place_labels(ends, obstacles, segments)


def render_physical(models):
    """DOT do DER físico com todas as tabelas, colunas, tipos e chaves, em posições fixas."""
    tables, links = physical_layout(models)
    lines = ['graph fisico {', PHYSICAL_HEADER]
    lines.append('  label="● chave primária   ◆ chave estrangeira   ○ coluna\\l";')
    lines += [table.node() for table in tables.values()]
    for index, link in enumerate(links):
        names = [f'f{index}p{number}' for number in range(len(link['points']))]
        for name, point in zip(names, link['points']):
            lines.append(f'  {name} [shape=point, width=0.01, height=0.01, style=invis, pos={pinned(*point)}];')
        child_card, parent_card = cardinalities(link['field'])
        lines.append(
            f'  {" -- ".join(names)};  // {link["child"].name}.{link["field"].column} -> {link["parent"].name} '
            f'{child_card}/{parent_card}'
        )
    for number, (center, text) in enumerate(physical_labels(tables, links)):
        lines.append(f'  k{number} [shape=plain, label="{text}", fontsize=9, pos={pinned(*center)}];')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def render_restrictions(models):
    """Markdown com o SQL das constraints e dos índices."""
    lines = [RESTRICTIONS_HEADER]
    with connection.schema_editor(collect_sql=True) as editor:
        for model in models:
            for item in [*model._meta.constraints, *model._meta.indexes]:
                sql = ' '.join(str(item.create_sql(model, editor)).split()).replace('|', '\\|')
                lines.append(f'| `{model._meta.db_table}` | `{item.name}` | `{sql}` |')
    return '\n'.join(lines) + '\n'


class Command(BaseCommand):
    """Escreve os DERs conceitual e físico em DOT (Graphviz) e o SQL das restrições."""

    help = 'Gera o DER conceitual, o DER físico (Graphviz) e a lista de restrições.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default=DEFAULT_OUTPUT, help='Diretório de saída.')

    def handle(self, *args, **options):
        output = Path(options['output'])
        if not output.is_absolute():
            output = Path(settings.BASE_DIR) / output
        output.mkdir(parents=True, exist_ok=True)
        models = project_models()
        files = {
            'der-conceitual.dot': render_conceptual(),
            'der-fisico.dot': render_physical(models),
            'restricoes.md': render_restrictions(models),
        }
        for name, content in files.items():
            (output / name).write_text(content, encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Gerados em {options["output"]}: {", ".join(files)}.'))
