from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts import permissions
from accounts.imports import UserImport
from accounts.models import Role, User
from accounts.tests.roles import management_role, requester_role
from imports.models import Import
from imports.reader import SourceRow
from imports.tests.worker import poll, preview, run_worker
from outbox.models import OutboxEntry
from ui.pagination import ROWS_PAGE_SIZE

HEADER = 'E-mail;Nome;Perfil;Nome de usuário\n'


def csv_file(lines, name='usuarios.csv'):
    return SimpleUploadedFile(name, (HEADER + lines).encode(), content_type='text/csv')


class ImportViewsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)

    def setUp(self):
        self.client.force_login(self.admin)

    def preview(self, *lines):
        labels = ('E-mail', 'Nome', 'Perfil', 'Nome de usuário')
        rows = [
            SourceRow(number, dict(zip(labels, line.split(';') + [''] * len(labels))))
            for number, line in enumerate(lines, start=2)
        ]
        return preview(UserImport(), rows, 'usuarios.csv', self.admin)

    def user_with(self, *codes, email='limitado@ifnmg.edu.br'):
        code = email.partition('@')[0].upper()
        role = Role.objects.create_role(code=code, name=code, permissions=codes)
        return User.objects.register(email=email, name=code.capitalize(), role=role)

    def routes(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
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
    def test_only_the_import_permission_is_needed_for_the_screens(self):
        client = Client()
        client.force_login(self.user_with(permissions.USER_IMPORT))
        routes = self.routes()
        for route in ('list', 'upload', 'template', 'detail', 'discard'):
            with self.subTest(route):
                self.assertEqual(client.get(routes[route][0]).status_code, 200)

    def test_direct_access_follows_each_permission(self):
        discarded = self.preview('bia@ifnmg.edu.br;Bia;SOLICITACAO')
        discarded.discard(UserImport(), self.admin)
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO').pk
        screens = (
            '/usuarios/importacoes/', '/usuarios/importacoes/nova/', '/usuarios/importacoes/modelo/',
            f'/usuarios/importacoes/{importation}/', f'/usuarios/importacoes/{importation}/descartar/',
        )
        cases = (
            ('so_importa', (permissions.USER_IMPORT,), 403, 200),
            ('so_visualiza', (permissions.USER_VIEW,), 200, 403),
            ('ambas', (permissions.USER_VIEW, permissions.USER_IMPORT), 200, 200),
            ('nenhuma', (permissions.PANEL_VIEW,), 403, 403),
        )
        for name, codes, user_list, imports in cases:
            client = Client()
            client.force_login(self.user_with(*codes, email=f'{name}@ifnmg.edu.br'))
            with self.subTest(name, url='/usuarios/'):
                self.assertEqual(client.get('/usuarios/').status_code, user_list)
            for url in screens:
                with self.subTest(name, url=url):
                    self.assertEqual(client.get(url).status_code, imports)
            for url in ('/usuarios/novo/', f'/usuarios/importacoes/{discarded.pk}/excluir/'):
                with self.subTest(name, url=url):
                    self.assertEqual(client.post(url).status_code, 403)
        self.assertTrue(Import.objects.filter(pk=discarded.pk).exists())

    def test_deleting_an_import_needs_its_own_permission(self):
        discarded = self.preview('bia@ifnmg.edu.br;Bia;SOLICITACAO')
        discarded.discard(UserImport(), self.admin)
        client = Client()
        client.force_login(self.user_with(permissions.USER_IMPORT, permissions.USER_IMPORT_DELETE))
        self.assertNotEqual(client.post(f'/usuarios/importacoes/{discarded.pk}/excluir/').status_code, 403)
        self.assertFalse(Import.objects.filter(pk=discarded.pk).exists())

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
            '/usuarios/importacoes/nova/', {'file': csv_file('bia@ifnmg.edu.br;Bia;SOLICITACAO\n')},
        )
        importation = Import.objects.get()
        self.assertRedirects(response, f'/usuarios/importacoes/{importation.pk}/', fetch_redirect_response=False)
        self.assertEqual(
            (importation.kind, importation.file_name, importation.status, importation.operation),
            ('USUARIO', 'usuarios.csv', 'RECEBIDA', 'PREVIA'),
        )
        self.assertFalse(importation.rows.exclude(action=None).exists())
        page = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(page, 'Arquivo usuarios.csv enviado. A prévia está em processamento.')
        run_worker(UserImport())
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), ('VALIDADA', None))
        self.assertFalse(User.objects.filter(email='bia@ifnmg.edu.br').exists())

    def test_htmx_upload_redirects_the_page(self):
        response = self.client.post(
            '/usuarios/importacoes/nova/',
            {'file': csv_file('bia@ifnmg.edu.br;Bia;SOLICITACAO\n')},
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
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO', 'bruno@ifnmg.edu.br;Bruno;GESTAO')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(response, 'Confirmar importação')
        self.assertContains(response, 'Descartar importação')
        self.assertNotContains(response, 'Prévia pronta.')
        self.assertContains(response, 'Perfil: SOLICITACAO → GESTAO')
        self.assertContains(response, '1 cadastro, 1 atualização e 0 sem alteração')

    def test_preview_with_errors_has_no_confirm_and_shows_line_and_column(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;COORDENACAO', 'bia@ifnmg.edu.br;Bia;SOLICITACAO')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertNotContains(response, 'Confirmar importação')
        self.assertContains(response, 'Enviar arquivo corrigido')
        self.assertContains(response, 'Perfil: Não existe perfil com o código COORDENACAO.')
        self.assertContains(response, '1 linha com erro')
        only_errors = self.client.get(f'/usuarios/importacoes/{importation.pk}/?linhas=erros')
        self.assertContains(only_errors, 'ana@ifnmg.edu.br')
        self.assertNotContains(only_errors, 'bia@ifnmg.edu.br')

    def test_file_error_is_shown(self):
        importation = self.preview('admin@ifnmg.edu.br;Admin;SOLICITACAO')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(response, 'Operação recusada')

    def test_history_lists_only_user_imports(self):
        self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        Import.objects.create(kind='GRUPO', status='VALIDADA', file_name='grupos.csv', created_by=self.admin)
        response = self.client.get('/usuarios/importacoes/')
        self.assertContains(response, 'usuarios.csv')
        self.assertNotContains(response, 'grupos.csv')
        self.assertContains(response, '1 cadastro, 0 atualizações e 0 sem alteração')

    def test_empty_history(self):
        self.assertContains(self.client.get('/usuarios/importacoes/'), 'Nenhuma importação de usuários.')


class LineNumberFilterTests(ImportViewsTestCase):
    def setUp(self):
        super().setUp()
        self.importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO', 'bia@ifnmg.edu.br;Bia;SOLICITACAO', 'caio@ifnmg.edu.br;Caio;SOLICITACAO')
        self.url = f'/usuarios/importacoes/{self.importation.pk}/'

    def test_one_line(self):
        response = self.client.get(self.url + '?numero=3')
        self.assertEqual(response.context['page'].paginator.count, 1)
        self.assertContains(response, 'bia@ifnmg.edu.br')
        self.assertNotContains(response, 'ana@ifnmg.edu.br')
        self.assertContains(response, 'Linha 3')
        self.assertContains(response, 'Mostrar todas as linhas')

    def test_two_lines(self):
        response = self.client.get(self.url + '?numero=2&numero=4')
        self.assertEqual(response.context['page'].paginator.count, 2)
        self.assertContains(response, 'Linhas 2 e 4')

    def test_invalid_number_is_discarded(self):
        response = self.client.get(self.url + '?numero=abc')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 3)
        self.assertNotContains(response, 'Mostrar todas as linhas')

    def test_number_combines_with_the_filter(self):
        response = self.client.get(self.url + '?linhas=erros&numero=2')
        self.assertEqual(response.context['page'].paginator.count, 0)


class ConfirmAndDiscardTests(ImportViewsTestCase):
    def test_confirm_applies_and_informs_the_link(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        response = self.client.post(f'/usuarios/importacoes/{importation.pk}/confirmar/', follow=True)
        self.assertRedirects(response, f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(response, 'Confirmação da importação do arquivo usuarios.csv em processamento.')
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), ('VALIDADA', 'CONFIRMACAO'))
        self.assertFalse(User.objects.filter(email='ana@ifnmg.edu.br').exists())
        run_worker(UserImport())
        self.assertNotContains(self.client.get(f'/usuarios/importacoes/{importation.pk}/'), 'Importação concluída.')
        poll(self.client, f'/usuarios/importacoes/{importation.pk}/')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertIn('Importação concluída.', [str(message) for message in response.context['messages']][0])
        self.assertContains(
            response,
            'Importação concluída. 1 usuário cadastrado. '
            'O link para definir a senha será enviado aos usuários cadastrados.',
        )
        ana = User.objects.get(email='ana@ifnmg.edu.br')
        self.assertTrue(OutboxEntry.objects.filter(reference=str(ana.pk)).exists())

    def test_divergence_message(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=self.teacher)
        self.client.post(f'/usuarios/importacoes/{importation.pk}/confirmar/')
        run_worker(UserImport())
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(response, 'Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo.')
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.revalidation_count), ('VALIDADA', 1))

    def test_discard_asks_on_get_and_discards_on_post(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        url = f'/usuarios/importacoes/{importation.pk}/descartar/'
        self.assertContains(self.client.get(url), 'Descartar a importação de usuarios.csv?')
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'VALIDADA')
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'Importação do arquivo usuarios.csv descartada.')
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'DESCARTADA')

    def test_second_confirmation_is_refused_with_message(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        url = f'/usuarios/importacoes/{importation.pk}/confirmar/'
        self.client.post(url)
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'Esta importação está em processamento e não aceita outra ação até ele terminar.')
        self.assertEqual(Import.objects.get().operation, 'CONFIRMACAO')
        run_worker(UserImport())
        response = self.client.post(url, follow=True)
        self.assertContains(
            response, 'Esta importação está concluída e não pode mais ser confirmada nem descartada.',
        )
        self.assertEqual(User.objects.filter(email='ana@ifnmg.edu.br').count(), 1)


class TemplateTests(ImportViewsTestCase):
    def test_template_is_utf8_with_bom_and_semicolons(self):
        response = self.client.get('/usuarios/importacoes/modelo/')
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('modelo-importacao-usuarios.csv', response['Content-Disposition'])
        self.assertEqual(response.content, '﻿E-mail;Nome;Perfil;Nome de usuário\r\n'.encode())


class PaginationTests(ImportViewsTestCase):
    def test_preview_rows_are_paginated_and_summary_counts_all(self):
        total = ROWS_PAGE_SIZE * 2 + 1
        lines = [f'p{index:03d}@ifnmg.edu.br;Pessoa {index:03d};COORDENACAO' for index in range(total)]
        importation = self.preview(*lines)
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        content = response.content.decode()
        self.assertIn(
            f'Exibindo <strong>1</strong> a <strong>{ROWS_PAGE_SIZE}</strong> de <strong>{total}</strong> linhas', content,
        )
        self.assertIn(f'p{ROWS_PAGE_SIZE - 1:03d}@ifnmg.edu.br', content)
        self.assertNotIn(f'p{ROWS_PAGE_SIZE:03d}@ifnmg.edu.br', content)
        self.assertIn(f'{total} linhas com erro', content)
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/', {'linhas': 'erros'})
        self.assertContains(response, f'href="/usuarios/importacoes/{importation.pk}/?linhas=erros&amp;pagina=2"')


class ImportDeletionTests(ImportViewsTestCase):
    def discarded(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        importation.discard(UserImport(), self.admin)
        return importation

    def test_administrator_deletes_a_discarded_import(self):
        importation = self.discarded()
        url = f'/usuarios/importacoes/{importation.pk}/excluir/'
        self.assertContains(self.client.get(f'/usuarios/importacoes/{importation.pk}/'), url)
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, '/usuarios/importacoes/')
        self.assertFalse(Import.objects.exists())

    def test_without_the_permission_the_deletion_is_refused(self):
        importation = self.discarded()
        self.client.force_login(self.user_with(permissions.USER_IMPORT))
        url = f'/usuarios/importacoes/{importation.pk}/excluir/'
        self.assertNotContains(self.client.get(f'/usuarios/importacoes/{importation.pk}/'), url)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Import.objects.exists())


class ProcessingTests(ImportViewsTestCase):
    """Quadro da operação pendente, rota do andamento e aviso de demora."""

    def requested(self):
        return Import.objects.request_preview(
            UserImport(), [SourceRow(2, {'E-mail': 'ana@ifnmg.edu.br', 'Nome': 'Ana', 'Perfil': 'SOLICITACAO', 'Nome de usuário': ''})],
            'usuarios.csv', self.admin,
        )

    def test_detail_of_a_pending_preview_shows_the_panel_without_actions_or_rows(self):
        importation = self.requested()
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertNotContains(response, 'em processamento desde')
        self.assertContains(response, 'Em processamento')
        self.assertContains(response, 'Recebida')
        self.assertContains(response, f'hx-get="/usuarios/importacoes/{importation.pk}/andamento/"')
        self.assertContains(response, 'hx-trigger="every 3s"')
        self.assertNotContains(response, 'Confirmar importação')
        self.assertNotContains(response, 'Descartar importação')
        self.assertNotContains(response, 'Linhas do arquivo')
        self.assertNotContains(response, 'demorando')

    def test_pending_confirmation_keeps_the_business_status_and_the_plan(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        self.client.post(f'/usuarios/importacoes/{importation.pk}/confirmar/')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertNotContains(response, 'em processamento desde')
        self.assertContains(response, 'Validada')
        self.assertContains(response, 'Linhas do arquivo')
        self.assertNotContains(response, 'Confirmar importação')
        self.assertNotContains(response, 'Prévia pronta.')

    def test_status_route_answers_204_while_pending_and_refreshes_when_done(self):
        importation = self.requested()
        url = f'/usuarios/importacoes/{importation.pk}/andamento/'
        self.assertEqual(self.client.get(url).status_code, 204)
        run_worker(UserImport())
        response = self.client.get(url)
        self.assertEqual(response['HX-Refresh'], 'true')

    def test_stale_warning_is_derived_from_the_request_time(self):
        importation = self.requested()
        Import.objects.filter(pk=importation.pk).update(requested_at=timezone.now() - timedelta(seconds=61))
        url = f'/usuarios/importacoes/{importation.pk}/andamento/'
        self.assertEqual(self.client.get(url)['HX-Refresh'], 'true')
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(
            response, 'O processamento está demorando mais que o esperado. Ele continua sendo executado em segundo plano.',
        )
        self.assertContains(response, 'O sistema pode continuar sendo usado. Volte a esta tela depois para consultar o resultado.')
        self.assertContains(response, f'hx-get="{url}?demora=1"')
        self.assertEqual(self.client.get(url + '?demora=1').status_code, 204)
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), ('RECEBIDA', 'PREVIA'))

    def test_stale_limit_comes_from_the_settings(self):
        importation = self.requested()
        Import.objects.filter(pk=importation.pk).update(requested_at=timezone.now() - timedelta(seconds=61))
        with override_settings(IMPORT_STALE_AFTER=120):
            response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertNotContains(response, 'demorando')

    def test_texts_do_not_expose_the_execution(self):
        importation = self.requested()
        Import.objects.filter(pk=importation.pk).update(requested_at=timezone.now() - timedelta(seconds=61))
        content = self.client.get(f'/usuarios/importacoes/{importation.pk}/').content.decode().lower()
        for term in ('worker', 'fila', 'postgresql', 'banco de dados', 'tentativa', 'trava'):
            with self.subTest(term):
                self.assertNotIn(term, content)

    @override_settings(IMPORT_MAX_ATTEMPTS=1)
    def test_failed_preview_shows_the_message_and_can_be_deleted(self):
        importation = self.requested()
        with mock.patch.object(Import, 'run_preview', side_effect=RuntimeError('falha')):
            run_worker(UserImport())
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(response, 'Falhou')
        self.assertContains(response, 'A prévia não foi gerada por uma falha do sistema. Envie o arquivo de novo.')
        self.assertContains(response, 'Enviar arquivo de novo')
        self.assertNotContains(response, 'RuntimeError')
        self.client.post(f'/usuarios/importacoes/{importation.pk}/excluir/')
        self.assertFalse(Import.objects.exists())

    @override_settings(IMPORT_MAX_ATTEMPTS=1)
    def test_failed_confirmation_keeps_validated_and_shows_the_result(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        self.client.post(f'/usuarios/importacoes/{importation.pk}/confirmar/')
        with mock.patch.object(Import, 'run_confirmation', side_effect=RuntimeError('falha')):
            run_worker(UserImport())
        response = self.client.get(f'/usuarios/importacoes/{importation.pk}/')
        self.assertContains(
            response, 'A confirmação não foi concluída por uma falha do sistema. Nada foi aplicado. Confirme de novo.',
        )
        self.assertContains(response, 'Confirmar importação')
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), ('VALIDADA', None))

    def test_discard_while_pending_is_refused(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO')
        self.client.post(f'/usuarios/importacoes/{importation.pk}/confirmar/')
        response = self.client.post(f'/usuarios/importacoes/{importation.pk}/descartar/', follow=True)
        self.assertContains(response, 'Esta importação está em processamento e não aceita outra ação até ele terminar.')
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), ('VALIDADA', 'CONFIRMACAO'))

    def test_list_shows_the_processing_badge(self):
        self.requested()
        response = self.client.get('/usuarios/importacoes/')
        self.assertContains(response, 'Em processamento')
