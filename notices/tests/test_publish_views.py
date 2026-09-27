from django.test import Client, TestCase

from accounts.models import Role, User
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


class PublishTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.admin = User.objects.register('admin@ifnmg.edu.br', 'Admin', cls.administrator)
        cls.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', cls.teacher)
        cls.bruno = User.objects.register('bruno@ifnmg.edu.br', 'Bruno', cls.teacher)

    def setUp(self):
        self.client.force_login(self.admin)


class AccessTests(PublishTestCase):
    def test_visitor_goes_to_login(self):
        self.client.logout()
        for url in (CREATE_URL, PUBLISH_URL):
            with self.subTest(url=url):
                response = self.client.post(url, data())
                self.assertRedirects(response, f'/contas/login/?next={url}', fetch_redirect_response=False)
        self.assertEqual(Notification.objects.count(), 0)

    def test_user_without_the_permission_is_refused(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(CREATE_URL).status_code, 403)
        self.assertEqual(self.client.post(CREATE_URL, data()).status_code, 403)
        self.assertEqual(self.client.post(PUBLISH_URL, data()).status_code, 403)
        self.assertEqual(Notification.objects.count(), 0)

    def test_user_with_the_permission_reaches_the_form(self):
        self.assertEqual(self.client.get(CREATE_URL).status_code, 200)

    def test_publication_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(PUBLISH_URL, data()).status_code, 403)
        self.assertEqual(Notification.objects.count(), 0)

    def test_navigation_shows_the_item_only_with_the_permission(self):
        self.assertContains(self.client.get('/inicio/', follow=True), '<span class="nav-text">Notificações</span>')
        self.client.force_login(self.ana)
        self.assertNotContains(self.client.get('/inicio/', follow=True), '<span class="nav-text">Notificações</span>')


class CreateStepTests(PublishTestCase):
    def test_form_shows_the_steps_and_the_fields(self):
        content = self.client.get(CREATE_URL).content.decode()
        self.assertIn('<h1 class="page-title">Nova notificação</h1>', content)
        self.assertIn('<li class="step is-current" aria-current="step">', content)
        self.assertIn('Detalhes da comunicação', content)
        self.assertIn('Título da notificação', content)
        self.assertIn('<span class="type-option-name">Informação</span>', content)
        self.assertIn('<div class="select select-many" data-select>', content)
        self.assertIn('data-select-none="Escolher usuários"', content)
        self.assertIn('data-select-source="/notificacoes/opcoes/usuarios/"', content)
        self.assertIn('<ul class="select-chips" role="list" data-select-chips></ul>', content)
        self.assertIn('<span class="type-option-hint">Uma ação concluída</span>', content)
        self.assertIn('Continuar para revisão</button>', content)
        self.assertIn('Fechar</a>', content)

    def test_form_shows_the_active_users_count(self):
        content = self.client.get(CREATE_URL).content.decode()
        self.assertIn('3 usuários ativos', content)

    def test_message_counter_starts_from_the_current_length(self):
        content = self.client.get(CREATE_URL).content.decode()
        self.assertIn('<span data-counter-value>0</span>/240', content)

    def test_role_is_required_for_the_role_destination(self):
        response = self.client.post(CREATE_URL, data(destination=catalog.ROLE))
        self.assertContains(response, 'Escolha o perfil que vai receber a notificação.')
        self.assertEqual(Notification.objects.count(), 0)

    def test_users_are_required_for_the_users_destination(self):
        response = self.client.post(CREATE_URL, data(destination=catalog.USERS))
        self.assertContains(response, 'Escolha pelo menos um usuário.')
        self.assertEqual(Notification.objects.count(), 0)

    def test_title_is_required(self):
        response = self.client.post(CREATE_URL, data(title=''))
        self.assertContains(response, 'Este campo é obrigatório.')
        self.assertEqual(Notification.objects.count(), 0)


class ReviewStepTests(PublishTestCase):
    def review(self, **changes):
        return self.client.post(CREATE_URL, data(**changes))

    def test_review_shows_the_preview_and_the_estimate(self):
        content = self.review().content.decode()
        self.assertIn('<h1 class="page-title">Revisar notificação</h1>', content)
        self.assertIn('<li class="step is-current" aria-current="step">', content)
        self.assertIn('<span class="notification-icon tone-info">', content)
        self.assertIn('<p class="notification-title">Nova versão do sistema</p>', content)
        self.assertIn('<dt>Destinatários</dt><dd>Todos os usuários</dd>', content)
        self.assertIn('<dt>Total estimado</dt><dd>3 usuários ativos</dd>', content)
        self.assertIn('Publicar notificação</button>', content)

    def test_review_creates_nothing(self):
        self.review()
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(resource=audit_catalog.NOTICE).count(), 0)

    def test_review_carries_the_values_forward(self):
        content = self.review(destination=catalog.ROLE, role=self.teacher.pk).content.decode()
        self.assertIn('<input type="hidden" name="title" value="Nova versão do sistema">', content)
        self.assertIn(f'<input type="hidden" name="role" value="{self.teacher.pk}">', content)
        self.assertIn('<dt>Destinatários</dt><dd>Usuários de um perfil</dd>', content)
        self.assertIn('<dt>Total estimado</dt><dd>2 usuários ativos</dd>', content)

    def test_review_counts_only_active_users(self):
        self.bruno.deactivate()
        content = self.review(destination=catalog.ROLE, role=self.teacher.pk).content.decode()
        self.assertIn('<dt>Total estimado</dt><dd>1 usuário ativo</dd>', content)

    def test_going_back_keeps_what_was_filled(self):
        content = self.client.post(CREATE_URL, data(title='Manutenção programada') | {'voltar': '1'}).content.decode()
        self.assertIn('<h1 class="page-title">Nova notificação</h1>', content)
        self.assertIn('value="Manutenção programada"', content)
        self.assertEqual(Notification.objects.count(), 0)


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

    def test_publication_is_audited(self):
        self.client.post(PUBLISH_URL, data())
        record = AuditLog.objects.filter(resource=audit_catalog.NOTICE).get()
        self.assertEqual(record.action, audit_catalog.PUBLISH)
        self.assertEqual(record.user, self.admin)
        self.assertEqual(record.metadata['destinatarios'], 3)

    def test_publication_to_specific_users(self):
        self.client.post(PUBLISH_URL, data(destination=catalog.USERS, users=[self.ana.pk]))
        self.assertEqual(list(Notification.objects.values_list('recipient', flat=True)), [self.ana.pk])

    def test_publication_to_a_role(self):
        self.client.post(PUBLISH_URL, data(destination=catalog.ROLE, role=self.teacher.pk))
        self.assertEqual(
            set(Notification.objects.values_list('recipient', flat=True)),
            {self.ana.pk, self.bruno.pk},
        )

    def test_publication_without_recipients_shows_the_refusal(self):
        role = Role.objects.create_role('COORDENACAO', 'Coordenação')
        response = self.client.post(PUBLISH_URL, data(destination=catalog.ROLE, role=role.pk))
        self.assertContains(response, 'Nenhum usuário ativo corresponde aos destinatários escolhidos.')
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(resource=audit_catalog.NOTICE).count(), 0)

    def test_type_generated_by_event_is_refused(self):
        response = self.client.post(PUBLISH_URL, data(type=catalog.ROLE_CHANGED))
        self.assertRedirects(response, CREATE_URL, fetch_redirect_response=False)
        self.assertEqual(Notification.objects.count(), 0)

    def test_get_is_refused(self):
        self.assertEqual(self.client.get(PUBLISH_URL).status_code, 405)


class ListTests(PublishTestCase):
    def publish(self, title, **changes):
        """Publica e segue o redirecionamento, para a mensagem de sucesso ser consumida."""
        self.client.post(PUBLISH_URL, data(title=title, **changes), follow=True)

    def test_anonymous_goes_to_login(self):
        self.client.logout()
        response = self.client.get('/notificacoes/')
        self.assertRedirects(response, '/contas/login/?next=/notificacoes/', fetch_redirect_response=False)

    def test_user_without_the_permission_is_refused(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get('/notificacoes/').status_code, 403)

    def test_list_comes_before_the_creation(self):
        content = self.client.get('/notificacoes/').content.decode()
        self.assertIn('<h1 class="page-title">Notificações</h1>', content)
        self.assertIn('Nova notificação</a>', content)
        self.assertIn('href="/notificacoes/nova/"', content)

    def test_only_global_notices_are_listed(self):
        self.publish('Para todos')
        self.publish('Para o perfil', destination=catalog.ROLE, role=self.teacher.pk)
        self.publish('Para a Ana', destination=catalog.USERS, users=[self.ana.pk])
        content = self.client.get('/notificacoes/').content.decode()
        self.assertIn('Para todos', content)
        self.assertNotIn('Para o perfil', content)
        self.assertNotIn('Para a Ana', content)
        self.assertEqual(Notice.objects.count(), 3)

    def test_list_shows_what_was_published(self):
        self.publish('Nova versão do sistema')
        content = self.client.get('/notificacoes/').content.decode()
        self.assertIn('<td data-label="Destinatários">3 usuários</td>', content)
        self.assertIn('<td data-label="Publicada por">Admin</td>', content)
        self.assertIn('Informação', content)

    def test_empty_state(self):
        content = self.client.get('/notificacoes/').content.decode()
        self.assertIn('Nenhuma notificação publicada para todos os usuários.', content)
        self.assertNotIn('pagination', content)

    def test_list_is_paginated(self):
        for number in range(6):
            self.publish(f'Comunicado {number}')
        content = self.client.get('/notificacoes/').content.decode()
        self.assertIn('Exibindo <strong>1</strong> a <strong>5</strong> de <strong>6</strong> notificações', content)
        self.assertIn('Página 1 de 2', content)

    def test_access_is_recorded(self):
        self.client.get('/notificacoes/')
        entry = AuditLog.objects.filter(action=audit_catalog.ACCESS, resource=audit_catalog.NOTICE).get()
        self.assertEqual(entry.user, self.admin)
        self.assertEqual(entry.metadata['rota'], 'notice_list')

    def test_publication_keeps_who_published(self):
        self.publish('Nova versão do sistema')
        notice = Notice.objects.get()
        self.assertEqual(notice.published_by, self.admin)
        self.assertEqual(notice.recipients_count, 3)
        self.assertEqual(notice.destination, catalog.ALL_USERS)
        self.assertEqual(Notification.objects.filter(notice=notice).count(), 3)
