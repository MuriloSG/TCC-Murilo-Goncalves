"""Espaços na importação de ensalamento: classificação, decisões, permissões e confirmação.

Os testes percorrem a importação real, pelo motor de `imports`, com planilhas montadas pelo
`workbook_file` e com as duas planilhas de exemplo do campus.
"""


from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
from imports.models import Import
from schedule.models import Allocation, Space, SpaceDecision
from schedule.spaces import CELLS_ONLY, CREATE, INACTIVE, PENDING, SIMILAR, classify_import
from schedule.tests.test_import import CONTENT_TYPE, ImportTestCase, workbook_file

SOURCES = settings.BASE_DIR / 'sources'
SECONDARY_CELL = ('SEGUNDA-FEIRA', '13:20 - 14:10', 0)


def user_with(email, *codes):
    code = email.partition('@')[0].upper()
    role = Role.objects.create_role(code=code, name=code, permissions=codes)
    return User.objects.register(email=email, name=code.capitalize(), role=role)


def secondary(text):
    """Planilha de teste com a atividade do ensino médio trocada pelo texto dado."""
    return workbook_file(secondary={SECONDARY_CELL: text})


def real(name):
    return SimpleUploadedFile(name, (SOURCES / name).read_bytes(), content_type=CONTENT_TYPE)


class SpaceImportTestCase(ImportTestCase):
    def setUp(self):
        super().setUp()
        self.importer_only = user_with('importador@ifnmg.edu.br', permissions.SPACE_ALLOCATION_IMPORT)
        self.creator = user_with('cadastro@ifnmg.edu.br', permissions.SPACE_ALLOCATION_IMPORT, permissions.SPACE_CREATE)

    def entry(self, importation, name):
        return classify_import(importation).found[name.casefold()]

    def decide(self, importation, name, kind, user=None, **target):
        SpaceDecision.objects.decide(importation, name, kind, user or self.executor, **target)
        importation.refresh(self.definition, user or self.executor)
        return importation


class ClassificationTests(SpaceImportTestCase):
    def test_first_import_of_the_corrected_spreadsheet_proposes_every_listed_space(self):
        importation = self.preview(real('planilha_example_corrigida.xlsx'))
        self.assertEqual(importation.status, Import.Status.PENDING)
        resolution = classify_import(importation)
        self.assertEqual(len(resolution.proposed), 85)
        self.assertEqual([entry.name for entry in resolution.pending], ['Lab. Química'])
        self.assertEqual(resolution.found['lab. química'].usage.lessons, 0)
        self.assertFalse(Space.objects.exists())
        self.decide(importation, 'Lab. Química', SpaceDecision.Kind.NEW)
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertTrue(importation.confirm(self.definition, self.executor))
        self.assertEqual(Space.objects.count(), 86)
        self.assertEqual(set(Space.objects.values_list('origin', 'source_import')), {('PLANILHA', importation.pk)})
        again = self.preview(real('planilha_example_corrigida.xlsx'))
        resolution = classify_import(again)
        self.assertEqual((len(resolution.to_create), len(resolution.pending), len(resolution.recognized)), (0, 0, 86))

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

    def test_other_name_is_recognized(self):
        space = Space.objects.register('HV 5', other_names=['HV5'])
        importation = self.conclude(secondary('Biologia (Érica) (HV5)'))
        self.assertEqual(Allocation.objects.get(subject__name='Biologia').space, space)
        self.assertEqual(space.other_names, ['HV5'])
        self.assertIsNone(Space.objects.get(pk=space.pk).source_import)
        self.assertEqual(self.entry(importation, 'HV5').outcome, 'reconhecido')

    def test_inactive_space_needs_decision_and_is_not_reactivated(self):
        space = Space.objects.register('HV 3')
        space.deactivate()
        importation = self.preview()
        self.assertEqual(importation.status, Import.Status.PENDING)
        entry = self.entry(importation, 'HV 3')
        self.assertEqual((entry.outcome, entry.reason), (PENDING, INACTIVE))
        self.assertFalse(Space.objects.get(pk=space.pk).is_active)

    def test_several_similar_names_are_not_associated(self):
        Space.objects.register('Lab. Química I')
        Space.objects.register('Lab. Química II')
        uploaded = workbook_file(
            spaces=['(1/13)', '(2/6)', '(HV 3)', '(Lab. Química)'],
            secondary={SECONDARY_CELL: 'Biologia (Érica) (Lab. Química)'},
        )
        entry = self.entry(self.preview(uploaded), 'Lab. Química')
        self.assertEqual((entry.outcome, entry.reason), (PENDING, SIMILAR))
        self.assertEqual({candidate.name for candidate in entry.candidates}, {'Lab. Química I', 'Lab. Química II'})

    def test_name_only_in_the_cells_needs_decision_even_without_similar(self):
        importation = self.preview(secondary('Biologia (Érica) (Zoo I)'))
        entry = self.entry(importation, 'Zoo I')
        self.assertEqual((entry.outcome, entry.reason, entry.from_list), (PENDING, CELLS_ONLY, False))
        self.assertEqual(entry.usage.lessons, 1)

    def test_listed_space_without_lessons_does_not_make_used_names_ambiguous(self):
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

    def test_inactive_space_without_lessons_stays_inactive(self):
        space = Space.objects.register('Lab. de Madeira')
        space.deactivate()
        importation = self.preview()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertNotIn('lab. de madeira', classify_import(importation).found)
        row = importation.rows.get(values__Nome='Lab. de Madeira')
        self.assertEqual((row.action, row.warnings, row.pending), (None, [], []))
        self.assertTrue(importation.confirm(self.definition, self.executor))
        self.assertFalse(Space.objects.get(pk=space.pk).is_active)

    def test_active_space_without_lessons_is_recognized(self):
        space = Space.objects.register('Lab. de Madeira')
        importation = self.preview()
        self.assertEqual(self.entry(importation, 'Lab. de Madeira').outcome, 'reconhecido')
        row = importation.rows.get(values__Nome='Lab. de Madeira')
        self.assertEqual((row.action, row.target), ('unchanged', str(space.pk)))


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
        self.assertTrue(importation.confirm(self.definition, self.executor))
        space.refresh_from_db()
        self.assertEqual((space.other_names, space.origin), (['HV5'], 'MANUAL'))
        self.assertEqual(Allocation.objects.get(subject__name='Biologia').space, space)
        record = AuditLog.objects.filter(resource=catalog.SPACE, action=catalog.UPDATE).get()
        self.assertEqual((record.origin, record.user), (catalog.IMPORTED, self.executor))
        self.assertEqual(record.metadata, {'importacao': importation.pk, 'decidido_por': self.executor.email})
        summary = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk').metadata
        self.assertEqual(summary['outros_nomes_associados'], 1)
        self.assertEqual(self.entry(self.preview(secondary('Biologia (Érica) (HV5)')), 'HV5').outcome, 'reconhecido')

    def test_new_space_for_a_name_only_in_the_cells(self):
        importation = self.preview(secondary('Biologia (Érica) (Zoo I)'))
        self.decide(importation, 'Zoo I', SpaceDecision.Kind.NEW, user=self.creator)
        self.assertFalse(Space.objects.filter(name='Zoo I').exists())
        self.assertTrue(importation.confirm(self.definition, self.creator))
        space = Space.objects.get(name='Zoo I')
        self.assertEqual((space.origin, space.source_import), ('PLANILHA', importation))
        record = AuditLog.objects.get(resource=catalog.SPACE, action=catalog.CREATE, resource_id=str(space.pk))
        self.assertEqual(record.metadata['decidido_por'], self.creator.email)

    def test_associate_to_a_name_of_the_same_import(self):
        uploaded = workbook_file(
            undergraduate={('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (HV3)'},
            secondary={SECONDARY_CELL: 'Biologia (Érica) (HV 3)'},
        )
        importation = self.preview(uploaded)
        entry = self.entry(importation, 'HV3')
        self.assertEqual([candidate.found_key for candidate in entry.candidates], ['hv 3'])
        self.assertEqual(self.entry(importation, 'HV 3').outcome, CREATE)
        self.decide(importation, 'HV3', SpaceDecision.Kind.SAME, user=self.creator, target_name='HV 3')
        self.assertTrue(importation.confirm(self.definition, self.creator))
        space = Space.objects.get(name='HV 3')
        self.assertEqual(space.other_names, ['HV3'])
        self.assertEqual(set(Allocation.objects.values_list('space', flat=True)), {space.pk})

    def test_reactivation(self):
        space = Space.objects.register('HV 3')
        space.deactivate()
        importation = self.decide(self.preview(), 'HV 3', SpaceDecision.Kind.REACTIVATE)
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertFalse(Space.objects.get(pk=space.pk).is_active)
        self.assertTrue(importation.confirm(self.definition, self.executor))
        self.assertTrue(Space.objects.get(pk=space.pk).is_active)
        summary = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk').metadata
        self.assertEqual(summary['espacos_reativados'], 1)

    def test_current_name_of_an_inactive_space_only_accepts_reactivation(self):
        space = Space.objects.register('HV 3')
        space.deactivate()
        importation = self.preview()
        with self.assertRaises(ValidationError):
            SpaceDecision.objects.decide(importation, 'HV 3', SpaceDecision.Kind.NEW, self.executor)
        self.assertFalse(SpaceDecision.objects.exists())

    def test_withdrawn_decision_brings_back_the_pending(self):
        importation = self.decide(self.preview(secondary('Biologia (Érica) (Zoo I)')), 'Zoo I', SpaceDecision.Kind.NEW)
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        SpaceDecision.objects.withdraw(importation, 'zoo i', self.executor)
        self.assertEqual(importation.refresh(self.definition, self.executor), Import.Status.PENDING)
        self.assertEqual(self.entry(importation, 'Zoo I').outcome, PENDING)

    def test_recognition_prevails_over_an_old_decision(self):
        importation = self.decide(self.preview(secondary('Biologia (Érica) (Sala 101)')), 'Sala 101', SpaceDecision.Kind.NEW)
        manual = Space.objects.register('Sala 101')
        self.assertFalse(importation.confirm(self.definition, self.executor))
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertTrue(importation.confirm(self.definition, self.executor))
        self.assertEqual(Space.objects.filter(name__iexact='Sala 101').count(), 1)
        self.assertEqual(Allocation.objects.get(subject__name='Biologia').space, manual)

    def test_decision_on_a_final_import_is_refused(self):
        importation = self.conclude()
        with self.assertRaises(ValidationError):
            SpaceDecision.objects.decide(importation, 'HV 3', SpaceDecision.Kind.NEW, self.executor)

    def test_discard_and_delete_leave_the_registry_untouched(self):
        importation = self.decide(self.preview(secondary('Biologia (Érica) (Zoo I)')), 'Zoo I', SpaceDecision.Kind.NEW)
        importation.discard(self.definition, self.executor)
        self.assertFalse(Space.objects.exists())
        importation.remove(self.definition, self.executor)
        self.assertFalse(SpaceDecision.objects.exists())
        self.assertFalse(Space.objects.exists())

    def test_two_imports_proposing_the_same_space_create_it_once(self):
        first = self.preview()
        second = self.preview(semester='2026/2')
        self.assertTrue(first.confirm(self.definition, self.executor))
        self.assertFalse(second.confirm(self.definition, self.executor))
        self.assertTrue(second.confirm(self.definition, self.executor))
        self.assertEqual(sorted(Space.objects.values_list('name', flat=True)), ['1/13', '2/6', 'HV 3', 'Lab. de Madeira'])


class PermissionTests(SpaceImportTestCase):
    def test_importer_only_cannot_confirm_what_changes_the_registry(self):
        importation = self.preview()
        with self.assertRaisesMessage(ValidationError, 'O seu perfil não tem permissão para essa configuração.'):
            importation.confirm(self.definition, self.importer_only)
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.revalidation_count), (Import.Status.VALIDATED, 0))
        self.assertFalse(Space.objects.exists())
        self.assertTrue(importation.confirm(self.definition, self.creator))
        self.assertEqual(Space.objects.count(), 4)

    def test_importer_only_concludes_when_the_registry_does_not_change(self):
        self.conclude()
        self.assertTrue(self.preview().confirm(self.definition, self.importer_only))

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

    def test_reactivation_requires_the_status_permission_to_confirm(self):
        space = Space.objects.register('HV 3')
        space.deactivate()
        importation = self.decide(self.preview(), 'HV 3', SpaceDecision.Kind.REACTIVATE)
        with self.assertRaises(ValidationError):
            importation.confirm(self.definition, self.creator)
        self.assertFalse(Space.objects.get(pk=space.pk).is_active)
