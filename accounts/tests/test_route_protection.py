from django.test import Client, TestCase
from django.urls import URLResolver, get_resolver, reverse

from accounts import permissions
from accounts.models import Role, User

PROTECTED_ROUTES = {
    'home': None,
    'notification_open': None,
    'notifications_panel': None,
    'notifications_read_all': None,
    'user_list': permissions.USER_VIEW,
    'user_create': permissions.USER_CREATE,
    'user_update': permissions.USER_EDIT,
    'user_change_role': permissions.USER_CHANGE_ROLE,
    'user_deactivate': permissions.USER_CHANGE_STATUS,
    'user_reactivate': permissions.USER_CHANGE_STATUS,
    'user_import_list': permissions.USER_IMPORT,
    'user_import_upload': permissions.USER_IMPORT,
    'user_import_template': permissions.USER_IMPORT,
    'user_import_detail': permissions.USER_IMPORT,
    'user_import_status': permissions.USER_IMPORT,
    'user_import_confirm': permissions.USER_IMPORT,
    'user_import_discard': permissions.USER_IMPORT,
    'user_import_delete': permissions.USER_IMPORT_DELETE,
    'role_list': permissions.ROLE_VIEW,
    'role_create': permissions.ROLE_CREATE,
    'role_detail': permissions.ROLE_VIEW,
    'role_update': permissions.ROLE_EDIT,
    'role_permissions': permissions.ROLE_CHANGE_PERMISSIONS,
    'role_delete': permissions.ROLE_DELETE,
    'audit_log_list': permissions.AUDIT_VIEW,
    'audit_log_detail': permissions.AUDIT_VIEW,
    'audit_user_options': permissions.AUDIT_VIEW,
    'notice_list': permissions.NOTICE_PUBLISH,
    'notice_create': permissions.NOTICE_PUBLISH,
    'notice_user_options': permissions.NOTICE_PUBLISH,
    'notice_publish': permissions.NOTICE_PUBLISH,
    'spaces_list': permissions.SPACE_VIEW,
    'spaces_create': permissions.SPACE_CREATE,
    'spaces_update': permissions.SPACE_EDIT,
    'spaces_deactivate': permissions.SPACE_CHANGE_STATUS,
    'spaces_reactivate': permissions.SPACE_CHANGE_STATUS,
    'spaces_delete': permissions.SPACE_DELETE,
    'subjects_list': permissions.SUBJECT_VIEW,
    'subjects_create': permissions.SUBJECT_CREATE,
    'subjects_detail': permissions.SUBJECT_VIEW,
    'subjects_update': permissions.SUBJECT_EDIT,
    'subjects_delete': permissions.SUBJECT_DELETE,
    'class_groups_list': permissions.CLASS_GROUP_VIEW,
    'class_groups_create': permissions.CLASS_GROUP_CREATE,
    'class_groups_detail': permissions.CLASS_GROUP_VIEW,
    'class_groups_update': permissions.CLASS_GROUP_EDIT,
    'class_groups_delete': permissions.CLASS_GROUP_DELETE,
    'space_allocation_grid': permissions.SPACE_ALLOCATION_VIEW,
    'space_allocation_occurrence_cancel': permissions.SPACE_ALLOCATION_VIEW,
    'space_allocation_recurrence_end': permissions.SPACE_ALLOCATION_END_RECURRENCE,
    'space_allocation_recurrence_create': permissions.SPACE_ALLOCATION_CREATE_RECURRENCE,
    'space_allocation_recurrence_change': permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE,
    'space_allocation_exception_list': permissions.SPACE_ALLOCATION_VIEW,
    'space_allocation_import_list': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_upload': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_detail': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_status': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_confirm': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_discard': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_delete': permissions.SPACE_ALLOCATION_IMPORT_DELETE,
    'space_allocation_import_decide': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_withdraw': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_associate': permissions.SPACE_ALLOCATION_IMPORT,
    'space_allocation_import_refresh': permissions.SPACE_ALLOCATION_IMPORT,
    'agenda_grid': permissions.BOOKING_VIEW,
    'agenda_occurrence_cancel': permissions.BOOKING_VIEW,
    'agenda_exception_list': permissions.BOOKING_VIEW,
    'agenda_request_create': permissions.BOOKING_REQUEST,
    'agenda_create': permissions.BOOKING_CREATE,
    'agenda_my_requests': permissions.BOOKING_REQUEST,
    'agenda_my_request': permissions.BOOKING_REQUEST,
    'agenda_my_request_accept': permissions.BOOKING_REQUEST,
    'agenda_my_request_decline': permissions.BOOKING_REQUEST,
    'agenda_my_request_cancel': permissions.BOOKING_REQUEST,
    'agenda_review_list': permissions.BOOKING_REVIEW,
    'agenda_review_detail': permissions.BOOKING_REVIEW,
    'agenda_review_approve': permissions.BOOKING_REVIEW,
    'agenda_review_reject': permissions.BOOKING_REVIEW,
    'agenda_review_suggest': permissions.BOOKING_REVIEW,
    'agenda_review_cancel': permissions.BOOKING_REVIEW,
    'panel': permissions.PANEL_VIEW,
    'panel_issue': permissions.PANEL_VIEW,
    'report_heatmap': permissions.REPORT_VIEW,
    'report_heatmap_cell': permissions.REPORT_VIEW,
    'report_requests': permissions.REPORT_VIEW,
    'settings_email': permissions.SETTINGS_EDIT,
    'settings_email_update': permissions.SETTINGS_EDIT,
    'settings_email_clear': permissions.SETTINGS_EDIT,
}

PUBLIC_ROUTES = {
    'public_calendar',
    'public_original_timetable',
    'account_login',
    'account_logout',
    'account_reset_password',
    'account_reset_password_done',
    'account_reset_password_from_key',
    'account_reset_password_from_key_done',
}

URL_KWARGS = {'pk': 1, 'key': 'choque', 'day': 'segunda', 'slot': 1, 'uidb36': '1'}

GRANTABLE_PERMISSIONS = permissions.ALL_PERMISSIONS - permissions.SUPERADMIN_RESERVED_PERMISSIONS


def url_patterns(patterns=None):
    """Percorre todas as rotas do projeto, inclusive as de cada app."""
    for pattern in get_resolver().url_patterns if patterns is None else patterns:
        if isinstance(pattern, URLResolver):
            yield from url_patterns(pattern.url_patterns)
        else:
            yield pattern


def route_url(pattern):
    """Monta a URL da rota com valores fictícios: a proteção age antes de buscar o objeto."""
    kwargs = {name: URL_KWARGS[name] for name in pattern.pattern.regex.groupindex}
    return reverse(pattern.name, kwargs=kwargs)


def accepted_methods(pattern):
    """Métodos que a view atende, entre GET e POST."""
    view_class = pattern.callback.view_class
    return [method for method in ('get', 'post') if hasattr(view_class, method)]


class RouteProtectionTests(TestCase):
    """Proteção de todas as rotas num só lugar (§7 das convenções).

    Cada app testa só a execução com a permissão; o anônimo, a falta da permissão
    e o POST sem CSRF são verificados aqui para toda rota do projeto.
    """

    @classmethod
    def setUpTestData(cls):
        cls.patterns = {pattern.name: pattern for pattern in url_patterns()}
        cls.admin = User.objects.register(
            email='admin@ifnmg.edu.br', name='Admin', role=Role.objects.get(code='ADMINISTRADOR'),
        )
        cls.without = {}
        for permission in {code for code in PROTECTED_ROUTES.values() if code}:
            code = 'SEM_' + permission.replace('.', '_')
            role = Role.objects.create_role(
                code=code, name=code, permissions=GRANTABLE_PERMISSIONS - {permission},
            )
            cls.without[permission] = User.objects.register(
                email=f'{code.lower()}@ifnmg.edu.br', name=code.capitalize(), role=role,
            )

    def protected(self):
        for name, permission in PROTECTED_ROUTES.items():
            yield name, permission, self.patterns[name]

    def test_every_route_is_classified(self):
        self.assertEqual(set(self.patterns), set(PROTECTED_ROUTES) | PUBLIC_ROUTES)

    def test_each_view_declares_the_expected_permission(self):
        expected = PROTECTED_ROUTES | dict.fromkeys(PUBLIC_ROUTES)
        for name, permission in expected.items():
            with self.subTest(name):
                view_class = self.patterns[name].callback.view_class
                self.assertEqual(getattr(view_class, 'permission_required', None), permission)

    def test_anonymous_is_redirected_to_login_with_next(self):
        client = Client()
        for name, _, pattern in self.protected():
            url = route_url(pattern)
            for method in accepted_methods(pattern):
                with self.subTest(name, method=method):
                    response = getattr(client, method)(url)
                    self.assertRedirects(response, f'/contas/login/?next={url}', fetch_redirect_response=False)

    def test_user_without_the_permission_gets_403(self):
        for name, permission, pattern in self.protected():
            if permission is None:
                continue
            client = Client()
            client.force_login(self.without[permission])
            url = route_url(pattern)
            for method in accepted_methods(pattern):
                with self.subTest(name, method=method):
                    self.assertEqual(getattr(client, method)(url).status_code, 403)

    def test_post_without_csrf_is_refused(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for name, pattern in self.patterns.items():
            if 'post' not in accepted_methods(pattern):
                continue
            with self.subTest(name):
                self.assertEqual(client.post(route_url(pattern)).status_code, 403)
