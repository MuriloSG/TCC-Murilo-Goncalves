"""Regras de texto da interface, espelhadas na seção 9 de docs/desenvolvimento/convencoes.md."""

import ast
import re
import unicodedata
from collections import namedtuple
from html.parser import HTMLParser

from django.template.base import Lexer, TokenType

Violation = namedtuple('Violation', ['excerpt', 'guidance'])
Fragment = namedtuple('Fragment', ['text', 'line', 'element'])

VARIABLE_MARKER = 'VAR'

MARKETING_WORDS = (
    r'\b(?:jornadas?|experiencias?|potencializ\w*|descubr\w*|descobr\w*|incrive(?:l|is)|simples'
    r'|facilmente|simplesmente|perfeit[oa]s?|poderos[oa]s?|intuitiv[oa]s?)\b'
)

FIRST_PERSON_PLURAL = (
    r'\b(?:enviaremos|recebemos|estamos|conseguimos|vamos|podemos|temos|precisamos'
    r'|sentimos|informamos|fizemos|pedimos|avisaremos|faremos)\b'
)

FORBIDDEN_PATTERNS = [
    (r'!', 'Sem ponto de exclamação.'),
    (r'\.\.\.|…', 'Sem reticências. Mostre o estado concreto.'),
    (r'[—–]', 'Sem travessão. Use vírgula, ponto ou um texto explícito como "Sem descrição".'),
    (r'\b(?:ops|oops|opa|eba|uau)\b', 'Sem interjeições.'),
    (r'\b(?:ola|bem[- ]vind[oa]s?|que bom)\b', 'Sem saudação.'),
    (
        r'\b(?:algo deu errado|parece que|ocorreu um erro)\b',
        'Mensagem vaga. Diga o que aconteceu e o que fazer.',
    ),
    (r'\bpor favor\b', 'Sem "por favor". Use o imperativo direto.'),
    (r'\bcom sucesso\b', 'Sem "com sucesso". Informe o fato no particípio.'),
    (MARKETING_WORDS, 'Sem linguagem de marketing.'),
    (r'\bvoces?\b', 'Sem "você". Use o imperativo nas instruções e a terceira pessoa nos fatos.'),
    (FIRST_PERSON_PLURAL, 'Sem primeira pessoa do plural. A interface não fala como pessoa.'),
]

EXACT_PATTERNS = [
    (r'(?i)(?<!\w)nós(?!\w)', 'Sem "nós". Use a terceira pessoa.'),
    (r'(?<!\w)E-Mail(?!\w)', 'Use "e-mail" (glossário, seção 9.4).'),
]

EMOJI_RANGES = [
    (0x1F000, 0x1FAFF),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0xFE0F, 0xFE0F),
    (0x200D, 0x200D),
]

GLOSSARY = [
    (r'\bbloque\w*', 'desativar; situação Inativo'),
    (r'\bsuspen[ds]\w*', 'desativar; situação Inativo'),
    (r'\binativ(?:ar|ad[oa]s?|ou|e|em|acao|acoes)\b', 'desativar'),
    (r'\breprov\w*', 'rejeitar, rejeitada'),
    (r'\bneg(?:ar|ad[oa]s?|ou|ue|uem)\b', 'rejeitar, rejeitada'),
    (r'\bdesmarc\w*', 'cancelar, cancelada'),
    (r'\banul(?:ar|ad[oa]s?|ou|e|em|a|am)\b', 'cancelar, cancelada'),
    (r'\bapag(?:ar|ad[oa]s?|ou|ue|uem|a|am)\b', 'excluir'),
    (r'\bdelet\w*', 'excluir'),
    (r'\bremov\w*|\bremoc(?:ao|oes)\b', 'excluir'),
    (r'\b(?:des)?log(?:ar|ad[oa]s?|ou|ue|uem)\b', 'entrar, sair'),
    (r'\blogout\b', 'sair'),
    (r'\bemail\b', 'e-mail'),
    (r'\b(?:recursos?|ambientes?|ite(?:m|ns))\b', 'espaço, laboratório ou sala'),
    (r'\bpedidos?\b', 'solicitação de agendamento'),
    (r'\bagendamentos? pendentes?\b', 'solicitação de agendamento'),
    (r'\bagendamentos? confirmad[oa]s?\b', 'agendamento'),
    (r'\breservas?\b', 'agendamento'),
    (r'\b(?:livres?|vag[oa]s?|indisponive(?:l|is))\b', 'disponível, ocupado'),
    (r'\b(?:em analise|aguardando)\b', 'pendente'),
    (r'\bprofessor(?:es|as?)?\b', 'docente'),
    (r'\b(?:pap(?:el|eis)|roles?|grupos?)\b', 'perfil'),
]

PROPER_NOUNS = (
    'Norte de Minas Gerais',
    'Instituto Federal',
    'Campus Salinas',
    'Salinas',
    'IFNMG',
)

CAPITALIZED_ELEMENTS = frozenset({
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'title', 'button', 'a', 'th', 'label', 'legend', 'dt',
})

TITLE_ELEMENTS = frozenset({'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'title'})

PERMISSION_CODE = re.compile(r'\b[A-Z]+(?:_[A-Z]+)*\.[A-Z]+(?:_[A-Z]+)*\b')

WORD = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*")
SENTENCE_BREAK = re.compile(r'(?<=[.?!:;·|(])\s*')


def fold(text):
    """Remove acentos e caixa mantendo o comprimento, para as posições valerem no texto original."""
    folded = []
    for char in text:
        base = ''.join(c for c in unicodedata.normalize('NFD', char) if not unicodedata.combining(c))
        base = base[:1] or char
        lower = base.lower()
        folded.append(lower if len(lower) == 1 else base)
    return ''.join(folded)


def mask_codes(folded, text):
    """Troca por espaços, no texto dobrado, os códigos de permissão do texto original."""
    for match in PERMISSION_CODE.finditer(text):
        start, end = match.span()
        folded = folded[:start] + ' ' * (end - start) + folded[end:]
    return folded


def is_emoji(char):
    code = ord(char)
    return any(start <= code <= end for start, end in EMOJI_RANGES)


def capitalization_violations(text):
    """Palavras com inicial maiúscula fora do início da frase, exceto nomes próprios e siglas."""
    for noun in PROPER_NOUNS:
        text = text.replace(noun, VARIABLE_MARKER)
    violations = []
    for sentence in SENTENCE_BREAK.split(text):
        for word in WORD.findall(sentence)[1:]:
            if word[0].isupper() and not (len(word) >= 2 and word.isupper()):
                violations.append(Violation(
                    word,
                    'Maiúscula só no início da frase, em nomes próprios e em siglas.',
                ))
    return violations


def find_violations(text, element=None):
    """Violações das regras de texto num trecho exibido."""
    violations = []
    folded = mask_codes(fold(text), text)
    for pattern, guidance in FORBIDDEN_PATTERNS:
        for match in re.finditer(pattern, folded):
            violations.append(Violation(text[match.start():match.end()], guidance))
    for pattern, guidance in EXACT_PATTERNS:
        for match in re.finditer(pattern, text):
            violations.append(Violation(match.group(), guidance))
    for pattern, term in GLOSSARY:
        for match in re.finditer(pattern, folded):
            violations.append(Violation(
                text[match.start():match.end()],
                f'Use "{term}" (glossário, seção 9.4).',
            ))
    for char in text:
        if is_emoji(char):
            violations.append(Violation(char, 'Sem emoji. Ícones só da biblioteca Lucide.'))
    if element in TITLE_ELEMENTS and re.search(r':\s', text):
        violations.append(Violation(text, 'Título sem dois-pontos seguidos de complemento.'))
    if element in CAPITALIZED_ELEMENTS:
        violations.extend(capitalization_violations(text))
    return violations


def visible_template_source(source):
    """Template só com o que chega ao usuário, preservando as linhas."""
    tokens = Lexer(source).tokenize()
    extends = any(
        token.token_type == TokenType.BLOCK and token.contents.split()[:1] == ['extends']
        for token in tokens
    )
    parts = []
    blocks = []
    in_comment = False
    for token in tokens:
        if token.token_type == TokenType.BLOCK:
            name, *args = token.contents.split() or ['']
            if name == 'comment':
                in_comment = True
            elif name == 'endcomment':
                in_comment = False
            elif name == 'block':
                blocks.append(args[0] if args else '')
                if extends and blocks[-1] == 'title':
                    parts.append('<title>')
            elif name == 'endblock' and blocks:
                if extends and blocks.pop() == 'title':
                    parts.append('</title>')
        elif in_comment:
            parts.append('\n' * token.contents.count('\n'))
        elif token.token_type == TokenType.TEXT:
            parts.append(token.contents)
        elif token.token_type == TokenType.VAR:
            parts.append(VARIABLE_MARKER)
    return ''.join(parts)


class VisibleTextParser(HTMLParser):
    """Coleta o texto visível e os atributos exibidos como Fragment(text, line, element)."""

    VOID_ELEMENTS = frozenset({
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source',
        'track', 'wbr',
    })
    HIDDEN_ELEMENTS = frozenset({'script', 'style'})
    TEXT_ATTRIBUTES = ('placeholder', 'title', 'alt', 'aria-label')

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments = []
        self.stack = []
        self.buffers = []

    def current_element(self, tag=None):
        for name in ([tag] if tag else []) + self.stack[::-1]:
            if name in CAPITALIZED_ELEMENTS:
                return name
        return tag or (self.stack[-1] if self.stack else None)

    def add(self, text, line, element):
        text = ' '.join(text.split())
        if text:
            self.fragments.append(Fragment(text, line, element))

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        attributes = dict(attrs)
        element = self.current_element(tag)
        for name in self.TEXT_ATTRIBUTES:
            if attributes.get(name):
                self.add(attributes[name], line, element)
        if attributes.get('data-label'):
            self.add(attributes['data-label'], line, 'th')
        if tag == 'input' and attributes.get('type') in ('submit', 'button') and attributes.get('value'):
            self.add(attributes['value'], line, 'button')
        if tag in self.VOID_ELEMENTS:
            return
        self.stack.append(tag)
        if tag in CAPITALIZED_ELEMENTS:
            self.buffers.append([tag, None, []])

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return
        while self.stack:
            closed = self.stack.pop()
            if closed in CAPITALIZED_ELEMENTS:
                self.flush()
            if closed == tag:
                break

    def flush(self):
        element, line, parts = self.buffers.pop()
        self.add(''.join(parts), line, element)

    def handle_data(self, data):
        if self.HIDDEN_ELEMENTS.intersection(self.stack) or not data.strip():
            return
        line = self.getpos()[0] + data[:len(data) - len(data.lstrip())].count('\n')
        if self.buffers:
            buffer = self.buffers[-1]
            if buffer[1] is None:
                buffer[1] = line
            buffer[2].append(data)
        else:
            self.add(data, line, self.stack[-1] if self.stack else None)

    def close(self):
        super().close()
        while self.buffers:
            self.flush()


def html_fragments(html):
    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    return parser.fragments


def template_fragments(source, name):
    """Trechos visíveis de um template. Nos .txt, cada linha inteira é visível."""
    visible = visible_template_source(source)
    if name.endswith('.txt'):
        return [
            Fragment(' '.join(line.split()), number, None)
            for number, line in enumerate(visible.splitlines(), start=1)
            if line.strip()
        ]
    return html_fragments(visible)


def is_logger_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == 'logger'
    )


def python_fragments(source):
    """Strings literais com espaço, sem docstrings nem argumentos de logger."""
    tree = ast.parse(source)
    skipped = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                skipped.add(id(first.value))
        if is_logger_call(node):
            for argument in node.args + [keyword.value for keyword in node.keywords]:
                skipped.update(id(child) for child in ast.walk(argument))
        if isinstance(node, ast.JoinedStr):
            skipped.update(id(child) for child in ast.walk(node) if child is not node)
    fragments = []
    for node in ast.walk(tree):
        if id(node) in skipped:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
        elif isinstance(node, ast.JoinedStr):
            text = ''.join(
                value.value if isinstance(value, ast.Constant) else VARIABLE_MARKER
                for value in node.values
            )
        else:
            continue
        if ' ' in text:
            fragments.append(Fragment(text, node.lineno, None))
    return fragments
