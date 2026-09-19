"""Verificação das classes dos templates contra a escala de tokens (D13).

Os valores aceitos vêm do ui/styles/app.css: tokens de cor, espaçamento, tamanho
de fonte, raio, sombra e largura, e os nomes das classes de componente. As
partes {{ }} e {% %} de um atributo class são descartadas, e os prefixos de
variante (sm:, hover:, focus-visible: e outros) são removidos antes da análise.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

from django.template.base import Lexer, TokenType

STYLES = Path(__file__).resolve().parent / 'styles' / 'app.css'

FLOATING_LAYER_CLASSES = frozenset({'modal', 'menu-list', 'tip'})

COLOR_PREFIXES = (
    'border-x', 'border-y', 'border-t', 'border-r', 'border-b', 'border-l', 'border-s', 'border-e',
    'bg', 'text', 'border', 'outline', 'ring', 'fill', 'stroke', 'decoration', 'divide', 'accent',
    'caret', 'placeholder', 'from', 'via', 'to',
)

NON_COLOR_VALUES = {
    'bg': {'fixed', 'local', 'scroll', 'none', 'cover', 'contain', 'auto', 'center', 'top', 'bottom',
           'left', 'right', 'repeat', 'no-repeat', 'repeat-x', 'repeat-y', 'clip-border', 'clip-padding',
           'clip-content', 'clip-text', 'origin-border', 'origin-padding', 'origin-content'},
    'text': {'left', 'center', 'right', 'justify', 'start', 'end', 'wrap', 'nowrap', 'balance', 'pretty',
             'ellipsis', 'clip'},
    'border': {'', 'solid', 'dashed', 'dotted', 'double', 'hidden', 'none', 'collapse', 'separate',
               'x', 'y', 't', 'r', 'b', 'l', 's', 'e'},
    'outline': {'', 'none', 'hidden', 'solid', 'dashed', 'dotted', 'double'},
    'ring': {'', 'inset'},
    'decoration': {'solid', 'double', 'dotted', 'dashed', 'wavy', 'auto', 'from-font', 'clone', 'slice'},
    'divide': {'x', 'y', 'x-reverse', 'y-reverse', 'solid', 'dashed', 'dotted', 'double', 'none'},
    'fill': {'none'},
    'stroke': {'none'},
    'accent': {'auto'},
    'caret': {'auto'},
}

COLOR_KEYWORDS = frozenset({'transparent', 'current', 'inherit'})

SPACING_PREFIXES = (
    'space-x', 'space-y', 'gap-x', 'gap-y', 'min-w', 'min-h', 'max-h', 'inset-x', 'inset-y',
    'scroll-m', 'scroll-p', 'translate-x', 'translate-y',
    'px', 'py', 'pt', 'pr', 'pb', 'pl', 'ps', 'pe', 'p',
    'mx', 'my', 'mt', 'mr', 'mb', 'ml', 'ms', 'me', 'm',
    'gap', 'w', 'h', 'size', 'inset', 'top', 'right', 'bottom', 'left', 'start', 'end', 'basis', 'indent',
)

SIZE_KEYWORDS = frozenset({
    'auto', 'full', 'screen', 'svw', 'lvw', 'dvw', 'svh', 'lvh', 'dvh', 'min', 'max', 'fit', 'px', 'lh',
    'reverse',
})

MAX_WIDTH_KEYWORDS = frozenset({'none', 'full', 'min', 'max', 'fit', 'px', 'screen'})

FRACTION = re.compile(r'\d+/\d+')
NUMBER = re.compile(r'\d+(\.\d+)?')


class Tokens:
    """Nomes aceitos por grupo, lidos do CSS."""

    def __init__(self, css):
        self.colors = set(re.findall(r'--color-([\w-]+):', css))
        self.spacing = set(re.findall(r'--spacing-([\w.]+):', css))
        self.text_sizes = set(re.findall(r'--text-([a-z0-9]+):', css))
        self.radius = set(re.findall(r'--radius-([\w-]+):', css))
        self.shadows = set(re.findall(r'--shadow-([\w-]+):', css))
        self.containers = set(re.findall(r'--container-([\w-]+):', css))
        self.components = set(re.findall(r'^\s*\.([a-z][a-z0-9-]*)', css, flags=re.MULTILINE))
        self.components |= set(re.findall(r'[\s,(]\.([a-z][a-z0-9-]*)', css))


def split_prefix(utility, prefixes):
    for prefix in prefixes:
        if utility == prefix:
            return prefix, ''
        if utility.startswith(prefix + '-'):
            return prefix, utility[len(prefix) + 1:]
    return None, None


def class_violation(css_class, tokens):
    """Motivo pelo qual a classe está fora da escala, ou None."""
    if '[' in css_class or ']' in css_class:
        return 'valor arbitrário'
    utility = css_class.rsplit(':', 1)[-1].lstrip('!').lstrip('-')
    if utility in tokens.components:
        return None
    if utility == 'shadow' or utility.startswith('shadow-'):
        value = utility[len('shadow-'):] if utility != 'shadow' else ''
        if value not in tokens.shadows | {'none'}:
            return 'sombra fora dos tokens'
        return None
    if utility == 'rounded' or utility.startswith('rounded-'):
        value = re.sub(r'^rounded-?(?:[setblr]{1,2}-|[setblr]{1,2}$)?', '', utility)
        if value not in tokens.radius | {'none', 'full'}:
            return 'raio fora dos tokens'
        return None
    if utility.startswith('max-w-'):
        value = utility[len('max-w-'):]
        if value not in tokens.containers | MAX_WIDTH_KEYWORDS:
            return 'largura máxima fora dos tokens'
        return None
    prefix, value = split_prefix(utility, SPACING_PREFIXES)
    if prefix is not None:
        if NUMBER.fullmatch(value):
            if value not in tokens.spacing:
                return 'passo fora da escala de espaçamento'
        elif value and not (FRACTION.fullmatch(value) or value in SIZE_KEYWORDS | tokens.containers):
            return None if prefix in {'start', 'end'} else 'tamanho fora da escala'
        return None
    prefix, value = split_prefix(utility, COLOR_PREFIXES)
    if prefix is not None:
        base = prefix.split('-')[0] if prefix.startswith('border') else prefix
        name = value.split('/')[0]
        if prefix == 'text' and name in tokens.text_sizes:
            return None
        if name in NON_COLOR_VALUES.get(base, set()) or NUMBER.fullmatch(name) or name.startswith('offset'):
            return None
        if name in tokens.colors | COLOR_KEYWORDS:
            return None
        return 'cor ou tamanho de fonte fora dos tokens'
    return None


class ClassParser(HTMLParser):
    """Coleta (linha, classes) e os atributos style de um HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.classes = []
        self.styles = []

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for name, value in attrs:
            if name == 'class' and value:
                self.classes.append((line, value.split()))
            elif name == 'style':
                self.styles.append((line, value or ''))


def template_markup(source):
    """Template com as tags e as variáveis trocadas por espaço, preservando as linhas."""
    parts = []
    for token in Lexer(source).tokenize():
        parts.append(token.contents if token.token_type == TokenType.TEXT else ' ')
    return ''.join(parts)


def find_class_violations(source, css=None):
    """Devolve (linha, trecho, motivo) de cada violação num template."""
    tokens = Tokens(css if css is not None else STYLES.read_text(encoding='utf-8'))
    parser = ClassParser()
    parser.feed(template_markup(source))
    parser.close()
    violations = [(line, f'style="{value}"', 'atributo style') for line, value in parser.styles]
    for line, classes in parser.classes:
        floating = FLOATING_LAYER_CLASSES & set(classes)
        for css_class in classes:
            reason = class_violation(css_class, tokens)
            if reason is None and css_class.rsplit(':', 1)[-1] == 'shadow-overlay' and not floating:
                reason = 'sombra fora de camada flutuante'
            if reason:
                violations.append((line, css_class, reason))
    return violations
