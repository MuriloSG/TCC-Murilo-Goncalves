from html import escape
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

DEFAULT_OUTPUT = 'docs/diagramas'

PROJECT_APPS = ['accounts', 'schedule', 'bookings', 'imports', 'notices', 'audit', 'outbox', 'system_settings']

IDENTIFIER_COLOR = '#3b4fa8'

CONCEPTUAL_HEADER = '''  layout=neato; mode=major; start=5; overlap=prism; sep="+10"; splines=line; bgcolor=white; pad=0.4;
  fontname="Helvetica"; fontsize=10; labelloc=b; labeljust=l;
  node [fontname="Helvetica", fontsize=10];
  edge [fontname="Helvetica", fontsize=9, color="#222222", len=1.4, labeldistance=1.8, labelangle=30];'''

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
    return f'<TR><TD ALIGN="LEFT" CELLPADDING="0">─<FONT COLOR="{color}">{circle}</FONT> {label}</TD></TR>'


def entity_node(key, name, attributes, footnote):
    """Entidade: retângulo com o nome e, ao lado, os atributos ou o asterisco da nota de rodapé."""
    box = f'<TD PORT="e" BORDER="1" CELLPADDING="12" WIDTH="110"><B>{escape(name)}</B></TD>'
    if footnote:
        side = '<TD VALIGN="TOP">*</TD>'
    else:
        rows = ''.join(attribute_row(attribute, attribute == 'id') for attribute in attributes)
        side = (
            '<TD><TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0"><TR><TD BORDER="1" SIDES="L">'
            f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="1">{rows}</TABLE></TD></TR></TABLE></TD>'
        )
    return f'  {key} [shape=plaintext, label=<<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0"><TR>{box}{side}</TR></TABLE>>];'


def render_conceptual():
    """DOT do DER conceitual na notação de Peter Chen, como no brModelo."""
    lines = ['graph conceitual {', CONCEPTUAL_HEADER]
    for key, (name, attributes) in CONCEPTUAL_ENTITIES.items():
        lines.append(entity_node(key, name, attributes, key in CONCEPTUAL_FOOTNOTES))
    for index, (left, left_cardinality, verb, right, right_cardinality) in enumerate(CONCEPTUAL_RELATIONSHIPS):
        lines.append(f'  r{index} [shape=diamond, label="{verb}", fontsize=9, height=0.5, width=1.1, margin=0.02];')
        lines.append(f'  {left}:e -- r{index} [taillabel="{left_cardinality}"]; r{index} -- {right}:e [headlabel="{right_cardinality}"];')
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
