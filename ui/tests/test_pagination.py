from django.contrib.auth.models import Group
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from ui.pagination import paginate


def render_pagination(path, total, per_page=20, **extra):
    Group.objects.bulk_create(Group(name=f'Grupo {index:03d}') for index in range(total))
    request = RequestFactory().get(path)
    page = paginate(request, Group.objects.order_by('name'), per_page)
    template = Template(
        '{% include "ui/components/pagination.html" with noun="grupo" noun_plural="grupos" hx_target=hx_target %}'
    )
    return page, template.render(Context({'request': request, 'page': page, **extra}))


class PaginateTests(TestCase):
    def test_first_page_by_default(self):
        page, content = render_pagination('/lista/', 57)
        self.assertEqual((page.number, len(page.object_list)), (1, 20))
        self.assertIn('Exibindo <strong>1</strong> a <strong>20</strong> de <strong>57</strong> grupos', content)
        self.assertIn('Página 1 de 3', content)
        self.assertIn('<span class="btn-secondary" aria-disabled="true">Anterior</span>', content)
        self.assertIn('href="/lista/?pagina=2" rel="next"', content)

    def test_last_page(self):
        page, content = render_pagination('/lista/?pagina=3', 57)
        self.assertEqual(len(page.object_list), 17)
        self.assertIn('Exibindo <strong>41</strong> a <strong>57</strong>', content)
        self.assertIn('<span class="btn-secondary" aria-disabled="true">Próxima</span>', content)
        self.assertIn('href="/lista/?pagina=2" rel="prev"', content)

    def test_invalid_and_out_of_range_pages(self):
        page, _ = render_pagination('/lista/?pagina=abc', 57)
        self.assertEqual(page.number, 1)
        Group.objects.all().delete()
        page, _ = render_pagination('/lista/?pagina=99', 57)
        self.assertEqual(page.number, 3)

    def test_first_page_link_has_no_page_parameter_and_keeps_others(self):
        _, content = render_pagination('/lista/?linhas=erros&pagina=2', 57)
        self.assertIn('href="/lista/?linhas=erros" rel="prev"', content)
        self.assertIn('href="/lista/?linhas=erros&amp;pagina=3" rel="next"', content)

    def test_single_page_shows_only_the_range(self):
        _, content = render_pagination('/lista/', 5)
        self.assertIn('Exibindo <strong>1</strong> a <strong>5</strong> de <strong>5</strong> grupos', content)
        self.assertNotIn('Página', content)

    def test_singular_and_empty(self):
        _, content = render_pagination('/lista/', 1)
        self.assertIn('de <strong>1</strong> grupo</p>', content)
        Group.objects.all().delete()
        _, content = render_pagination('/lista/', 0)
        self.assertEqual(content.strip(), '')

    def test_htmx_target(self):
        _, content = render_pagination('/lista/', 57, hx_target='tabela')
        self.assertIn('hx-get="/lista/?pagina=2" hx-target="#tabela" hx-swap="innerHTML show:top" hx-push-url="true"', content)
