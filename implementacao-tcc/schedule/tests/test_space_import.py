"""Espaços na importação de ensalamento: classificação, decisões, permissões e confirmação."""

from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
from imports.models import Import
from imports.tests.worker import confirm, refresh
from schedule.models import Allocation, Space, SpaceDecision
from schedule.spaces import CELLS_ONLY, CREATE, INACTIVE, PENDING, SIMILAR, classify_import
from schedule.tests.test_import import CONTENT_TYPE, ImportTestCase, space_manager, workbook_file

FIXTURES = Path(__file__).parent / 'fixtures'
CORRECTED = 'planilha_example_sugerida_corrigida.xlsx'
SECONDARY_CELL = ('SEGUNDA-FEIRA', '13:20 - 14:10', 0)


def user_with(email, *codes):
    code = email.partition('@')[0].upper()
    role = Role.objects.create_role(code=code, name=code, permissions=codes)
    return User.objects.register(email=email, name=code.capitalize(), role=role)


def secondary(text):
    """Planilha de teste com a atividade do ensino médio trocada pelo texto dado."""
    return workbook_file(secondary={SECONDARY_CELL: text})


def real(name):
    return SimpleUploadedFile(name, (FIXTURES / name).read_bytes(), content_type=CONTENT_TYPE)


class SpaceImportTestCase(ImportTestCase):
    def setUp(self):
        super().setUp()
        self.importer_only = user_with('importador@ifnmg.edu.br', permissions.SPACE_ALLOCATION_IMPORT)
        self.creator = user_with('cadastro@ifnmg.edu.br', permissions.SPACE_ALLOCATION_IMPORT, permissions.SPACE_CREATE)

    def entry(self, importation, name):
        return classify_import(importation).found[name.casefold()]

    def decide(self, importation, name, kind, user=None, **target):
        SpaceDecision.objects.decide(importation, name, kind, user or self.executor, **target)
        refresh(importation, self.definition, user or self.executor)
        return importation


class ClassificationTests(SpaceImportTestCase):
    def test_first_import_of_the_corrected_spreadsheet_proposes_every_listed_space(self):
        """A planilha corrigida traz a aba de usuários, e cadastrá-los exige `USUARIO.CRIAR`."""
        self.executor = space_manager('completo@ifnmg.edu.br', extra_permissions=[permissions.USER_CREATE, permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST])
        importation = self.preview(real(CORRECTED))
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        resolution = classify_import(importation)
        self.assertEqual(len(resolution.proposed), 85)
        self.assertEqual(resolution.pending, [])
        self.assertNotIn('lab. química', resolution.found)
        self.assertFalse(Space.objects.exists())
        self.assertTrue(confirm(importation, self.definition, self.executor))
        self.assertEqual(Space.objects.count(), 85)
        self.assertEqual(set(Space.objects.values_list('origin', 'source_import')), {('PLANILHA', importation.pk)})
        again = self.preview(real(CORRECTED))
        resolution = classify_import(again)
        self.assertEqual((len(resolution.to_create), len(resolution.pending), len(resolution.recognized)), (0, 0, 85))

    def test_first_import_of_the_original_spreadsheet(self):
        importation = self.preview(real('planilha_example.xlsx'))
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        resolution = classify_import(importation)
        self.assertEqual(
            {entry.name for entry in resolution.pending},
            {'HV1', 'HV3', 'HV4', 'HV5', 'Zoo I', 'EaD', '2/41', 'Lab. Química'},
        )
        proposed = {entry.name for entry in resolution.proposed}
        self.assertLessEqual({'HV 1', 'HV 3', 'HV 4'}, proposed)
        self.assertEqual([candidate.name for candidate in resolution.found['hv1'].candidates], ['HV 1'])
        self.assertEqual(resolution.found['2/41'].reason, CELLS_ONLY)

    def test_registered_active_space_is_recognized(self):
        with self.case('pelo outro nome'):
            space = Space.objects.register('HV 5', other_names=['HV5'])
            importation = self.conclude(secondary('Biologia (Érica) (HV5)'))
            self.assertEqual(Allocation.objects.get(subject__name='Biologia').space, space)
            self.assertEqual(space.other_names, ['HV5'])
            self.assertIsNone(Space.objects.get(pk=space.pk).source_import)
            self.assertEqual(self.entry(importation, 'HV5').outcome, 'reconhecido')
        with self.case('ativo e sem aulas'):
            space = Space.objects.register('Lab. de Madeira')
            importation = self.preview()
            self.assertEqual(self.entry(importation, 'Lab. de Madeira').outcome, 'reconhecido')
            row = importation.rows.get(values__Nome='Lab. de Madeira')
            self.assertEqual((row.action, row.target), ('unchanged', str(space.pk)))

    def test_inactive_space_is_never_reactivated_without_a_decision(self):
        with self.case('com aulas, pede decisão'):
            space = Space.objects.register('HV 3')
            space.deactivate()
            importation = self.preview()
            self.assertEqual(importation.status, Import.Status.PENDING)
            entry = self.entry(importation, 'HV 3')
            self.assertEqual((entry.outcome, entry.reason), (PENDING, INACTIVE))
            self.assertFalse(Space.objects.get(pk=space.pk).is_active)
        with self.case('sem aulas, continua inativo'):
            space = Space.objects.register('Lab. de Madeira')
            space.deactivate()
            importation = self.preview()
            self.assertEqual(importation.status, Import.Status.VALIDATED)
            self.assertNotIn('lab. de madeira', classify_import(importation).found)
            row = importation.rows.get(values__Nome='Lab. de Madeira')
            self.assertEqual((row.action, row.warnings, row.pending), (None, [], []))
            self.assertTrue(confirm(importation, self.definition, self.executor))
            self.assertFalse(Space.objects.get(pk=space.pk).is_active)

    def test_ambiguous_or_unlisted_names_need_a_decision(self):
        with self.case('vários nomes parecidos'):
            Space.objects.register('Lab. Química I')
            Space.objects.register('Lab. Química II')
            uploaded = workbook_file(
                spaces=['(1/13)', '(2/6)', '(HV 3)', '(Lab. Química)'],
                secondary={SECONDARY_CELL: 'Biologia (Érica) (Lab. Química)'},
            )
            entry = self.entry(self.preview(uploaded), 'Lab. Química')
            self.assertEqual((entry.outcome, entry.reason), (PENDING, SIMILAR))
            self.assertEqual({candidate.name for candidate in entry.candidates}, {'Lab. Química I', 'Lab. Química II'})
        with self.case('espaço listado sem aulas'):
            uploaded = workbook_file(
                spaces=['(1/13)', '(2/6)', '(HV 3)', '(Lab. Química I)', '(Lab. Química)'],
                secondary={SECONDARY_CELL: 'Biologia (Érica) (Lab. Química I)'},
            )
            importation = self.preview(uploaded)
            self.assertEqual(self.entry(importation, 'Lab. Química I').outcome, CREATE)
            entry = self.entry(importation, 'Lab. Química')
            self.assertEqual((entry.outcome, entry.reason), (PENDING, SIMILAR))
            self.assertEqual([candidate.name for candidate in entry.candidates], ['Lab. Química I'])
            row = importation.rows.get(values__Nome='(Lab. Química)')
            self.assertEqual(row.pending, [{'code': 'espaco_a_decidir', 'key': 'Lab. Química'}])
        with self.case('nome só nas células'):
            importation = self.preview(secondary('Biologia (Érica) (Zoo I)'))
            entry = self.entry(importation, 'Zoo I')
            self.assertEqual((entry.outcome, entry.reason, entry.from_list), (PENDING, CELLS_ONLY, False))
            self.assertEqual(entry.usage.lessons, 1)


class DecisionTests(SpaceImportTestCase):
    def test_associate_to_an_existing_space(self):
        space = Space.objects.register('HV 5')
        importation = self.preview(secondary('Biologia (Érica) (HV5)'))
        self.assertEqual(importation.status, Import.Status.PENDING)
        self.decide(importation, 'HV5', SpaceDecision.Kind.SAME, space=space)
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertEqual(Space.objects.get(pk=space.pk).other_names, [])
        decision_record = AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION_IMPORT, action=catalog.UPDATE).get()
        self.assertEqual(decision_record.new_values, {'nome_encontrado': 'HV5', 'decisao': 'ASSOCIAR', 'espaco': 'HV 5'})
        self.assertTrue(confirm(importation, self.definition, self.executor))
        space.refresh_from_db()
        self.assertEqual((space.other_names, space.origin), (['HV5'], 'MANUAL'))
        self.assertEqual(Allocation.objects.get(subject__name='Biologia').space, space)
        record = AuditLog.objects.filter(resource=catalog.SPACE, action=catalog.UPDATE).get()
        self.assertEqual((record.origin, record.user), (catalog.IMPORTED, self.executor))
        self.assertEqual(record.metadata, {'importacao': importation.pk, 'decidido_por': self.executor.email})
        summary = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk').metadata
        self.assertEqual(summary['outros_nomes_associados'], 1)
        self.assertEqual(self.entry(self.preview(secondary('Biologia (Érica) (HV5)')), 'HV5').outcome, 'reconhecido')

    def test_new_space_or_a_name_of_the_same_import(self):
        with self.case('espaço novo para um nome só nas células'):
            importation = self.preview(secondary('Biologia (Érica) (Zoo I)'))
            self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW, user=self.creator)
            self.assertFalse(Space.objects.filter(name='Zoo I').exists())
            self.assertTrue(confirm(importation, self.definition, self.creator))
            space = Space.objects.get(name='Zoo I')
            self.assertEqual((space.origin, space.source_import), ('PLANILHA', importation))
            record = AuditLog.objects.get(resource=catalog.SPACE, action=catalog.CREATE, resource_id=str(space.pk))
            self.assertEqual(record.metadata['decidido_por'], self.creator.email)
        with self.case('outro nome da mesma importação'):
            uploaded = workbook_file(
                undergraduate={('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (HV3)'},
                secondary={SECONDARY_CELL: 'Biologia (Érica) (HV 3)'},
            )
            importation = self.preview(uploaded)
            entry = self.entry(importation, 'HV3')
            self.assertEqual([candidate.found_key for candidate in entry.candidates], ['hv 3'])
            self.assertEqual(self.entry(importation, 'HV 3').outcome, CREATE)
            self.decide(importation, 'HV3', SpaceDecision.Kind.SAME, user=self.creator, target_name='HV 3')
            self.assertTrue(confirm(importation, self.definition, self.creator))
            space = Space.objects.get(name='HV 3')
            self.assertEqual(space.other_names, ['HV3'])
            self.assertEqual(set(Allocation.objects.values_list('space', flat=True)), {space.pk})

    def test_inactive_space_is_reactivated_only_by_its_decision(self):
        with self.case('o nome atual só aceita reativar'):
            space = Space.objects.register('HV 3')
            space.deactivate()
            importation = self.preview()
            with self.assertRaises(ValidationError):
                SpaceDecision.objects.decide(importation, 'HV 3', SpaceDecision.Kind.NEW, self.executor)
            self.assertFalse(SpaceDecision.objects.exists())
        with self.case('reativação'):
            space = Space.objects.register('HV 3')
            space.deactivate()
            importation = self.decide(self.preview(), 'HV 3', SpaceDecision.Kind.REACTIVATE)
            self.assertEqual(importation.status, Import.Status.VALIDATED)
            self.assertFalse(Space.objects.get(pk=space.pk).is_active)
            self.assertTrue(confirm(importation, self.definition, self.executor))
            self.assertTrue(Space.objects.get(pk=space.pk).is_active)
            summary = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk').metadata
            self.assertEqual(summary['espacos_reativados'], 1)

    def test_decisions_are_withdrawn_with_the_pending_and_refused_on_final_imports(self):
        with self.case('decisão retirada'):
            importation = self.decide(self.preview(secondary('Biologia (Érica) (Zoo I)')), 'Zoo I', SpaceDecision.Kind.NEW)
            self.assertEqual(importation.status, Import.Status.VALIDATED)
            SpaceDecision.objects.withdraw(importation, 'zoo i', self.executor)
            self.assertEqual(refresh(importation, self.definition, self.executor), Import.Status.PENDING)
            self.assertEqual(self.entry(importation, 'Zoo I').outcome, PENDING)
        with self.case('descarte e exclusão'):
            importation = self.decide(self.preview(secondary('Biologia (Érica) (Zoo I)')), 'Zoo I', SpaceDecision.Kind.NEW)
            importation.discard(self.definition, self.executor)
            self.assertFalse(Space.objects.exists())
            importation.remove(self.definition, self.executor)
            self.assertFalse(SpaceDecision.objects.exists())
            self.assertFalse(Space.objects.exists())
        with self.case('importação concluída'):
            importation = self.conclude()
            with self.assertRaises(ValidationError):
                SpaceDecision.objects.decide(importation, 'HV 3', SpaceDecision.Kind.NEW, self.executor)

    def test_recognition_prevails_over_an_old_decision(self):
        importation = self.decide(self.preview(secondary('Biologia (Érica) (Sala 101)')), 'Sala 101', SpaceDecision.Kind.NEW)
        manual = Space.objects.register('Sala 101')
        self.assertFalse(confirm(importation, self.definition, self.executor))
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertTrue(confirm(importation, self.definition, self.executor))
        self.assertEqual(Space.objects.filter(name__iexact='Sala 101').count(), 1)
        self.assertEqual(Allocation.objects.get(subject__name='Biologia').space, manual)

    def test_two_imports_proposing_the_same_space_create_it_once(self):
        first = self.preview()
        second = self.preview(semester='2026/2')
        self.assertTrue(confirm(first, self.definition, self.executor))
        self.assertFalse(confirm(second, self.definition, self.executor))
        self.assertTrue(confirm(second, self.definition, self.executor))
        self.assertEqual(sorted(Space.objects.values_list('name', flat=True)), ['1/13', '2/6', 'HV 3', 'Lab. de Madeira'])


class PermissionTests(SpaceImportTestCase):
    def test_confirmation_needs_the_permissions_of_what_changes_the_registry(self):
        with self.case('só importar não cadastra espaços'):
            importation = self.preview()
            with self.assertRaisesMessage(ValidationError, 'O seu perfil não tem permissão para essa configuração.'):
                confirm(importation, self.definition, self.importer_only)
            importation.refresh_from_db()
            self.assertEqual((importation.status, importation.revalidation_count), (Import.Status.VALIDATED, 0))
            self.assertFalse(Space.objects.exists())
            self.assertTrue(confirm(importation, self.definition, self.creator))
            self.assertEqual(Space.objects.count(), 4)
        with self.case('só importar basta sem mudança no cadastro'):
            self.conclude()
            self.assertTrue(confirm(self.preview(), self.definition, self.importer_only))
        with self.case('reativar exige a permissão da situação'):
            space = Space.objects.register('HV 3')
            space.deactivate()
            importation = self.decide(self.preview(), 'HV 3', SpaceDecision.Kind.REACTIVATE)
            with self.assertRaises(ValidationError):
                confirm(importation, self.definition, self.creator)
            self.assertFalse(Space.objects.get(pk=space.pk).is_active)

    def test_decision_without_the_permission_is_refused(self):
        space = Space.objects.register('HV 5')
        importation = self.preview(secondary('Biologia (Érica) (HV5)'))
        with self.assertRaises(ValidationError):
            SpaceDecision.objects.decide(importation, 'HV5', SpaceDecision.Kind.SAME, self.creator, space=space)
        with self.assertRaises(ValidationError):
            SpaceDecision.objects.decide(importation, 'HV5', SpaceDecision.Kind.NEW, self.importer_only)
        self.assertFalse(SpaceDecision.objects.exists())
        SpaceDecision.objects.decide(importation, 'HV5', SpaceDecision.Kind.NEW, self.creator)
        self.assertEqual(SpaceDecision.objects.get().kind, 'NOVO')
