import re

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase

from accounts.models import Role, User

PASSWORD = 'Senha-forte-123'


def reset_link(message):
    return re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', message.body).group(1)


class PasswordFlowTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')

    def setUp(self):
        cache.clear()
        self.user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=self.teacher)

    def request_link(self, email='maria@ifnmg.edu.br'):
        response = self.client.post('/contas/senha/recuperar/', {'email': email})
        self.assertRedirects(response, '/contas/senha/recuperar/enviado/', fetch_redirect_response=False)

    def set_password(self, link, password=PASSWORD, client=None):
        client = client or Client()
        response = client.get(link)
        if response.status_code != 302:
            return response
        return client.post(response['Location'], {'password1': password, 'password2': password})

    def login(self, email='maria@ifnmg.edu.br', password=PASSWORD):
        client = Client()
        client.post('/contas/login/', {'login': email, 'password': password})
        return '_auth_user_id' in client.session


class UnusablePasswordTests(PasswordFlowTestCase):
    def test_registered_user_does_not_authenticate_before_defining_the_password(self):
        self.assertFalse(self.user.has_usable_password())
        for password in ['', '!', self.user.password, PASSWORD]:
            with self.subTest(password=password):
                self.assertFalse(self.login(password=password))

    def test_registered_user_defines_the_password_through_the_link(self):
        self.request_link()
        response = self.set_password(reset_link(mail.outbox[0]))
        self.assertRedirects(response, '/contas/senha/redefinir/concluido/', fetch_redirect_response=False)
        self.assertTrue(self.login())


class InactiveUserTests(PasswordFlowTestCase):
    def test_inactive_user_receives_no_email(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.request_link()
        self.assertEqual(mail.outbox, [])

    def test_link_issued_before_deactivation_does_not_reset_the_password(self):
        self.request_link()
        link = reset_link(mail.outbox[0])
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        response = self.set_password(link)

        self.assertTrue(response.context['token_fail'])
        self.assertFalse(User.objects.get(pk=self.user.pk).has_usable_password())

    def test_link_opened_before_deactivation_does_not_reset_the_password(self):
        self.request_link()
        client = Client()
        form_url = client.get(reset_link(mail.outbox[0]))['Location']
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        response = client.post(form_url, {'password1': PASSWORD, 'password2': PASSWORD})

        self.assertTrue(response.context['token_fail'])
        self.assertFalse(User.objects.get(pk=self.user.pk).has_usable_password())
