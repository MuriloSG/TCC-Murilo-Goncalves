"""Paginação das listas (D1 da Change paginar-listas).

get_page devolve a primeira página para valores inválidos e a última para números
além do fim, para que um link salvo nunca vire erro depois que a lista mudar.
"""

from django.core.paginator import Paginator

PAGE_PARAMETER = 'pagina'
PAGE_SIZE = 20
ROWS_PAGE_SIZE = 50


def paginate(request, items, per_page=PAGE_SIZE):
    return Paginator(items, per_page).get_page(request.GET.get(PAGE_PARAMETER))
