"""Quadro "Espaços desta importação" e atualização automática da prévia, pelas telas."""

from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts import permissions
from config.testing import IsolatedCasesMixin
from imports.models import Import
from imports.tests.worker import poll, run_worker
from schedule.models import Space, SpaceDecision
from schedule.tests.test_import import PERIOD, workbook_file
from schedule.tests.test_space_import import SECONDARY_CELL, user_with
from schedule.views import SPACE_ALLOCATION_IMPORT_SCREENS

TWO_CELL_NAMES = {
    ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (Zoo I)',
    ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
    ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/41)',
}


class PanelTestCase(IsolatedCasesMixin, TestCase):
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
        run_worker(SPACE_ALLOCATION_IMPORT_SCREENS.definition)
        return Import.objects.latest('pk')

    def submit(self, url, data=None):
        """Envia o POST, deixa o worker executar o que ele pediu e abre a tela para onde ele redireciona."""
        response = self.client.post(url, data or {})
        run_worker(SPACE_ALLOCATION_IMPORT_SCREENS.definition)
        poll(self.client, response.url)
        return self.client.get(response.url)

    def detail(self, importation, user=None):
        self.client.force_login(user or self.manager)
        return self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk))

    def decide(self, importation, name, kind, user=None, **extra):
        self.client.force_login(user or self.manager)
        return self.submit(
            reverse('space_allocation_import_decide', args=[importation.pk]),
            {'nome': name, 'decisao': kind, **extra},
        )


class PanelTests(PanelTestCase):
    def test_panel_describes_what_the_confirmation_does(self):
        with self.case('antes, no futuro'):
            importation = self.upload()
            response = self.detail(importation)
            self.assertContains(response, '4 espaços novos serão cadastrados ao confirmar esta importação.')
            self.assertNotContains(response, 'foram cadastrados')
        with self.case('depois, os criados'):
            importation = self.upload()
            response = self.submit(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk))
            self.assertContains(response, '4 espaços cadastrados.')
            self.assertContains(response, '4 espaços cadastrados por esta importação.')
            self.assertNotContains(response, 'Nenhuma alteração foi feita no cadastro de espaços.')

    def test_pending_items_explain_each_name(self):
        with self.case('nome parecido'):
            Space.objects.register('HV 5')
            importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (HV5)'}))
            response = self.detail(importation)
            self.assertContains(response, 'HV5 parece ser HV 5. É o mesmo espaço?')
            self.assertContains(response, 'É o mesmo que HV 5')
            self.assertContains(response, 'É um espaço novo')
        with self.case('nome só nas células'):
            importation = self.upload(workbook_file(undergraduate=TWO_CELL_NAMES))
            response = self.detail(importation)
            self.assertContains(response, '2/41 aparece nas aulas e não está na lista de salas da planilha.')
            self.assertContains(response, 'É o mesmo que outro espaço')
            self.assertContains(response, 'Se for erro de digitação, corrija a planilha e envie de novo.')
            self.assertContains(response, '2 espaços precisam de decisão antes de concluir.')
        with self.case('importação com erros'):
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

    def test_controls_follow_the_permissions(self):
        with self.case('só importar vê a mensagem'):
            importation = self.upload(workbook_file(undergraduate=TWO_CELL_NAMES), user=self.importer)
            response = self.detail(importation, self.importer)
            self.assertContains(response, 'O seu perfil não tem permissão para essa configuração.')
            self.assertNotContains(response, 'É um espaço novo')
            self.assertNotContains(response, reverse('space_allocation_import_decide', args=[importation.pk]))
        with self.case('só importar não confirma o que cadastra'):
            importation = self.upload(user=self.importer)
            response = self.detail(importation, self.importer)
            self.assertNotContains(response, 'Confirmar importação')
            self.assertContains(response, 'O seu perfil não tem permissão para essa configuração.')
            response = self.submit(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk))
            self.assertContains(response, 'O seu perfil não tem permissão para essa configuração.')
            importation.refresh_from_db()
            self.assertEqual(importation.status, Import.Status.VALIDATED)
            self.client.force_login(self.manager)
            response = self.submit(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk))
            self.assertContains(response, '4 espaços cadastrados.')
            self.assertEqual(Space.objects.count(), 4)
        with self.case('permissão parcial'):
            Space.objects.register('HV 5')
            importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (HV5)'}))
            response = self.detail(importation, self.creator)
            self.assertContains(response, 'É um espaço novo')
            self.assertNotContains(response, 'É o mesmo que HV 5')
        with self.case('decisão sem a permissão'):
            Space.objects.register('HV 5')
            importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (HV5)'}))
            response = self.decide(
                importation, 'HV5', SpaceDecision.Kind.SAME, user=self.creator, espaco=Space.objects.get(name='HV 5').pk,
            )
            self.assertContains(response, 'O seu perfil não tem permissão para essa configuração.')
            self.assertFalse(SpaceDecision.objects.exists())


class AutomaticRefreshTests(PanelTestCase):
    def test_decisions_refresh_the_preview(self):
        with self.case('última decisão'):
            importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
            self.assertEqual(importation.status, Import.Status.PENDING)
            self.assertContains(self.detail(importation), 'id="espacos" data-busy-region open')
            response = self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW)
            importation.refresh_from_db()
            self.assertEqual(importation.status, Import.Status.VALIDATED)
            self.assertContains(response, 'Ao confirmar, serão cadastrados')
            self.assertContains(response, 'Será cadastrado como espaço novo.')
            self.assertContains(response, 'Alterar decisão')
            self.assertFalse(Space.objects.filter(name='Zoo I').exists())
        with self.case('decisão intermediária'):
            importation = self.upload(workbook_file(undergraduate=TWO_CELL_NAMES))
            response = self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW)
            importation.refresh_from_db()
            self.assertEqual(importation.status, Import.Status.PENDING)
            self.assertContains(response, '1 espaço precisa de decisão antes de concluir.')
            row = importation.rows.get(values__Célula='Horário - Graduação!C3')
            self.assertEqual(row.pending, [{'code': 'espaco_a_decidir', 'key': 'Zoo I'}])

    def test_failed_refresh_keeps_the_decision_and_offers_to_try_again(self):
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
        with override_settings(IMPORT_MAX_ATTEMPTS=1), mock.patch.object(Import, 'run_refresh', side_effect=RuntimeError('falha')):
            response = self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW)
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.PENDING)
        self.assertTrue(SpaceDecision.objects.filter(found_name='Zoo I').exists())
        self.assertContains(response, 'Não foi possível atualizar a prévia.')
        self.assertContains(response, 'Tentar novamente')
        self.submit(reverse('space_allocation_import_refresh', args=[importation.pk]))
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertNotContains(self.detail(importation), 'Tentar novamente')

    def test_decision_while_the_refresh_is_pending_is_refused(self):
        importation = self.upload(workbook_file(undergraduate=TWO_CELL_NAMES))
        importation.request_refresh(self.manager)
        response = self.client.post(
            reverse('space_allocation_import_decide', args=[importation.pk]),
            {'nome': 'Zoo I', 'decisao': SpaceDecision.Kind.NEW},
            follow=True,
        )
        self.assertContains(response, 'Esta importação está em processamento e não aceita outra ação até ele terminar.')
        self.assertFalse(SpaceDecision.objects.exists())
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), (Import.Status.PENDING, Import.Operation.REFRESH))
        self.assertNotContains(response, 'É um espaço novo')

    def test_choosing_a_registered_space_in_the_modal(self):
        target = Space.objects.register('Lab. Zootecnia')
        importation = self.upload(workbook_file(secondary={SECONDARY_CELL: 'Biologia (Érica) (Zoo I)'}))
        url = reverse('space_allocation_import_associate', args=[importation.pk]) + '?nome=Zoo%20I'
        page = self.client.get(url)
        self.assertContains(page, 'Escolher o espaço de Zoo I')
        self.assertContains(page, 'Lab. Zootecnia')
        self.client.post(url, {'espaco': target.pk})
        run_worker(SPACE_ALLOCATION_IMPORT_SCREENS.definition)
        decision = SpaceDecision.objects.get()
        self.assertEqual((decision.kind, decision.space), ('ASSOCIAR', target))
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
