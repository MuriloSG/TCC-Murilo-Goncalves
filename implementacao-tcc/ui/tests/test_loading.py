from django.test import TestCase

from accounts.models import User


class GlobalLoadingTests(TestCase):
    """O carregamento global existe uma única vez, oculto, em toda página que estende o base.html."""

    DIALOG = '<dialog id="carregamento" class="loading" aria-labelledby="carregamento-texto">'
    SCRIPT = '<script src="/static/ui/js/loading.js" defer></script>'

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superadmin(email='ana@ifnmg.edu.br', name='Ana Maria Souza', password='Senha-forte-123')

    def assert_single_hidden_loading(self, response):
        content = response.content.decode()
        self.assertEqual(content.count('id="carregamento"'), 1)
        self.assertIn(self.DIALOG, content)
        self.assertNotRegex(content, r'<dialog id="carregamento"[^>]*\bopen\b')
        self.assertIn('<span class="spinner" aria-hidden="true"></span>', content)
        self.assertIn(self.SCRIPT, content)

    def test_pagina_autenticada(self):
        self.client.force_login(self.admin)
        self.assert_single_hidden_loading(self.client.get('/inicio/', follow=True))

    def test_login_e_calendario_publico(self):
        for url in ('/contas/login/', '/'):
            with self.subTest(url=url):
                self.assert_single_hidden_loading(self.client.get(url))
