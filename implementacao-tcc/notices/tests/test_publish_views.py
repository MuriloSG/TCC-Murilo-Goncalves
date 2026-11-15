from django.test import TestCase
from config.testing import IsolatedCasesMixin

from accounts.models import Role, User
from accounts.tests.roles import management_role, requester_role
from audit import catalog as audit_catalog
from audit.models import AuditLog
from notices import catalog
from notices.models import Notice, Notification

CREATE_URL = '/notificacoes/nova/'
PUBLISH_URL = '/notificacoes/publicar/'


def data(**changes):
    values = {
        'title': 'Nova versão do sistema',
        'message': 'Uma versão nova do sistema foi disponibilizada.',
        'type': catalog.INFORMATION,
        'destination': catalog.ALL_USERS,
    }
    values.update(changes)
    return values


class PublishTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()
        cls.admin = User.objects.register('admin@ifnmg.edu.br', 'Admin', cls.administrator)
        cls.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', cls.teacher)
        cls.bruno = User.objects.register('bruno@ifnmg.edu.br', 'Bruno', cls.teacher)

    def setUp(self):
        self.client.force_login(self.admin)


class CreateStepTests(PublishTestCase):
    def test_destination_requires_its_choice(self):
        with self.case('perfil'):
            response = self.client.post(CREATE_URL, data(destination=catalog.ROLE))
            self.assertContains(response, 'Escolha o perfil que vai receber a notificação.')
            self.assertEqual(Notification.objects.count(), 0)
        with self.case('usuários'):
            response = self.client.post(CREATE_URL, data(destination=catalog.USERS))
            self.assertContains(response, 'Escolha pelo menos um usuário.')
            self.assertEqual(Notification.objects.count(), 0)


class ReviewStepTests(PublishTestCase):
    def review(self, **changes):
        return self.client.post(CREATE_URL, data(**changes))

    def test_review_shows_the_preview_without_creating(self):
        with self.case('prévia e estimativa'):
            content = self.review().content.decode()
            self.assertIn('Nova versão do sistema', content)
            self.assertIn('Todos os usuários', content)
            self.assertIn('3 usuários ativos', content)
            self.assertIn('Publicar notificação</button>', content)
        with self.case('não cria nada'):
            self.review()
            self.assertEqual(Notification.objects.count(), 0)
            self.assertEqual(AuditLog.objects.filter(resource=audit_catalog.NOTICE).count(), 0)

    def test_review_carries_the_values_forward(self):
        with self.case('valores'):
            content = self.review(destination=catalog.ROLE, role=self.teacher.pk).content.decode()
            self.assertIn('<input type="hidden" name="title" value="Nova versão do sistema">', content)
            self.assertIn(f'<input type="hidden" name="role" value="{self.teacher.pk}">', content)
            self.assertIn('<dt>Destinatários</dt><dd>Usuários de um perfil</dd>', content)
            self.assertIn('<dt>Total estimado</dt><dd>2 usuários ativos</dd>', content)
        with self.case('chaves sem separador de milhar'):
            role = Role.objects.create(pk=1234, code='EXTENSAO', name='Extensão')
            user = User.objects.create(pk=1235, email='caio@ifnmg.edu.br', name='Caio')
            cases = (
                (dict(destination=catalog.ROLE, role=role.pk), '<input type="hidden" name="role" value="1234">'),
                (dict(destination=catalog.USERS, users=[user.pk]), '<input type="hidden" name="users" value="1235">'),
            )
            for changes, expected in cases:
                with self.subTest(changes['destination']):
                    self.assertIn(expected, self.review(**changes).content.decode())


class PublishStepTests(PublishTestCase):
    def test_publication_reaches_every_active_user(self):
        response = self.client.post(PUBLISH_URL, data(), follow=True)
        self.assertRedirects(response, '/notificacoes/')
        self.assertEqual(Notification.objects.count(), 3)
        self.assertEqual(Notification.objects.unread().count(), 3)
        self.assertContains(
            response,
            'Notificação &quot;Nova versão do sistema&quot; publicada para 3 destinatários.',
        )

    def test_publication_without_recipients_shows_the_refusal(self):
        role = Role.objects.create_role('COORDENACAO', 'Coordenação')
        response = self.client.post(PUBLISH_URL, data(destination=catalog.ROLE, role=role.pk))
        self.assertContains(response, 'Nenhum usuário ativo corresponde aos destinatários escolhidos.')
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(resource=audit_catalog.NOTICE).count(), 0)


class ListTests(PublishTestCase):
    def publish(self, title, **changes):
        """Publica e segue o redirecionamento, para a mensagem de sucesso ser consumida."""
        self.client.post(PUBLISH_URL, data(title=title, **changes), follow=True)

    def test_list_shows_only_the_global_notices_published(self):
        with self.case('só globais'):
            self.publish('Para todos')
            self.publish('Para o perfil', destination=catalog.ROLE, role=self.teacher.pk)
            self.publish('Para a Ana', destination=catalog.USERS, users=[self.ana.pk])
            content = self.client.get('/notificacoes/').content.decode()
            self.assertIn('Para todos', content)
            self.assertNotIn('Para o perfil', content)
            self.assertNotIn('Para a Ana', content)
            self.assertEqual(Notice.objects.count(), 3)
        with self.case('o que foi publicado'):
            self.publish('Nova versão do sistema')
            content = self.client.get('/notificacoes/').content.decode()
            self.assertIn('3 usuários', content)
            self.assertIn('Admin', content)
            self.assertIn('Informação', content)
