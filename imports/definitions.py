"""Contrato das importações específicas (D4).

Cada app estende ImportDefinition e declara colunas, identificador, travamento,
execução de uma linha, verificações do arquivo e rótulos. O motor trata o plano
como dado e não interpreta o seu conteúdo.

Uma pendência é um ponto da linha que depende de uma decisão de usuário prevista pela
importação específica, e não um erro do arquivo: a linha com pendência não é aplicada, e a
importação sem erro com alguma pendência fica `PENDENTE` (D10 da Change
manipulacao-dos-espacos).
"""

from contextlib import nullcontext
from dataclasses import dataclass, field

from django.core.exceptions import NON_FIELD_ERRORS


@dataclass(frozen=True)
class Column:
    """Coluna declarada.

    A coluna é sempre exigida no cabeçalho. `required` diz respeito à célula: numa
    coluna opcional, a célula vazia é entregue à importação específica como texto
    vazio, em vez de virar erro da linha.
    """

    label: str
    required: bool = True


@dataclass(frozen=True)
class RowFilter:
    """Recorte das linhas oferecido na prévia, por um valor de uma coluna lógica.

    `columns` limita as colunas exibidas enquanto o recorte está escolhido, para que a
    tabela mostre só o que importa naquele recorte. Vazio mantém todas as colunas.
    """

    slug: str
    label: str
    column: str
    value: str
    columns: tuple = ()


@dataclass(frozen=True)
class RowError:
    column: str | None
    code: str
    message: str


@dataclass
class RowPlan:
    """Decisão sobre uma linha: ação, alvo, mudanças, avisos, pendências e erros (D8).

    `created` é a chave do registro criado pela linha. Fica fora da comparação e só
    é gravado na conclusão, porque a chave gerada na prévia desaparece no rollback.

    `pending` é a lista de pendências da linha, cada uma com o código e a chave canônica
    que a agrupa.
    """

    action: str | None = None
    target: str | None = None
    changes: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    created: str | None = None
    pending: list = field(default_factory=list)


class ImportDefinition:
    """Importação específica, declarada por atributos e operações sobre as linhas.

    `optional_sheets` são as abas da fonte em grade que a planilha pode não ter: a ausência
    delas não recusa o arquivo, e a leitura de cada uma, quando presente, é feita pela
    própria importação específica. O motor só as cita no texto de ajuda do envio (D4 da
    Change importar-usuarios-com-o-ensalamento).
    """

    kind = ''
    audit_resource = ''
    columns = ()
    identifier = ''
    columns_by_field = {}
    action_labels = {}
    field_labels = {}
    warning_labels = {}
    pending_labels = {}
    upload_fields = {}
    row_filters = ()
    optional_sheets = ()
    max_file_size = None
    max_rows = None
    has_template = True

    def source(self):
        """Fonte que lê o arquivo enviado. A leitura de CSV é o padrão.

        O import é local porque o leitor depende deste módulo, e não o contrário.
        """
        from imports.reader import CsvSource

        return CsvSource()

    def file_columns(self):
        """Colunas que vêm do arquivo, sem as colunas lógicas preenchidas pelo envio."""
        return tuple(column for column in self.columns if column.label not in self.upload_fields)

    def normalize_identifier(self, value):
        return value.strip()

    def execution(self, importation=None):
        """Contexto aberto em volta de todas as linhas e das verificações do arquivo.

        Recebe a importação em curso na atualização da prévia e na confirmação, e nenhuma
        na primeira prévia, para que a importação específica leia os dados que guarda
        junto da importação.
        """
        return nullcontext()

    def lock(self, rows, executor):
        """Trava o que a execução vai ler, antes da primeira linha."""

    def execute_row(self, values, executor):
        """Executa a linha com as operações reais do domínio e devolve o RowPlan."""
        raise NotImplementedError

    def clean_upload(self, values):
        """Validação conjunta dos campos próprios do envio, antes da leitura do arquivo.

        Recebe os valores limpos, pelo rótulo da coluna lógica, e lança `ValidationError`
        para recusar o envio. A regra fica no model; aqui ela só é chamada.
        """

    def upload_display(self, label, value):
        """Valor de um campo próprio como aparece no resumo; o gravado nas linhas não muda."""
        return value

    def check_file(self, executor):
        """Verificações do arquivo inteiro, depois de todas as linhas. Devolve RowError sem coluna."""
        return []

    def check_confirmation(self, importation, executor):
        """Verificação própria da confirmação, antes de reexecutar as linhas.

        Lança `ValidationError` com a mensagem para recusar a confirmação; a recusa não
        altera a importação nem nenhum dado.
        """

    def pending_label(self, code, key):
        """Texto de uma pendência da linha, a partir do rótulo declarado para o código."""
        return self.pending_labels.get(code, code).format(key=key)

    def audit_metadata(self, rows):
        """Informações adicionais próprias da importação nos registros de auditoria.

        Recebe as linhas, cada uma com os valores lidos, e devolve valores canônicos.
        """
        return {}


def errors_from_validation(error, columns_by_field):
    """Traduz uma ValidationError do model em erros de coluna, com as mensagens do próprio model.

    Campos fora do mapa e erros gerais ficam sem coluna.
    """
    if hasattr(error, 'error_dict'):
        groups = error.error_dict.items()
    else:
        groups = [(NON_FIELD_ERRORS, error.error_list)]
    errors = []
    for name, items in groups:
        column = columns_by_field.get(name)
        for item in items:
            for message in item.messages:
                errors.append(RowError(column, item.code or 'invalid', message))
    return errors
