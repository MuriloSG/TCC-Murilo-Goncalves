from django.contrib.staticfiles import finders
from django.test import SimpleTestCase
from django.urls import reverse

from accounts import permissions
from accounts.tests.test_route_protection import PROTECTED_ROUTES
from tutorials.catalog import DEVICES, MODULES, NOTIFICATIONS, SCREENS, features, menu_items


class CatalogTests(SimpleTestCase):
    def test_funcionalidades_com_identificador_unico(self):
        slugs = [feature.slug for feature in features()]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertTrue(all(module.features for module in MODULES))

    def test_permissoes_existem_no_catalogo(self):
        for feature in features():
            codes = set(feature.permissions)
            for step in feature.steps:
                codes |= set(step.permissions)
            with self.subTest(feature=feature.slug):
                self.assertLessEqual(codes, permissions.ALL_PERMISSIONS)

    def test_todo_passo_tem_instrucao_texto_alternativo_e_marcadores(self):
        for feature in features():
            for number, step in enumerate(feature.steps, start=1):
                with self.subTest(feature=feature.slug, step=number):
                    self.assertTrue(step.text.strip())
                    self.assertTrue(step.alt.strip())
                    self.assertTrue(step.marks)

    def test_imagens_do_computador_e_do_celular_existem(self):
        for feature in features():
            for number in range(1, len(feature.steps) + 1):
                for device in DEVICES:
                    with self.subTest(image=feature.image(number, device)):
                        self.assertIsNotNone(finders.find(feature.image(number, device)))

    def test_botao_do_fim_abre_tela_coberta_pelas_permissoes(self):
        for feature in [feature for feature in features() if feature.screen]:
            with self.subTest(feature=feature.slug):
                reverse(feature.screen)
                self.assertTrue(feature.screen_label)
                required = PROTECTED_ROUTES[feature.screen]
                self.assertTrue(required is None or required in feature.permissions)

    def test_cada_tela_corresponde_a_uma_opcao_do_menu(self):
        prefixes = [item.prefix for item in menu_items()]
        for screen in SCREENS:
            with self.subTest(screen=screen.prefix):
                self.assertEqual(prefixes.count(screen.prefix), 1)
                self.assertTrue(screen.features)

    def test_cada_funcionalidade_aparece_numa_tela_so_menos_o_uso_geral(self):
        placed = [feature.slug for screen in SCREENS for feature in screen.features]
        self.assertEqual(len(placed), len(set(placed)))
        self.assertEqual(set(placed), {feature.slug for feature in features()} - {NOTIFICATIONS.slug})
