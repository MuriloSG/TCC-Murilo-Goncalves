"""Quadro "Espaços desta importação" e atualização automática da prévia, pelas telas."""

from unittest import mock

from django.test import Client, TestCase
from django.urls import reverse

from accounts import permissions
from imports.models import Import
from schedule.imports import SpaceAllocationImport
from schedule.models import Space, SpaceDecision
from schedule.tests.test_import import PERIOD, workbook_file
from schedule.tests.test_space_import import SECONDARY_CELL, user_with
from schedule.views import SPACE_ALLOCATION_IMPORT_SCREENS

TWO_CELL_NAMES = {
    ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (Zoo I)',
    ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
    ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/41)',
}


class PanelTestCase(TestCase):
    def setUp(self):
        self.manager = user_with(
            'gestor@ifnmg.edu.br', permissions.SPACE_ALLOCATION_IMPORT, permissions.SPACE_ALLOCATION_VIEW,
            *permissions.SPACE_PERMISSIONS,
        )
        self.importer = user_with('importador@ifnmg.edu.br', permissions.SPACE_ALLOCATION_IMPORT)
        self.creator = user_with('cadastro@ifnmg.edu.br', permissions.SPACE_ALLOCATION_IMPORT, permissions.SPACE_CREATE)

    def upload(self, uploaded=None, user=None, semester='2026/1'):
        self.client.force_login(user or self.manager)
        self.client.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'),
            {'own_semestre': semester, **PERIOD, 'file': uploaded if uploaded is not None else workbook_file()},
        )
        return Import.objects.latest('pk')

    def detail(self, importation, user=None):
        self.client.force_login(user or self.manager)
        return self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk))

    def decide(self, importation, name, kind, user=None, **extra):
        self.client.force_login(user or self.manager)
        return self.client.post(
            reverse('space_allocation_import_decide', args=[importation.pk]),
            {'nome': name, 'decisao': kind, **extra},
            follow=True,
        )


class PanelTests(PanelTestCase):
    def test_proposals_are_described_in_the_future(self):
        importation = self.upload()
        response = self.detail(importation)
        self.assertContains(response, 'Espaços desta importação')
        self.assertNotContains(response, 'Nenhuma alteração foi feita no cadastro de espaços.')
        self.assertContains(response, '3 espaços novos serão cadastrados ao confirmar esta importação.')
        self.assertContains(response, 'A lista de salas da planilha tem 1 sala sem aula, que não será cadastrada.')
        self.assertContains(response, 'Pronta para confirmar. Ao confirmar, serão cadastrados 3 espaços.')
        self.assertNotContains(response, 'foram cadastrados')
        self.assertContains(response, 'Não é um espaço novo')

    def test_decision_forms_show_the_refresh_state_while_they_run(self):
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
        response = self.detail(importation)
        self.assertContains(response, 'data-busy-region')
        self.assertContains(response, 'Atualizando a prévia com a decisão.')
        self.assertContains(response, 'data-busy>', count=1)

    def test_pending_item_of_a_similar_name(self):
        Space.objects.register('HV 5')
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (HV5)'}))
        response = self.detail(importation)
        self.assertContains(response, 'Precisa de decisão')
        self.assertContains(response, '1 espaço já cadastrado foi reconhecido.', count=0)
        self.assertContains(response, 'HV5 parece ser HV 5. É o mesmo espaço?')
        self.assertContains(response, 'É o mesmo que HV 5')
        self.assertContains(response, 'É um espaço novo')
        self.assertContains(response, 'Só nas aulas')
        self.assertContains(response, '1 aula · 1 turma · segunda-feira')

    def test_pending_item_of_a_name_only_in_the_cells(self):
        importation = self.upload(workbook_file(undergraduate=TWO_CELL_NAMES))
        response = self.detail(importation)
        self.assertContains(response, '2/41 aparece nas aulas e não está na lista de salas da planilha.')
        self.assertContains(response, 'É o mesmo que outro espaço')
        self.assertContains(response, 'Se for erro de digitação, corrija a planilha e envie de novo.')
        self.assertContains(response, '2 espaços precisam de decisão antes de concluir.')

    def test_importer_only_sees_the_message_without_controls(self):
        importation = self.upload(workbook_file(undergraduate=TWO_CELL_NAMES), user=self.importer)
        response = self.detail(importation, self.importer)
        self.assertContains(response, 'O seu perfil não tem permissão para essa configuração.')
        self.assertNotContains(response, 'É um espaço novo')
        self.assertNotContains(response, reverse('space_allocation_import_decide', args=[importation.pk]))

    def test_importer_only_cannot_confirm_an_import_that_creates_spaces(self):
        importation = self.upload(user=self.importer)
        response = self.detail(importation, self.importer)
        self.assertNotContains(response, 'Confirmar importação')
        self.assertContains(response, 'O seu perfil não tem permissão para essa configuração.')
        response = self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk), follow=True)
        self.assertContains(response, 'O seu perfil não tem permissão para essa configuração.')
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.client.force_login(self.manager)
        response = self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk), follow=True)
        self.assertContains(response, '3 espaços cadastrados.')
        self.assertEqual(Space.objects.count(), 3)

    def test_partial_permission_shows_only_the_allowed_decisions(self):
        Space.objects.register('HV 5')
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (HV5)'}))
        response = self.detail(importation, self.creator)
        self.assertContains(response, 'É um espaço novo')
        self.assertNotContains(response, 'É o mesmo que HV 5')

    def test_import_with_errors_lists_the_names_without_controls(self):
        uploaded = workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'Física (Agnaldo) (1/13)',
            ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (Zoo I)',
        })
        importation = self.upload(uploaded)
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        response = self.detail(importation)
        self.assertContains(response, 'Depois de corrigir a planilha, estes espaços também vão precisar de decisão.')
        self.assertContains(response, 'Zoo I')
        self.assertNotContains(response, 'É um espaço novo')

    def test_concluded_import_lists_the_spaces_it_created(self):
        importation = self.upload()
        response = self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk), follow=True)
        self.assertContains(response, '3 espaços cadastrados.')
        self.assertContains(response, '3 espaços cadastrados por esta importação.')
        self.assertNotContains(response, 'Nenhuma alteração foi feita no cadastro de espaços.')

    def test_import_list_shows_the_decision_status(self):
        self.upload(workbook_file(undergraduate=TWO_CELL_NAMES))
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertContains(response, 'Precisa de decisão')


class AutomaticRefreshTests(PanelTestCase):
    def test_last_decision_refreshes_the_preview(self):
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
        self.assertEqual(importation.status, Import.Status.PENDING)
        response = self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW)
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertContains(response, 'Pronta para confirmar.')
        self.assertContains(response, 'Será cadastrado como espaço novo.')
        self.assertContains(response, 'Alterar decisão')
        self.assertFalse(Space.objects.filter(name='Zoo I').exists())

    def test_intermediate_decision_only_updates_the_panel(self):
        importation = self.upload(workbook_file(undergraduate=TWO_CELL_NAMES))
        response = self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW)
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.PENDING)
        self.assertContains(response, '1 espaço precisa de decisão antes de concluir.')
        row = importation.rows.get(values__Célula='Horário - Graduação!C3')
        self.assertEqual(row.pending, [{'code': 'espaco_a_decidir', 'key': 'Zoo I'}])

    def test_withdrawing_a_decision_brings_back_the_pending(self):
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
        self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW)
        response = self.client.post(
            reverse('space_allocation_import_withdraw', args=[importation.pk]), {'nome': 'Zoo I'}, follow=True,
        )
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.PENDING)
        self.assertContains(response, 'Decisão sobre o espaço Zoo I desfeita.')

    def test_failed_refresh_keeps_the_decision_and_offers_to_try_again(self):
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
        with mock.patch.object(Import, 'refresh', side_effect=RuntimeError('falha')):
            response = self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW)
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.PENDING)
        self.assertTrue(SpaceDecision.objects.filter(found_name='Zoo I').exists())
        self.assertContains(response, 'Não foi possível atualizar a prévia.')
        self.assertContains(response, 'Tentar novamente')
        self.client.post(reverse('space_allocation_import_refresh', args=[importation.pk]))
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertNotContains(self.detail(importation), 'Tentar novamente')

    def test_decision_without_the_permission_is_refused_with_message(self):
        Space.objects.register('HV 5')
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (HV5)'}))
        response = self.decide(
            importation, 'HV5', SpaceDecision.Kind.SAME, user=self.creator, espaco=Space.objects.get(name='HV 5').pk,
        )
        self.assertContains(response, 'O seu perfil não tem permissão para essa configuração.')
        self.assertFalse(SpaceDecision.objects.exists())

    def test_choosing_a_registered_space_in_the_modal(self):
        target = Space.objects.register('Lab. Zootecnia')
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
        url = reverse('space_allocation_import_associate', args=[importation.pk]) + '?nome=Zoo%20I'
        page = self.client.get(url)
        self.assertContains(page, 'Escolher o espaço de Zoo I')
        self.assertContains(page, 'Lab. Zootecnia')
        self.client.post(url, {'espaco': target.pk})
        decision = SpaceDecision.objects.get()
        self.assertEqual((decision.kind, decision.space), ('ASSOCIAR', target))
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)


class DecisionAccessTests(PanelTestCase):
    def routes(self, pk):
        return [
            reverse('space_allocation_import_decide', args=[pk]),
            reverse('space_allocation_import_withdraw', args=[pk]),
            reverse('space_allocation_import_refresh', args=[pk]),
            reverse('space_allocation_import_associate', args=[pk]),
        ]

    def test_anonymous_is_sent_to_the_login(self):
        for url in self.routes(1):
            with self.subTest(url=url):
                response = self.client.post(url)
                self.assertRedirects(response, f"{reverse('account_login')}?next={url}", fetch_redirect_response=False)

    def test_without_the_import_permission(self):
        importation = self.upload()
        self.client.force_login(user_with('espacos@ifnmg.edu.br', *permissions.SPACE_PERMISSIONS))
        for url in self.routes(importation.pk):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 403)

    def test_decision_without_csrf_is_refused(self):
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.manager)
        response = client.post(
            reverse('space_allocation_import_decide', args=[importation.pk]), {'nome': 'Zoo I', 'decisao': 'NOVO'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(SpaceDecision.objects.exists())

    def test_definition_is_the_ensalamento_import(self):
        self.assertIsInstance(SPACE_ALLOCATION_IMPORT_SCREENS.definition, SpaceAllocationImport)
