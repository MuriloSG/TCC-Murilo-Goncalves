"""Auxiliares do ensalamento."""

from accounts.models import normalize_username


def normalize_name(value):
    """Apara as bordas e reduz espaços internos repetidos, devolvendo None quando não sobra nada.

    É a mesma normalização do `User.username`, e não outra: o nome do docente precisa
    casar exatamente com o identificador usado fora da aplicação, e a caixa e os acentos
    são preservados (D4, D6 e D7 da Change importar-ensalamento-da-planilha).
    """
    return normalize_username(value)
