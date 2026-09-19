from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from accounts import permissions
from accounts.imports import UserImport
from accounts.models import Role, User
from imports.models import Import
from imports.reader import SourceRow
from outbox.models import OutboxEntry

HEADER = 'E-mail;Nome;Perfil\n'


def csv_file(lines, name='usuarios.csv'):
    return SimpleUploadedFile(name, (HEADER + lines).encode(), content_type='text/csv')


class ImportViewsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)

    def setUp(self):
        self.client.force_login(self.admin)

    def preview(self, *lines):
        rows = [
            SourceRow(number, dict(zip(('E-mail', 'Nome', 'Perfil'), line.split(';'))))
            for number, line in enumerate(lines, start=2)
        ]
        return Import.objects.preview(UserImport(), rows, 'usuarios.csv', self.admin)

    def user_with(self, *codes, email='limitado@ifnmg.edu.br'):
        code = email.partition('@')[0].upper()
        role = Role.objects.create_role(code=code, name=code, permissions=codes)
        return User.objects.register(email=email, name=code.capitalize(), role=role)

    def routes(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE')
        pk = importation.pk
        return {
            'list': ('/usuarios/importacoes/', 'get'),
            'upload': ('/usuarios/importacoes/nova/', 'post'),
            'template': ('/usuarios/importacoes/modelo/', 'get'),
            'detail': (f'/usuarios/importacoes/{pk}/', 'get'),
            'confirm': (f'/usuarios/importacoes/{pk}/confirmar/', 'post'),
            'discard': (f'/usuarios/importacoes/{pk}/descartar/', 'post'),
        }


class AccessTests(ImportViewsTestCase):
    def test_anonymous_is_redirected_to_login_with_next(self):
        client = Client()
        for route, (url, method) in self.routes().items():
            with self.subTest(route):
                response = getattr(client, method)(url)
                self.assertRedirects(response, f'/contas/login/?next={url}', fetch_redirect_response=False)
        self.assertEqual(Import.objects.get().status, 'VALIDADA')

    def test_without_the_import_permission_gets_403(self):
        client = Client()
        client.force_login(self.user_with(*permissions.ADMINISTRATIVE_CAPABILITY))
        for route, (url, method) in self.routes().items():
            with self.subTest(route):
                self.assertEqual(getattr(client, method)(url).status_code, 403)
        self.assertEqual(Import.objects.get().status, 'VALIDADA')
        self.assertFalse(User.objects.filter(email='ana@ifnmg.edu.br').exists())

    def test_only_the_import_permission_is_needed_for_the_screens(self):
        client = Client()
        client.force_login(self.user_with(permissions.USER_IMPORT))
        routes = self.routes()
        for route in ('list', 'upload', 'template', 'detail', 'discard'):
            with self.subTest(route):
                self.assertEqual(client.get(routes[route][0]).status_code, 200)

    def test_post_without_csrf_gets_403(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        routes = self.routes()
        response = client.post(routes['upload'][0], {'file': csv_file('bia@ifnmg.edu.br;Bia;DOCENTE\n')})
        self.assertEqual(response.status_code, 403)
        for route in ('confirm', 'discard'):
            with self.subTest(route):
                self.assertEqual(client.post(routes[route][0]).status_code, 403)
        self.assertEqual(Import.objects.count(), 1)
        self.assertEqual(Import.objects.get().status, 'VALIDADA')

    def test_import_of_another_kind_gives_404(self):
        other = Import.objects.create(kind='GRUPO', status='VALIDADA', file_name='grupos.csv', created_by=self.admin)
        for suffix in ('', 'confirmar/', 'descartar/'):
            with self.subTest(suffix):
                method = self.client.post if suffix else self.client.get
                self.assertEqual(method(f'/usuarios/importacoes/{other.pk}/{suffix}').status_code, 404)

    def test_user_list_shows_import_actions_only_with_the_permission(self):
        response = self.client.get('/usuarios/')
        self.assertContains(response, 'href="/usuarios/importacoes/"')
        self.assertNotContains(response, '/usuarios/importacoes/nova/')
        client = Client()
        client.force_login(self.user_with(permissions.USER_VIEW))
        response = client.get('/usuarios/')
        self.assertNotContains(response, '/usuarios/importacoes/')


class UploadTests(ImportViewsTestCase):
    def test_valid_file_creates_the_preview_and_opens_it(self):
        response = self.client.post(
            '/usuarios/importacoes/nova/', {'file': csv_file('bia@ifnmg.edu.br;Bia;DOCENTE\n')},
        )
        importation = Import.objects.get()
        self.assertRedirects(response, f'/usuarios/importacoes/{importation.pk}/')
        self.assertEqual(
            (importation.kind, importation.file_name, importation.status), ('USUARIO', 'usuarios.csv', 'VALIDADA'),
        )
        self.assertFalse(User.objects.filter(email='bia@ifnmg.edu.br').exists())

    def test_htmx_upload_redirects_the_page(self):
        response = self.client.post(
            '/usuarios/importacoes/nova/',
            {'file': csv_file('bia@ifnmg.edu.br;Bia;DOCENTE\n')},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response['HX-Redirect'], f'/usuarios/importacoes/{Import.objects.get().pk}/')

    def test_rejected_file_shows_the_error_and_creates_nothing(self):
        upload = SimpleUploadedFile('usuarios.csv', b'E-mail;Nome;Perfl\na;b;c\n')
        response = self.client.post('/usuarios/importacoes/nova/', {'file': upload})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Coluna &quot;Perfl&quot; não reconhecida.')
        self.assertFalse(Import.objects.exists())

    def test_upload_form_has_multipart_encoding(self):
        response = self.client.get('/usuarios/importacoes/nova/', HTTP_HX_REQUEST='true')
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'hx-encoding="multipart/form-data"')


class DetailTests(ImportViewsTestCase):
    def test_validated_preview_offers_confirm_and_discard(self):
        User.objects.register(email='bruno@ifnmg.edu.br', name='Bruno', role=self.teacher)
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE', 'bruno@ifnmg.edu.br;Bruno;ADMINISTRADOR')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(response, 'Confirmar importação')
        self.assertContains(response, 'Descartar importação')
        self.assertContains(response, 'Prévia pronta. Nenhum dado foi gravado.')
        self.assertContains(response, 'Perfil: DOCENTE → ADMINISTRADOR')
        self.assertContains(response, '1 cadastro, 1 atualização e 0 sem alteração')

    def test_preview_with_errors_has_no_confirm_and_shows_line_and_column(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;COORDENACAO', 'bia@ifnmg.edu.br;Bia;DOCENTE')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertNotContains(response, 'Confirmar importação')
        self.assertContains(response, 'Enviar arquivo corrigido')
        self.assertContains(response, 'Perfil: Não existe perfil com o código COORDENACAO.')
        self.assertContains(response, '1 linha com erro')
        only_errors = self.client.get(f'/usuarios/importacoes/{importation.pk}/?linhas=erros')
        self.assertContains(only_errors, 'ana@ifnmg.edu.br')
        self.assertNotContains(only_errors, 'bia@ifnmg.edu.br')

    def test_file_error_is_shown(self):
        importation = self.preview('admin@ifnmg.edu.br;Admin;DOCENTE')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(response, 'Operação recusada')

    def test_history_lists_only_user_imports(self):
        self.preview('ana@ifnmg.edu.br;Ana;DOCENTE')
        Import.objects.create(kind='GRUPO', status='VALIDADA', file_name='grupos.csv', created_by=self.admin)
        response = self.client.get('/usuarios/importacoes/')
        self.assertContains(response, 'usuarios.csv')
        self.assertNotContains(response, 'grupos.csv')
        self.assertContains(response, '1 cadastro, 0 atualizações e 0 sem alteração')

    def test_empty_history(self):
        self.assertContains(self.client.get('/usuarios/importacoes/'), 'Nenhuma importação de usuários.')


class ConfirmAndDiscardTests(ImportViewsTestCase):
    def test_confirm_applies_and_informs_the_link(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE')
        response = self.client.post(f'/usuarios/importacoes/{importation.pk}/confirmar/', follow=True)
        self.assertRedirects(response, f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(
            response,
            'Importação concluída. 1 usuário cadastrado. '
            'O link para definir a senha será enviado aos usuários cadastrados.',
        )
        ana = User.objects.get(email='ana@ifnmg.edu.br')
        self.assertTrue(OutboxEntry.objects.filter(reference=str(ana.pk)).exists())

    def test_divergence_message(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE')
        User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=self.teacher)
        response = self.client.post(f'/usuarios/importacoes/{importation.pk}/confirmar/', follow=True)
        self.assertContains(response, 'Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo.')
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.revalidation_count), ('VALIDADA', 1))

    def test_confirm_get_is_not_allowed(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE')
        self.assertEqual(self.client.get(f'/usuarios/importacoes/{importation.pk}/confirmar/').status_code, 405)

    def test_discard_asks_on_get_and_discards_on_post(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE')
        url = f'/usuarios/importacoes/{importation.pk}/descartar/'
        self.assertContains(self.client.get(url), 'Descartar a importação de usuarios.csv?')
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'VALIDADA')
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'Importação do arquivo usuarios.csv descartada.')
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'DESCARTADA')

    def test_second_confirmation_is_refused_with_message(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE')
        url = f'/usuarios/importacoes/{importation.pk}/confirmar/'
        self.client.post(url)
        response = self.client.post(url, follow=True)
        self.assertContains(
            response, 'Esta importação está concluída e não pode mais ser confirmada nem descartada.',
        )


class TemplateTests(ImportViewsTestCase):
    def test_template_is_utf8_with_bom_and_semicolons(self):
        response = self.client.get('/usuarios/importacoes/modelo/')
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('modelo-importacao-usuarios.csv', response['Content-Disposition'])
        self.assertEqual(response.content, '﻿E-mail;Nome;Perfil\r\n'.encode())


class PaginationTests(ImportViewsTestCase):
    def test_preview_rows_are_paginated_and_summary_counts_all(self):
        lines = [f'p{index:03d}@ifnmg.edu.br;Pessoa {index:03d};COORDENACAO' for index in range(120)]
        importation = self.preview(*lines)
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        content = response.content.decode()
        self.assertIn('Exibindo <strong>1</strong> a <strong>50</strong> de <strong>120</strong> linhas', content)
        self.assertIn('p049@ifnmg.edu.br', content)
        self.assertNotIn('p050@ifnmg.edu.br', content)
        self.assertIn('120 linhas com erro', content)
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/', {'linhas': 'erros'})
        self.assertContains(response, f'href="/usuarios/importacoes/{importation.pk}/?linhas=erros&amp;pagina=2"')

    def test_history_is_paginated(self):
        for _ in range(21):
            self.preview('ana@ifnmg.edu.br;Ana;DOCENTE')
        response = self.client.get('/usuarios/importacoes/', {'pagina': '2'})
        self.assertContains(
            response, 'Exibindo <strong>21</strong> a <strong>21</strong> de <strong>21</strong> importações',
        )
        self.assertContains(response, 'Todas as importações <span class="count">21</span>')
