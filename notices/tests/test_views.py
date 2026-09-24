from django.test import Client, TestCase

from accounts.models import Role, User
from audit.models import AuditLog
from notices import catalog
from notices.models import Notification


class NotificationViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        docente = Role.objects.get(code='DOCENTE')
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
    def test_anonymous_goes_to_login(self):
        notification = self.notify()
        self.client.logout()
        response = self.client.post(f'/notificacoes/{notification.pk}/abrir/')
        self.assertRedirects(
            response,
            f'/contas/login/?next=/notificacoes/{notification.pk}/abrir/',
            fetch_redirect_response=False,
        )
        self.assertTrue(Notification.objects.get(pk=notification.pk).unread)

    def test_opening_marks_as_read_and_returns_to_the_origin(self):
        notification = self.notify()
        response = self.client.post(f'/notificacoes/{notification.pk}/abrir/', {'next': '/usuarios/'})
        self.assertRedirects(response, '/usuarios/', fetch_redirect_response=False)
        self.assertFalse(Notification.objects.get(pk=notification.pk).unread)
        self.assertEqual(Notification.objects.unread_count(self.ana), 0)

    def test_opening_goes_to_the_target_when_there_is_one(self):
        notification = self.notify(target_url='/perfis/')
        response = self.client.post(f'/notificacoes/{notification.pk}/abrir/', {'next': '/usuarios/'})
        self.assertRedirects(response, '/perfis/', fetch_redirect_response=False)

    def test_origin_outside_the_system_is_ignored(self):
        notification = self.notify()
        response = self.client.post(
            f'/notificacoes/{notification.pk}/abrir/',
            {'next': 'https://exemplo.invalido/'},
        )
        self.assertRedirects(response, '/inicio/', fetch_redirect_response=False)

    def test_notification_of_another_user_is_refused(self):
        notification = self.notify(recipient=self.bruno)
        response = self.client.post(f'/notificacoes/{notification.pk}/abrir/')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Notification.objects.get(pk=notification.pk).unread)

    def test_get_is_refused(self):
        notification = self.notify()
        response = self.client.get(f'/notificacoes/{notification.pk}/abrir/')
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Notification.objects.get(pk=notification.pk).unread)

    def test_requires_csrf(self):
        notification = self.notify()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.ana)
        response = client.post(f'/notificacoes/{notification.pk}/abrir/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Notification.objects.get(pk=notification.pk).unread)

    def test_opening_a_read_notification_changes_nothing(self):
        notification = self.notify()
        notification.mark_as_read()
        read_at = notification.read_at
        self.client.post(f'/notificacoes/{notification.pk}/abrir/')
        self.assertEqual(Notification.objects.get(pk=notification.pk).read_at, read_at)


class ReadAllTests(NotificationViewTestCase):
    def test_marks_only_the_notifications_of_the_user(self):
        self.notify()
        self.notify()
        self.notify(recipient=self.bruno)
        response = self.client.post('/notificacoes/lidas/', {'next': '/usuarios/'})
        self.assertRedirects(response, '/usuarios/', fetch_redirect_response=False)
        self.assertEqual(Notification.objects.unread_count(self.ana), 0)
        self.assertEqual(Notification.objects.unread_count(self.bruno), 1)

    def test_anonymous_goes_to_login(self):
        self.client.logout()
        response = self.client.post('/notificacoes/lidas/')
        self.assertRedirects(
            response,
            '/contas/login/?next=/notificacoes/lidas/',
            fetch_redirect_response=False,
        )

    def test_requires_csrf(self):
        self.notify()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.ana)
        response = client.post('/notificacoes/lidas/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Notification.objects.unread_count(self.ana), 1)

    def test_get_is_refused(self):
        self.notify()
        response = self.client.get('/notificacoes/lidas/')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Notification.objects.unread_count(self.ana), 1)


class PanelTests(NotificationViewTestCase):
    def test_anonymous_goes_to_login(self):
        self.client.logout()
        response = self.client.get('/notificacoes/sino/')
        self.assertRedirects(
            response,
            '/contas/login/?next=/notificacoes/sino/',
            fetch_redirect_response=False,
        )

    def test_fragment_has_the_notifications_of_the_user(self):
        self.notify()
        self.notify(recipient=self.bruno)
        content = self.client.get('/notificacoes/sino/').content.decode()
        self.assertTrue(content.startswith('<details class="menu notifications"'))
        self.assertIn('<span class="notifications-count" aria-hidden="true">1</span>', content)
        self.assertEqual(content.count('<li class="notification'), 1)

    def test_fragment_without_notifications(self):
        content = self.client.get('/notificacoes/sino/').content.decode()
        self.assertIn('<p class="notifications-empty">Nenhuma notificação.</p>', content)

    def test_fragment_is_not_recorded_as_access(self):
        before = AuditLog.objects.count()
        self.client.get('/notificacoes/sino/')
        self.assertEqual(AuditLog.objects.count(), before)
