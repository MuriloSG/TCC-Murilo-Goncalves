from django.test import TestCase
from config.testing import IsolatedCasesMixin

from accounts.models import User
from accounts.tests.roles import requester_role
from audit.models import AuditLog
from notices import catalog
from notices.models import Notification


class NotificationViewTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        docente = requester_role()
        cls.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', docente)
        cls.bruno = User.objects.register('bruno@ifnmg.edu.br', 'Bruno', docente)

    def setUp(self):
        self.client.force_login(self.ana)

    def notify(self, recipient=None, target_url=''):
        return Notification.objects.notify(
            recipient or self.ana,
            catalog.INFORMATION,
            'Nova versão do sistema',
            'Uma versão nova do sistema foi disponibilizada.',
            target_url=target_url,
        )


class OpenTests(NotificationViewTestCase):
    def test_opening_marks_as_read_and_goes_to_the_target_or_the_origin(self):
        with self.case('origem'):
            notification = self.notify()
            response = self.client.post(f'/notificacoes/{notification.pk}/abrir/', {'next': '/usuarios/'})
            self.assertRedirects(response, '/usuarios/', fetch_redirect_response=False)
            self.assertFalse(Notification.objects.get(pk=notification.pk).unread)
            self.assertEqual(Notification.objects.unread_count(self.ana), 0)
        with self.case('destino'):
            notification = self.notify(target_url='/perfis/')
            response = self.client.post(f'/notificacoes/{notification.pk}/abrir/', {'next': '/usuarios/'})
            self.assertRedirects(response, '/perfis/', fetch_redirect_response=False)

    def test_return_never_leaves_the_system(self):
        with self.case('origem externa'):
            notification = self.notify()
            response = self.client.post(
                f'/notificacoes/{notification.pk}/abrir/',
                {'next': 'https://exemplo.invalido/'},
            )
            self.assertRedirects(response, '/inicio/', fetch_redirect_response=False)
        with self.case('fragmento'):
            self.notify()
            for origin in ('', 'https://externo.com/'):
                content = self.client.get('/notificacoes/sino/', {'origem': origin}).content.decode()
                self.assertIn('name="next" value="/inicio/"', content)

    def test_notification_of_another_user_is_refused(self):
        notification = self.notify(recipient=self.bruno)
        response = self.client.post(f'/notificacoes/{notification.pk}/abrir/')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Notification.objects.get(pk=notification.pk).unread)


class ReadAllTests(NotificationViewTestCase):
    def test_marks_only_the_notifications_of_the_user(self):
        self.notify()
        self.notify()
        self.notify(recipient=self.bruno)
        response = self.client.post('/notificacoes/lidas/', {'next': '/usuarios/'})
        self.assertRedirects(response, '/usuarios/', fetch_redirect_response=False)
        self.assertEqual(Notification.objects.unread_count(self.ana), 0)
        self.assertEqual(Notification.objects.unread_count(self.bruno), 1)


class PanelTests(NotificationViewTestCase):
    def test_fragment_has_the_notifications_of_the_user(self):
        with self.case('notificações do usuário'):
            self.notify()
            self.notify(recipient=self.bruno)
            content = self.client.get('/notificacoes/sino/').content.decode()
            self.assertTrue(content.startswith('<details class="menu notifications"'))
            self.assertIn('<span class="notifications-count" aria-hidden="true">1</span>', content)
            self.assertEqual(content.count('<li class="notification'), 1)
        with self.case('volta à tela aberta'):
            self.notify()
            content = self.client.get('/notificacoes/sino/', {'origem': '/agenda/?semana=2'}).content.decode()
            self.assertIn('name="next" value="/agenda/?semana=2"', content)
            self.assertNotIn('value="/notificacoes/sino/', content)
