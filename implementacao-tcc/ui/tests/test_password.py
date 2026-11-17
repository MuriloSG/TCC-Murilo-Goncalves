import re

from django.contrib.staticfiles import finders
from django.test import TestCase

from accounts.forms import LoginForm, PasswordResetKeyForm
from accounts.models import User
from config.testing import IsolatedCasesMixin
from system_settings.forms import SmtpForm


TOGGLE = re.compile(r'<button[^>]*data-password-toggle[^>]*>')


class PasswordToggleTests(IsolatedCasesMixin, TestCase):
    """Todo campo de senha ganha o botão de olho, oculto até o password.js ligá-lo."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superadmin(email='ana@ifnmg.edu.br', name='Ana Maria Souza', password='Senha-forte-123')

    def assert_toggles(self, html, ids):
        buttons = TOGGLE.findall(html)
        self.assertEqual([re.search(r'aria-controls="([^"]+)"', b).group(1) for b in buttons], ids)
        for button in buttons:
            for attr in ('type="button"', 'aria-pressed="false"', 'aria-label="Mostrar senha"', ' hidden'):
                self.assertIn(attr, button)

    def test_botao_de_olho(self):
        with self.case('login'):
            html = self.client.get('/contas/login/').content.decode()
            self.assert_toggles(html, ['id_password'])
            self.assertIn('<script src="/static/ui/js/password.js" defer></script>', html)
        with self.case('definir senha'):
            form = PasswordResetKeyForm(user=self.user, temp_key='chave')
            self.assert_toggles(str(form), ['id_password1', 'id_password2'])
        with self.case('smtp'):
            self.assert_toggles(str(SmtpForm()), ['id_password'])
        with self.case('campo que não é senha'):
            html = str(LoginForm()['login'].as_field_group())
            self.assertNotIn('data-password-toggle', html)
        with self.case('script'):
            self.assertIsNotNone(finders.find('ui/js/password.js'))


class PublicLoginLinkTests(TestCase):
    """As telas públicas têm, ao lado do botão de tema, um ícone que leva ao login."""

    def test_icone_de_login_no_cabecalho_publico(self):
        response = self.client.get('/')
        self.assertContains(
            response,
            '<a class="icon-btn public-login" href="/contas/login/" aria-label="Entrar no sistema">',
        )
