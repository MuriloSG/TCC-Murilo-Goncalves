"""Paginação que nunca falha num link salvo, caindo na primeira ou na última página."""

from django.core.paginator import Paginator

PAGE_PARAMETER = 'pagina'
PAGE_SIZE = 5
ROWS_PAGE_SIZE = 20
OPTIONS_PAGE_SIZE = 10


def paginate(request, items, per_page=PAGE_SIZE):
    return Paginator(items, per_page).get_page(request.GET.get(PAGE_PARAMETER))
