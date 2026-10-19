from django.test import SimpleTestCase

from ui.class_rules import find_class_violations
from ui.tests.files import relative, template_files


class ProjectTemplateClassesTests(SimpleTestCase):
    def test_templates_usam_so_a_escala_de_tokens(self):
        files = list(template_files(('.html', '.svg')))
        self.assertTrue(any(path.name == 'user_list.html' for path in files))
        problems = [
            f'{relative(path)}:{line}: {excerpt} ({reason})'
            for path in files
            for line, excerpt, reason in find_class_violations(path.read_text(encoding='utf-8'))
        ]
        if problems:
            self.fail(f'{len(problems)} valor(es) solto(s) nos templates:\n' + '\n'.join(problems))


class ClassRulesTests(SimpleTestCase):
    def assertViolation(self, source, excerpt, line=1):
        violations = find_class_violations(source)
        self.assertIn(excerpt, [item[1] for item in violations], violations)
        self.assertIn(line, [item[0] for item in violations if item[1] == excerpt])

    def assertAllowed(self, source):
        self.assertEqual(find_class_violations(source), [])

    def test_valor_arbitrario_indica_linha_e_classe(self):
        self.assertViolation('<p>Texto</p>\n<div class="mt-[13px]"></div>', 'mt-[13px]', line=2)
        self.assertViolation('<div class="bg-[#fff]"></div>', 'bg-[#fff]')

    def test_cor_da_paleta_padrao(self):
        self.assertViolation('<div class="bg-blue-500"></div>', 'bg-blue-500')
        self.assertViolation('<div class="hover:text-red-600"></div>', 'hover:text-red-600')
        self.assertViolation('<div class="border-white"></div>', 'border-white')
        self.assertAllowed('<div class="bg-surface text-text-muted border-divider hover:bg-page"></div>')

    def test_atributo_style(self):
        self.assertViolation('<div style="color: red"></div>', 'style="color: red"')

    def test_passo_fora_da_escala(self):
        self.assertViolation('<div class="p-7"></div>', 'p-7')
        self.assertViolation('<div class="sm:gap-9"></div>', 'sm:gap-9')
        self.assertViolation('<div class="h-18"></div>', 'h-18')
        self.assertAllowed('<div class="p-4 gap-11 min-h-11 size-5 -mt-1 w-full mx-auto inset-0 w-1/2"></div>')

    def test_tamanho_de_fonte_raio_e_largura(self):
        self.assertViolation('<p class="text-4xl"></p>', 'text-4xl')
        self.assertViolation('<p class="rounded-2xl"></p>', 'rounded-2xl')
        self.assertViolation('<p class="max-w-7xl"></p>', 'max-w-7xl')
        self.assertAllowed('<p class="text-sm rounded-lg rounded-full max-w-modal text-center"></p>')

    def test_sombra_so_em_camada_flutuante(self):
        self.assertViolation('<button class="btn-primary shadow-overlay"></button>', 'shadow-overlay')
        self.assertViolation('<section class="card shadow-overlay"></section>', 'shadow-overlay')
        self.assertViolation('<div class="shadow-lg"></div>', 'shadow-lg')
        self.assertAllowed('<div class="menu-list shadow-overlay"></div>')

    def test_tags_do_django_no_atributo(self):
        self.assertAllowed('<a class="icon-btn{% if action.danger %} danger{% endif %} {{ extra }}"></a>')
        self.assertAllowed('<span class="badge tone-{{ tone }}"></span>')

    def test_componentes_sao_aceitos_pelo_nome(self):
        self.assertAllowed('<a class="btn-primary"></a><div class="field card data-table"></div>')
