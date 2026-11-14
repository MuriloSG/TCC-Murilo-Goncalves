from html import escape
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

DEFAULT_OUTPUT = 'docs/diagramas'

PROJECT_APPS = ['accounts', 'schedule', 'bookings', 'imports', 'notices', 'audit', 'outbox', 'system_settings']

IDENTIFIER_COLOR = '#3b4fa8'

CONCEPTUAL_HEADER = '''  layout=neato; overlap=true; splines=line; bgcolor=white; pad=0.4;
  fontname="Helvetica"; fontsize=10; labelloc=b; labeljust=l;
  node [fontname="Helvetica", fontsize=10];
  edge [color="#222222"];'''

PHYSICAL_HEADER = '''  layout=dot; rankdir=LR; nodesep=0.3; ranksep=1.2; splines=polyline; bgcolor=white; pad=0.4;
  fontname="Helvetica"; fontsize=10; labelloc=b; labeljust=l;
  node [fontname="Helvetica", fontsize=10];
  edge [fontname="Helvetica", fontsize=9, color="#222222", labeldistance=1.8, labelangle=30];'''

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
    'Ocorrencia': (3, 4), 'Espaco': (3, 1), 'OutroNome': (3, 0), 'Solicitacao': (3, 3),
    'Agendamento': (4, 2), 'Decisao': (4, 1),
    'Usuario': (4, 4), 'Perfil': (5, 4), 'Permissao': (5, 3), 'Auditoria': (5, 5),
    'Importacao': (5, 2), 'Linha': (5, 1), 'Aviso': (3, 5), 'Notificacao': (4, 5),
}

# Geometria em polegadas: tamanho da célula, retângulo da entidade, losango e rótulo de cardinalidade.
CELL_WIDTH, CELL_HEIGHT = 6.2, 3.4
BOX_WIDTH = 140 / 72
ATTRIBUTE_ROW = 13 / 72
CHAR_WIDTH = 6.2 / 72
DIAMOND_WIDTH, DIAMOND_HEIGHT = 1.5, 0.55
LABEL_WIDTH, LABEL_HEIGHT = 0.4, 0.17
PARALLEL_OFFSET = 0.7  # afastamento do losango quando duas entidades têm mais de um relacionamento

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
            f'  {self.key} [shape=plain, pos="{center:.3f},{self.y:.3f}!", '
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
        if total > 1:  # relacionamentos paralelos: afasta o losango e recalcula as pontas na direção dele
            length = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
            shift = (pairs[:index].count(pairs[index]) - (total - 1) / 2) * 2 * PARALLEL_OFFSET
            x, y = x - (end[1] - start[1]) / length * shift, y + (end[0] - start[0]) / length * shift
            start, end = a.exit_point(x, y), b.exit_point(x, y)
        relationships.append((index, verb, (x, y), [(left, start, left_cardinality), (right, end, right_cardinality)]))
    return entities, relationships


def place_cardinalities(entities, relationships):
    """Cardinalidade junto da ponta de cada linha, na primeira posição que não encosta em nada."""
    obstacles = [entity.rect() for entity in entities.values()]
    obstacles += [centered_rect(x, y, DIAMOND_WIDTH * 0.8, DIAMOND_HEIGHT * 0.8) for _, _, (x, y), _ in relationships]
    segments = [(point, diamond) for _, _, diamond, ends in relationships for _, point, _ in ends]
    placed = []
    for _, _, diamond, ends in relationships:
        for _, point, cardinality in ends:
            dx, dy = diamond[0] - point[0], diamond[1] - point[1]
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

            chosen = min(candidates, key=conflicts)  # a primeira livre; sem nenhuma livre, a que menos encosta
            placed.append(centered_rect(*chosen, LABEL_WIDTH, LABEL_HEIGHT))
            yield chosen, cardinality


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
            f'  r{index} [shape=diamond, label="{verb}", pos="{x:.3f},{y:.3f}!", fontsize=9, '
            f'width={DIAMOND_WIDTH}, height={DIAMOND_HEIGHT}, fixedsize=true];'
        )
        for side, (_, (px, py), _) in zip('ab', ends):
            lines.append(f'  p{index}{side} [shape=point, width=0.01, height=0.01, style=invis, pos="{px:.3f},{py:.3f}!"];')
        lines.append(f'  p{index}a -- r{index} -- p{index}b;')
    labels = place_cardinalities(entities, relationships)
    for number, ((x, y), cardinality) in enumerate(labels):
        lines.append(f'  c{number} [shape=plain, label="{cardinality}", fontsize=9, pos="{x:.3f},{y:.3f}!"];')
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


def column_row(field):
    """Coluna: marcador de chave, nome, tipo e se aceita nulo."""
    if field.primary_key:
        marker = f'<FONT COLOR="{IDENTIFIER_COLOR}">●</FONT>'
    elif field.is_relation:
        marker = '◆'
    else:
        marker = '○'
    keys = ', '.join(
        key for key, present in [
            ('PK', field.primary_key), ('FK', field.is_relation), ('UK', field.unique and not field.primary_key),
        ] if present
    )
    name = f'<B>{escape(field.column)}</B>' if field.primary_key else escape(field.column)
    nullable = 'NULL' if field.null else 'NOT NULL'
    return (
        f'<TR><TD ALIGN="LEFT">{marker} {name}</TD><TD ALIGN="LEFT">{escape(column_type(field))}</TD>'
        f'<TD ALIGN="LEFT">{nullable}</TD><TD ALIGN="LEFT">{keys}</TD></TR>'
    )


def table_node(model):
    """Tabela no estilo do modelo lógico do brModelo."""
    rows = ''.join(column_row(field) for field in model._meta.local_fields)
    title = f'<TR><TD COLSPAN="4" BORDER="1" SIDES="B"><B>{model._meta.db_table}</B></TD></TR>'
    table = f'<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">{title}{rows}</TABLE>'
    return f'  {model._meta.db_table} [shape=plaintext, label=<{table}>];'


def relationship_edge(model, field):
    """Linha da FK com a cardinalidade (mín,máx) de cada lado."""
    child_side = '(0,1)' if field.one_to_one or field.unique else '(0,n)'
    parent_side = '(0,1)' if field.null else '(1,1)'
    return (
        f'  {model._meta.db_table} -- {field.related_model._meta.db_table} '
        f'[taillabel="{child_side}", headlabel="{parent_side}"];'
    )


def render_physical(models):
    """DOT do DER físico com todas as tabelas, colunas, tipos e chaves."""
    lines = ['graph fisico {', PHYSICAL_HEADER]
    lines.append('  label="● chave primária   ◆ chave estrangeira   ○ coluna\\l";')
    lines.extend(table_node(model) for model in models)
    lines.extend(relationship_edge(model, field) for model in models for field in foreign_keys(model))
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
