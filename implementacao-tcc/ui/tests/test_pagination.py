from django.contrib.auth.models import Group
from django.template import Context, Template
from django.test import RequestFactory, TestCase
from config.testing import IsolatedCasesMixin

from ui.pagination import paginate


def render_pagination(path, total, per_page=20, **extra):
    Group.objects.bulk_create(Group(name=f'Grupo {index:03d}') for index in range(total))
    request = RequestFactory().get(path)
    page = paginate(request, Group.objects.order_by('name'), per_page)
    template = Template(
        '{% include "ui/components/pagination.html" with noun="grupo" noun_plural="grupos" hx_target=hx_target %}'
    )
    return page, template.render(Context({'request': request, 'page': page, **extra}))


class PaginateTests(IsolatedCasesMixin, TestCase):
    def test_page_choice(self):
        with self.case('primeira por padrão'):
            page, content = render_pagination('/lista/', 57)
            self.assertEqual((page.number, len(page.object_list)), (1, 20))
            self.assertIn('Exibindo <strong>1</strong> a <strong>20</strong> de <strong>57</strong> grupos', content)
            self.assertIn('Página 1 de 3', content)
            self.assertIn('<span class="btn-secondary" aria-disabled="true">Anterior</span>', content)
            self.assertIn('href="/lista/?pagina=2" rel="next"', content)
        with self.case('última'):
            page, content = render_pagination('/lista/?pagina=3', 57)
            self.assertEqual(len(page.object_list), 17)
            self.assertIn('Exibindo <strong>41</strong> a <strong>57</strong>', content)
            self.assertIn('<span class="btn-secondary" aria-disabled="true">Próxima</span>', content)
            self.assertIn('href="/lista/?pagina=2" rel="prev"', content)
        with self.case('inválida ou fora do intervalo'):
            page, _ = render_pagination('/lista/?pagina=abc', 57)
            self.assertEqual(page.number, 1)
            Group.objects.all().delete()
            page, _ = render_pagination('/lista/?pagina=99', 57)
            self.assertEqual(page.number, 3)

    def test_links_keep_the_query_and_the_htmx_target(self):
        with self.case('link da primeira página'):
            _, content = render_pagination('/lista/?linhas=erros&pagina=2', 57)
            self.assertIn('href="/lista/?linhas=erros" rel="prev"', content)
            self.assertIn('href="/lista/?linhas=erros&amp;pagina=3" rel="next"', content)
        with self.case('alvo do htmx'):
            _, content = render_pagination('/lista/', 57, hx_target='tabela')
            self.assertIn('hx-get="/lista/?pagina=2" hx-target="#tabela" hx-swap="innerHTML show:top" hx-push-url="true"', content)

    def test_single_page_singular_and_empty(self):
        with self.case('página única'):
            _, content = render_pagination('/lista/', 5)
            self.assertIn('Exibindo <strong>1</strong> a <strong>5</strong> de <strong>5</strong> grupos', content)
            self.assertNotIn('Página', content)
        with self.case('singular e vazio'):
            _, content = render_pagination('/lista/', 1)
            self.assertIn('de <strong>1</strong> grupo</p>', content)
            Group.objects.all().delete()
            _, content = render_pagination('/lista/', 0)
            self.assertEqual(content.strip(), '')
