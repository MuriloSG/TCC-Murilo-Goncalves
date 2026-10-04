from datetime import time
from importlib import import_module

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from audit import catalog
from audit.models import AuditLog
from imports.models import Import
from schedule.models import (
    ClassGroup,
    Course,
    Semester,
    Space,
    SpaceDecision,
    SpaceName,
    SpaceOrigin,
    Stage,
    Weekday,
)
from schedule.tests.test_timetable import allocate

adoption = import_module('schedule.migrations.0004_adopt_existing_spaces')


def space_records(action):
    return AuditLog.objects.filter(resource=catalog.SPACE, action=action)


def allocation_in(space):
    semester, _ = Semester.objects.resolve('2026/2')
    course, _ = Course.objects.resolve('Eng. Florestal', stage=Stage.UNDERGRADUATE)
    group, _ = ClassGroup.objects.resolve(course, '6º período')
    return allocate(semester, group, 'Patologia Florestal', Weekday.MONDAY, time(7, 20), time(8, 10), space=space.name)


class RegisterTests(TestCase):
    def test_manual_space_is_active_with_its_names_and_audited(self):
        space = Space.objects.register('  Sala   101 ', other_names=['S101', 's101', '', 'Sala 101'])
        self.assertEqual((space.name, space.origin, space.source_import, space.is_active), ('Sala 101', 'MANUAL', None, True))
        self.assertEqual(space.other_names, ['S101'])
        record = space_records(catalog.CREATE).get()
        self.assertEqual(record.resource_id, str(space.pk))
        self.assertEqual(
            record.new_values, {'name': 'Sala 101', 'outros_nomes': ['S101'], 'origem': 'MANUAL', 'importacao': None},
        )

    def test_found_by_other_name_without_case(self):
        space = Space.objects.register('HV 5', other_names=['HV5'])
        self.assertEqual(Space.objects.named('hv5'), space)
        self.assertEqual(Space.objects.named(' HV  5 '), space)
        self.assertIsNone(Space.objects.named('HV 4'))

    def test_name_used_as_other_name_is_refused(self):
        Space.objects.register('HV 5', other_names=['HV5'])
        with self.assertRaises(ValidationError) as context:
            Space.objects.register('hv5')
        self.assertEqual(context.exception.message_dict, {'name': ['Já existe um espaço com este nome.']})
        self.assertEqual(Space.objects.count(), 1)

    def test_other_name_of_another_space_is_refused_citing_it(self):
        Space.objects.register('HV 4')
        with self.assertRaises(ValidationError) as context:
            Space.objects.register('HV 5', other_names=['hv 4'])
        self.assertEqual(context.exception.message_dict, {'other_names': ['Já existe um espaço com o nome hv 4.']})
        self.assertFalse(space_records(catalog.CREATE).filter(new_values__name='HV 5').exists())

    def test_database_guarantees_a_single_space_per_name(self):
        first = Space.objects.register('HV 4')
        second = Space.objects.register('HV 5')
        with self.assertRaises(IntegrityError), transaction.atomic():
            SpaceName.objects.create(space=second, name='hv 4')
        self.assertEqual(Space.objects.named('HV 4'), first)

    def test_spreadsheet_origin_keeps_the_import(self):
        user = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        importation = Import.objects.create(kind='ENSALAMENTO', status='CONCLUIDA', file_name='a.xlsx', created_by=user)
        space = Space.objects.register('Zoo I', origin=SpaceOrigin.SPREADSHEET, source_import=importation)
        self.assertEqual((space.origin, space.source_import), ('PLANILHA', importation))
        self.assertEqual(space_records(catalog.CREATE).get().new_values['importacao'], importation.pk)


class UpdateTests(TestCase):
    def test_rename_keeps_the_previous_name(self):
        space = Space.objects.register('HV 5', other_names=['HV5'])
        space.update_details('Sala HV 05', ['HV5'])
        self.assertEqual((space.name, space.other_names), ('Sala HV 05', ['HV 5', 'HV5']))
        self.assertEqual(Space.objects.named('HV 5'), space)
        record = space_records(catalog.UPDATE).get()
        self.assertEqual(record.old_values, {'name': 'HV 5', 'outros_nomes': ['HV5']})
        self.assertEqual(record.new_values, {'name': 'Sala HV 05', 'outros_nomes': ['HV 5', 'HV5']})

    def test_other_name_promoted_to_current(self):
        space = Space.objects.register('HV 5', other_names=['HV5'])
        space.update_details('HV5', ['HV5'])
        self.assertEqual((space.name, space.other_names), ('HV5', ['HV 5']))

    def test_other_name_removed(self):
        space = Space.objects.register('HV 5', other_names=['HV5'])
        space.update_details('HV 5', [])
        self.assertEqual(space.other_names, [])
        self.assertIsNone(Space.objects.named('HV5'))

    def test_name_of_another_space_is_refused(self):
        Space.objects.register('HV 4')
        space = Space.objects.register('HV 5')
        for name, others in (('hv 4', []), ('HV 5', ['HV 4'])):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                space.update_details(name, others)
        space.refresh_from_db()
        self.assertEqual((space.name, space.other_names), ('HV 5', []))

    def test_origin_status_and_allocations_do_not_change(self):
        space = Space.objects.register('3/8')
        allocation = allocation_in(space)
        space.deactivate()
        space.update_details('Sala 3/8', [])
        space.refresh_from_db()
        allocation.refresh_from_db()
        self.assertEqual((space.origin, space.source_import, space.is_active), ('MANUAL', None, False))
        self.assertEqual(allocation.space, space)

    def test_nothing_changed_records_nothing(self):
        space = Space.objects.register('HV 5', other_names=['HV5'])
        space.update_details('HV 5', ['hv5'])
        self.assertFalse(space_records(catalog.UPDATE).exists())

    def test_names_added_and_removed_for_the_import_with_metadata(self):
        space = Space.objects.register('HV 5')
        space.add_name('HV5', metadata={'importacao': 7})
        self.assertEqual(space.other_names, ['HV5'])
        space.remove_name('hv5', metadata={'importacao': 8})
        self.assertEqual(space.other_names, [])
        self.assertEqual(
            list(space_records(catalog.UPDATE).order_by('pk').values_list('metadata', flat=True)),
            [{'importacao': 7}, {'importacao': 8}],
        )


class StatusTests(TestCase):
    def test_deactivate_and_reactivate(self):
        space = Space.objects.register('1/10')
        allocation = allocation_in(space)
        space.deactivate()
        self.assertFalse(space.is_active)
        allocation.refresh_from_db()
        self.assertEqual(allocation.space, space)
        space.reactivate()
        self.assertTrue(space.is_active)
        self.assertEqual(space_records(catalog.DEACTIVATE).count(), 1)
        self.assertEqual(space_records(catalog.ACTIVATE).count(), 1)

    def test_same_status_changes_nothing(self):
        space = Space.objects.register('1/10')
        space.reactivate()
        space.deactivate()
        space.deactivate()
        self.assertEqual(space_records(catalog.ACTIVATE).count(), 0)
        self.assertEqual(space_records(catalog.DEACTIVATE).count(), 1)


class DeleteTests(TestCase):
    def test_space_without_classes_is_deleted_with_names_and_decisions(self):
        user = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        importation = Import.objects.create(kind='ENSALAMENTO', status='PENDENTE', file_name='a.xlsx', created_by=user)
        space = Space.objects.register('Sala Teste', other_names=['ST'])
        SpaceDecision.objects.create(
            importation=importation, found_name='S. Teste', kind='ASSOCIAR', space=space, decided_by=user,
        )
        self.assertTrue(space.is_deletable)
        space.delete_space()
        self.assertFalse(Space.objects.exists())
        self.assertFalse(SpaceName.objects.exists())
        self.assertFalse(SpaceDecision.objects.exists())
        record = space_records(catalog.DELETE).get()
        self.assertEqual(record.old_values, {'name': 'Sala Teste', 'outros_nomes': ['ST'], 'origem': 'MANUAL'})

    def test_space_with_classes_is_not_deleted(self):
        space = Space.objects.register('1/10')
        allocation_in(space)
        self.assertFalse(space.is_deletable)
        with self.assertRaisesMessage(ValidationError, 'O espaço 1/10 tem aulas no ensalamento e não pode ser excluído.'):
            space.delete_space()
        self.assertTrue(Space.objects.filter(pk=space.pk).exists())
        self.assertFalse(space_records(catalog.DELETE).exists())
