"""Sugestão de nomes de espaço parecidos (D6 da Change manipulacao-dos-espacos).

A semelhança serve só para montar as perguntas da importação e nunca associa, cria,
renomeia ou une espaços. A regra é heurística e pode ser ajustada, desde que os casos reais
dos testes continuem valendo: a regra forte junta os nomes que ficam iguais sem espaços,
pontos, hífens, acentos, caixa e zeros à esquerda (`HV5` e `HV 5`, `Sala 01` e `Sala 1`), e a
regra fraca junta o nome que é outro acrescido de um número ou de um romano no fim
(`Lab. Química` e `Lab. Química I`).
"""

import re
import unicodedata

SEPARATORS = re.compile(r'[\s.\-]+')
NUMBERS = re.compile(r'\d+')
ROMAN_NUMERALS = frozenset({'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x'})


def plain(value):
    """Texto sem acentos, sem caixa e com os números sem zeros à esquerda."""
    decomposed = unicodedata.normalize('NFKD', value.casefold())
    without_accents = ''.join(char for char in decomposed if not unicodedata.combining(char))
    return NUMBERS.sub(lambda found: str(int(found.group())), without_accents)


def strong_key(value):
    return SEPARATORS.sub('', plain(value))


def tokens(value):
    return [token for token in SEPARATORS.split(plain(value)) if token]


def is_numeral(token):
    return token.isdigit() or token in ROMAN_NUMERALS


def extends(shorter, longer):
    """Diz se o nome maior é o menor acrescido, no fim, de um número ou de um romano."""
    return len(longer) == len(shorter) + 1 and longer[:-1] == shorter and is_numeral(longer[-1])


def are_similar(first, second):
    if first.casefold() == second.casefold():
        return False
    if strong_key(first) == strong_key(second):
        return True
    first_tokens, second_tokens = tokens(first), tokens(second)
    return extends(first_tokens, second_tokens) or extends(second_tokens, first_tokens)


def similar_names(name, known):
    """Nomes conhecidos parecidos com o nome, na ordem dada e sem repetição."""
    found, seen = [], set()
    for candidate in known:
        key = candidate.casefold()
        if key in seen or not are_similar(name, candidate):
            continue
        seen.add(key)
        found.append(candidate)
    return found
