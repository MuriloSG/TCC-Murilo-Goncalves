from django.contrib.staticfiles import finders
from django.test import SimpleTestCase
from django.urls import reverse

from accounts import permissions
from accounts.tests.test_route_protection import PROTECTED_ROUTES
from tutorials.catalog import DEVICES, MODULES, NOTIFICATIONS, SCREENS, features, menu_items


class CatalogTests(SimpleTestCase):
    def test_funcionalidades_unicas_com_permissoes_do_catalogo(self):
        with self.subTest('identificador único'):
            slugs = [feature.slug for feature in features()]
            self.assertEqual(len(slugs), len(set(slugs)))
            self.assertTrue(all(module.features for module in MODULES))
        with self.subTest('permissões do catálogo'):
            for feature in features():
                codes = set(feature.permissions)
                for step in feature.steps:
                    codes |= set(step.permissions)
                with self.subTest(feature=feature.slug):
                    self.assertLessEqual(codes, permissions.ALL_PERMISSIONS)

    def test_passos_completos_com_imagens(self):
        with self.subTest('instrução e texto alternativo'):
            for feature in features():
                for number, step in enumerate(feature.steps, start=1):
                    with self.subTest(feature=feature.slug, step=number):
                        self.assertTrue(step.text.strip())
                        self.assertTrue(step.alt.strip())
                        self.assertTrue(step.marks)
        with self.subTest('imagens'):
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

    def test_telas_correspondem_ao_menu(self):
        with self.subTest('opção do menu'):
            prefixes = [item.prefix for item in menu_items()]
            for screen in SCREENS:
                with self.subTest(screen=screen.prefix):
                    if screen.url_name:
                        self.assertNotIn(screen.prefix, prefixes)
                        self.assertTrue(screen.label and reverse(screen.url_name))
                    else:
                        self.assertEqual(prefixes.count(screen.prefix), 1)
                    self.assertTrue(screen.features)
        with self.subTest('uma tela por funcionalidade'):
            placed = [feature.slug for screen in SCREENS for feature in screen.features]
            self.assertEqual(len(placed), len(set(placed)))
            self.assertEqual(set(placed), {feature.slug for feature in features()} - {NOTIFICATIONS.slug})
