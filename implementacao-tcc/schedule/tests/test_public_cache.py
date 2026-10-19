"""Cache público das telas abertas: chaves, leitura, indisponibilidade, invalidação depois do commit e cabeçalhos."""

import re
from datetime import date, time
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.cache import caches
from django.core.management import call_command
from django.db import connection, transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from accounts.models import User
from bookings.models import Booking, SlotUnavailable
from bookings.tests.base import REQUESTER, REVIEWER, frozen_clock, semester_with_lesson, space, submit, user_with
from config.cache import JsonSerializer, TolerantRedisCache
from imports.forms import ImportUploadForm
from imports.tests.worker import confirm, preview
from schedule import public_cache
from schedule.imports import SpaceAllocationImport
from schedule.models import Allocation, ClassOffering, Course, Space, Stage, Teacher
from schedule.tests.test_import import PERIOD, space_manager, workbook_file
from schedule.tests.test_public_calendar import TODAY, PublicCalendarTestCase

LOCMEM = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
    'public': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'public-tests'},
}

CALENDAR = reverse('public_calendar')
ORIGINAL = reverse('public_original_timetable')


class FailingCache:
    """Cache que falha como um Redis fora do ar ou lento demais."""

    def __init__(self, error=RedisConnectionError):
        self.error = error
        self.calls = 0

    def fail(self, *args, **kwargs):
        self.calls += 1
        raise self.error('indisponível')

    get = set = add = incr = fail


def generation():
    return caches['public'].get(public_cache.GENERATION_KEY)


class CleanPublicCache:
    """Cache público limpo e sem pausa a cada teste."""

    def setUp(self):
        super().setUp()
        caches['public'].clear()
        public_cache.resume()
        self.addCleanup(public_cache.resume)


@override_settings(CACHES=LOCMEM)
class KeyTests(CleanPublicCache, SimpleTestCase):
    def test_key_format_and_fixed_length(self):
        short = public_cache.cache_key(public_cache.OPTIONS, 7, {'semester': '2026/2'})
        long = public_cache.cache_key(public_cache.CALENDAR_GRID, 7, {'space': 'x' * 5000})
        self.assertRegex(short, r'^public:options:g7:[0-9a-f]{32}$')
        self.assertEqual(len(long), len('public:calendar-grid:g7:') + 32)

    def test_same_params_same_key_in_any_order(self):
        first = public_cache.cache_key(public_cache.CALENDAR_GRID, 1, {'space': 3, 'teacher': None, 'start': date(2026, 9, 21)})
        second = public_cache.cache_key(public_cache.CALENDAR_GRID, 1, {'start': date(2026, 9, 21), 'teacher': None, 'space': 3})
        self.assertEqual(first, second)

    def test_different_params_resource_or_generation_change_the_key(self):
        base = public_cache.cache_key(public_cache.CALENDAR_GRID, 1, {'space': 3})
        for other in (
            public_cache.cache_key(public_cache.CALENDAR_GRID, 1, {'space': 4}),
            public_cache.cache_key(public_cache.CALENDAR_GRID, 1, {'teacher': 3}),
            public_cache.cache_key(public_cache.ORIGINAL_GRID, 1, {'space': 3}),
            public_cache.cache_key(public_cache.CALENDAR_GRID, 2, {'space': 3}),
        ):
            with self.subTest(other=other):
                self.assertNotEqual(base, other)

    def test_unknown_resource_is_refused(self):
        with self.assertRaises(ValueError):
            public_cache.cache_key('pagina', 1, {})

    def test_final_ttls(self):
        self.assertEqual(public_cache.TTL, {'options': 3600, 'calendar-grid': 600, 'original-grid': 1800})


@override_settings(CACHES=LOCMEM)
class LookupTests(CleanPublicCache, SimpleTestCase):
    def test_miss_then_hit(self):
        builder = mock.Mock(return_value=['valor'])
        first, second = public_cache.Lookup(), public_cache.Lookup()
        self.assertEqual(first.fetch(public_cache.OPTIONS, {'semester': '*'}, builder), ['valor'])
        self.assertEqual(second.fetch(public_cache.OPTIONS, {'semester': '*'}, builder), ['valor'])
        self.assertEqual((first.status, second.status, builder.call_count), ('miss', 'hit', 1))

    def test_generation_is_read_once_per_request(self):
        lookup = public_cache.Lookup()
        with mock.patch.object(public_cache, 'current_generation', wraps=public_cache.current_generation) as read:
            lookup.fetch(public_cache.OPTIONS, {'semester': '*'}, list)
            lookup.fetch(public_cache.OPTIONS, {'semester': '2026/2'}, list)
        self.assertEqual(read.call_count, 1)

    def test_bump_makes_the_previous_entry_unreachable(self):
        builder = mock.Mock(side_effect=['antes', 'depois'])
        public_cache.Lookup().fetch(public_cache.OPTIONS, {}, builder)
        public_cache.bump_generation()
        lookup = public_cache.Lookup()
        self.assertEqual(lookup.fetch(public_cache.OPTIONS, {}, builder), 'depois')
        self.assertEqual(lookup.status, 'miss')

    def test_missing_generation_is_recreated_without_reusing_a_previous_one(self):
        first = public_cache.current_generation()
        public_cache.bump_generation()
        used = public_cache.current_generation()
        caches['public'].delete(public_cache.GENERATION_KEY)
        recreated = public_cache.current_generation()
        self.assertNotIn(recreated, (first, used))
        self.assertGreater(recreated, used)

    def test_bump_without_generation_creates_a_new_one(self):
        public_cache.bump_generation()
        self.assertIsNotNone(generation())

    def test_unreadable_value_is_a_miss(self):
        lookup = public_cache.Lookup()
        lookup.generation()
        with mock.patch.object(caches['public'], 'get', side_effect=ValueError):
            self.assertEqual(lookup.fetch(public_cache.OPTIONS, {}, lambda: 'banco'), 'banco')
        self.assertEqual(lookup.status, 'miss')

    @override_settings(CACHES={**LOCMEM, 'public': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}})
    def test_without_redis_configured_it_bypasses(self):
        lookup = public_cache.Lookup()
        self.assertEqual(lookup.fetch(public_cache.OPTIONS, {}, lambda: 'banco'), 'banco')
        self.assertEqual(lookup.status, 'bypass')
        public_cache.bump_generation()


@override_settings(CACHES=LOCMEM)
class UnavailableTests(CleanPublicCache, SimpleTestCase):
    def test_connection_error_and_timeout_fall_back_to_the_database(self):
        for error in (RedisConnectionError, RedisTimeoutError, OSError):
            with self.subTest(error=error.__name__), mock.patch.object(public_cache, 'backend', return_value=FailingCache(error)):
                public_cache.resume()
                lookup = public_cache.Lookup()
                with self.assertLogs('schedule.public_cache', 'WARNING') as logs:
                    self.assertEqual(lookup.fetch(public_cache.OPTIONS, {}, lambda: 'banco'), 'banco')
                self.assertEqual(lookup.status, 'bypass')
                self.assertIn('REDIS UNAVAILABLE read', logs.output[0])

    def test_pause_skips_redis_for_thirty_seconds(self):
        failing = FailingCache()
        clock = mock.patch('schedule.public_cache.time.monotonic', return_value=1000.0)
        with mock.patch.object(public_cache, 'backend', return_value=failing), clock as monotonic, self.assertLogs('schedule.public_cache', 'WARNING'):
            public_cache.Lookup().fetch(public_cache.OPTIONS, {}, list)
            calls = failing.calls
            for _ in range(5):
                lookup = public_cache.Lookup()
                lookup.fetch(public_cache.OPTIONS, {}, list)
                self.assertEqual(lookup.status, 'bypass')
            self.assertEqual(failing.calls, calls)
            monotonic.return_value = 1000.0 + public_cache.PAUSE_SECONDS
            public_cache.Lookup().fetch(public_cache.OPTIONS, {}, list)
            self.assertGreater(failing.calls, calls)

    def test_write_failure_still_returns_the_value(self):
        cache = caches['public']
        with mock.patch.object(cache, 'set', side_effect=RedisConnectionError('fora')), self.assertLogs('schedule.public_cache', 'WARNING') as logs:
            lookup = public_cache.Lookup()
            self.assertEqual(lookup.fetch(public_cache.OPTIONS, {}, lambda: 'banco'), 'banco')
        self.assertEqual(lookup.status, 'miss')
        self.assertIn('REDIS UNAVAILABLE write', logs.output[0])

    def test_invalidation_failure_is_logged_and_does_not_raise(self):
        with mock.patch.object(public_cache, 'backend', return_value=FailingCache()), self.assertLogs('schedule.public_cache', 'WARNING') as logs:
            public_cache.bump_generation()
        self.assertIn('REDIS UNAVAILABLE invalidate', logs.output[0])
        self.assertFalse(public_cache.is_enabled())


@override_settings(CACHES=LOCMEM)
class InvalidationTestCase(CleanPublicCache, TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        super().setUp()
        self.start = public_cache.current_generation()

    def bumps(self):
        return generation() - self.start


class CommitTests(InvalidationTestCase):
    def test_commit_bumps_and_rollback_does_not(self):
        with transaction.atomic():
            Space.objects.register('Sala 40')
            self.assertEqual(self.bumps(), 0)
        self.assertEqual(self.bumps(), 1)
        with self.assertRaises(RuntimeError), transaction.atomic():
            Space.objects.register('Sala 41')
            raise RuntimeError
        self.assertEqual(self.bumps(), 1)
        self.assertFalse(Space.objects.filter(name='Sala 41').exists())

    def test_many_writes_in_one_transaction_bump_once(self):
        with self.assertLogs('schedule.public_cache', 'INFO') as logs, transaction.atomic():
            for number in range(5):
                Teacher.objects.resolve(f'Docente {number}')
        self.assertEqual(self.bumps(), 1)
        self.assertEqual(len([line for line in logs.output if 'CACHE INVALIDATED' in line]), 1)

    def test_rolled_back_savepoint_does_not_lose_a_later_write(self):
        with transaction.atomic():
            try:
                with transaction.atomic():
                    Teacher.objects.resolve('Desfeito')
                    raise RuntimeError
            except RuntimeError:
                pass
            Teacher.objects.resolve('Mantido')
        self.assertEqual(self.bumps(), 1)

    def test_space_changes_bump(self):
        lab = Space.objects.register('Lab 1')
        for operation in (
            lambda: lab.update_details('Lab Um', []),
            lab.deactivate,
            lambda: lab.reactivate(),
            lab.delete_space,
        ):
            before = self.bumps()
            operation()
            self.assertEqual(self.bumps(), before + 1)

    def test_course_changes_bump(self):
        course = Course.objects.register('Eng. Alimentos', Stage.UNDERGRADUATE)
        for operation in (
            lambda: course.update_details('Engenharia de Alimentos', Stage.UNDERGRADUATE),
            lambda: course.update_details('Engenharia de Alimentos', Stage.SECONDARY),
            course.delete_course,
        ):
            before = self.bumps()
            operation()
            self.assertEqual(self.bumps(), before + 1)

    def test_login_and_password_change_do_not_bump(self):
        user = User.objects.create_superadmin('super@ifnmg.edu.br', 'Super', 'senha-forte-123')
        before = self.bumps()
        self.assertTrue(self.client.login(username='super@ifnmg.edu.br', password='senha-forte-123'))
        user.refresh_from_db()
        self.assertIsNotNone(user.last_login)
        user.set_password('outra-senha-forte-456')
        user.save(update_fields=['password'])
        self.assertEqual(self.bumps(), before)
        user.email = 'novo@ifnmg.edu.br'
        user.save(update_fields=['email'])
        self.assertEqual(self.bumps(), before)

    def test_relevant_user_change_bumps(self):
        user = User.objects.create_superadmin('super@ifnmg.edu.br', 'Super', 'senha-forte-123')
        for field, value in (('name', 'Outro'), ('username', 'outro'), ('is_active', False)):
            with self.subTest(field=field):
                before = self.bumps()
                setattr(user, field, value)
                user.save(update_fields=[field])
                self.assertEqual(self.bumps(), before + 1)
        before = self.bumps()
        user.save()
        self.assertEqual(self.bumps(), before + 1)

    def test_teacher_change_of_an_allocation_bumps(self):
        semester = semester_with_lesson()
        allocation = Allocation.objects.get(semester=semester)
        other = Teacher.objects.resolve('Outra Docente')[0]
        before = self.bumps()
        self.assertEqual(allocation.update_details(allocation.space, [other])[0], 'update')
        self.assertEqual(self.bumps(), before + 1)

    def test_bulk_writes_invalidate_explicitly(self):
        semester = semester_with_lesson()
        allocation = Allocation.objects.get(semester=semester)
        before = self.bumps()
        with mock.patch('django.db.models.signals.post_save.send'), mock.patch('django.db.models.signals.m2m_changed.send'):
            ClassOffering.objects.record_many(semester, [(allocation.subject_id, allocation.class_group_id)])
        self.assertEqual(self.bumps(), before + 1)
        offering = ClassOffering.objects.get()
        with mock.patch('django.db.models.signals.post_save.send'):
            offering.sync_assignments()
        self.assertEqual(self.bumps(), before + 2)

    @override_settings(ENVIRONMENT='local')
    def test_clear_data_invalidates(self):
        Space.objects.register('Sala 50')
        before = self.bumps()
        call_command('clear_data', '--yes', stdout=mock.Mock())
        self.assertEqual(self.bumps(), before + 1)

    def test_invalidation_failure_keeps_the_committed_write(self):
        with mock.patch.object(caches['public'], 'incr', side_effect=RedisConnectionError('fora')), \
                self.assertLogs('schedule.public_cache', 'WARNING') as logs:
            Space.objects.register('Sala 60')
        self.assertTrue(Space.objects.filter(name='Sala 60').exists())
        self.assertIn('REDIS UNAVAILABLE invalidate', logs.output[0])


class BookingInvalidationTests(InvalidationTestCase):
    def setUp(self):
        super().setUp()
        frozen_clock(self)
        semester_with_lesson()
        self.reviewer = user_with('revisor@ifnmg.edu.br', *REVIEWER)
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.lab = space('Laboratório 1')

    def test_request_approval_and_cancellation_bump_after_commit(self):
        before = self.bumps()
        request = submit(self.ana, self.lab)
        self.assertGreater(self.bumps(), before)
        before = self.bumps()
        request.approve(self.reviewer)
        self.assertEqual(self.bumps(), before + 1)
        before = self.bumps()
        request.cancel(self.ana)
        self.assertEqual(self.bumps(), before + 1)
        self.assertFalse(Booking.objects.exists())

    def test_booking_change_and_deletion_bump(self):
        request = submit(self.ana, self.lab)
        request.approve(self.reviewer)
        booking = Booking.objects.get()
        before = self.bumps()
        booking.description = 'Outra descrição'
        booking.save()
        self.assertEqual(self.bumps(), before + 1)
        booking.delete()
        self.assertEqual(self.bumps(), before + 2)

    def test_refused_approval_does_not_bump(self):
        request = submit(self.ana, self.lab)
        second = submit(user_with('bruno@ifnmg.edu.br', *REQUESTER), self.lab)
        request.approve(self.reviewer)
        before = self.bumps()
        with self.assertRaises(SlotUnavailable):
            second.approve(self.reviewer)
        self.assertEqual(self.bumps(), before)


class ImportInvalidationTests(InvalidationTestCase):
    """A prévia é desfeita e não invalida; a confirmação pelo worker invalida o mesmo alias que a tela lê."""

    def setUp(self):
        super().setUp()
        self.executor = space_manager()
        self.definition = SpaceAllocationImport()

    def test_preview_does_not_bump_and_worker_confirmation_bumps_once(self):
        form = ImportUploadForm(
            data={'own_semestre': '2026/1', **PERIOD}, files={'file': workbook_file()}, definition=self.definition,
        )
        self.assertTrue(form.is_valid(), form.errors)
        before = self.bumps()
        importation = preview(self.definition, form.cleaned_data['rows'], form.cleaned_data['file'].name, self.executor)
        self.assertEqual(self.bumps(), before)
        self.assertTrue(confirm(importation, self.definition, self.executor))
        self.assertEqual(self.bumps(), before + 1)
        self.assertTrue(Allocation.objects.exists())


@override_settings(CACHES=LOCMEM)
class PublicViewCacheTests(CleanPublicCache, PublicCalendarTestCase):
    def open(self, url=CALENDAR, **params):
        return self.client.get(url, params)

    def test_headers_miss_then_hit_and_no_cache(self):
        for url, params in ((CALENDAR, {'sala': '10'}), (ORIGINAL, {'sala': '10'})):
            with self.subTest(url=url):
                first, second = self.open(url, **params), self.open(url, **params)
                self.assertEqual((first['X-Public-Cache'], second['X-Public-Cache']), ('miss', 'hit'))
                self.assertIn('no-cache', second['Cache-Control'])
                self.assertEqual(first.content, second.content)
                self.assertNotIn('Set-Cookie', second.headers)

    def test_same_content_with_and_without_cache(self):
        cases = [
            (CALENDAR, {}), (CALENDAR, {'sala': '10'}), (CALENDAR, {'sala': 'SALA DEZ'}),
            (CALENDAR, {'docente': 'aldo gomes', 'inicio': '2026-09-01', 'fim': '2026-09-30'}),
            (CALENDAR, {'curso': 'INFORMÁTICA', 'turma': '2º ANO A'}), (CALENDAR, {'nivel': 'graduacao', 'docente': 'Adailton'}),
            (CALENDAR, {'sala': '10', 'inicio': '2026-09-30', 'fim': '2026-09-01'}),
            (ORIGINAL, {'sala': '10'}), (ORIGINAL, {'curso': 'LICENCIATURA EM FÍSICA'}),
        ]
        for url, params in cases:
            with self.subTest(url=url, params=params):
                with override_settings(CACHES={**LOCMEM, 'public': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}):
                    plain = self.open(url, **params)
                    self.assertEqual(plain['X-Public-Cache'], 'bypass')
                cold, warm = self.open(url, **params), self.open(url, **params)
                self.assertEqual(plain.content, cold.content)
                self.assertEqual(plain.content, warm.content)

    def test_spellings_share_the_entry(self):
        self.open(sala='Sala Dez')
        self.assertEqual(self.open(sala='SALA DEZ')['X-Public-Cache'], 'hit')
        self.open(docente='Aldo Gomes')
        self.assertEqual(self.open(docente='ALDO GOMES')['X-Public-Cache'], 'hit')

    def test_unknown_parameter_creates_no_grid_entry(self):
        keys_before = set(caches['public']._cache)
        response = self.open(sala='x' * 5000)
        self.assertContains(response, 'Escolha uma sala, um docente ou um curso.')
        options = len(set(caches['public']._cache) - keys_before)
        self.open(sala='y' * 5000)
        self.assertEqual(len(set(caches['public']._cache) - keys_before), options)

    def test_warm_page_without_principal_filter_makes_no_query(self):
        self.open()
        with CaptureQueriesContext(connection) as queries:
            response = self.open()
        self.assertEqual(response['X-Public-Cache'], 'hit')
        self.assertEqual(len(queries), 0)

    def test_warm_grid_makes_no_query(self):
        self.open(sala='10')
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.open(sala='10')['X-Public-Cache'], 'hit')
        self.assertEqual(len(queries), 0)

    def test_day_change_rebuilds_the_grid(self):
        self.open(sala='10')
        with mock.patch('schedule.public_views.timezone.localdate', return_value=date(2026, 9, 24)):
            self.assertEqual(self.open(sala='10')['X-Public-Cache'], 'miss')

    def test_after_invalidation_the_next_request_reads_the_database(self):
        self.assertContains(self.open(sala='10'), 'Banco de Dados')
        Allocation.objects.filter(subject__name='Banco de Dados').update(space=Space.objects.named('12'))
        self.assertEqual(self.open(sala='10')['X-Public-Cache'], 'hit')
        public_cache.bump_generation()
        response = self.open(sala='10')
        self.assertEqual(response['X-Public-Cache'], 'miss')
        self.assertNotContains(response, 'Banco de Dados')

    def test_redis_down_serves_the_database_content(self):
        expected = self.open(sala='10').content
        public_cache.bump_generation()
        with mock.patch.object(public_cache, 'backend', return_value=FailingCache(RedisTimeoutError)), self.assertLogs('schedule.public_cache', 'WARNING'):
            response = self.open(sala='10')
        self.assertEqual(response['X-Public-Cache'], 'bypass')
        self.assertEqual(response.content, expected)

    def test_authenticated_visitor_gets_the_shared_content(self):
        anonymous = self.open(sala='10').content
        self.client.force_login(self.aldo)
        response = self.open(sala='10')
        self.assertEqual(response['X-Public-Cache'], 'hit')
        self.assertEqual(response.content, anonymous)
        self.assertNotIn(self.aldo.name.encode(), response.content.split(b'<main')[0])

    def test_login_and_password_pages_do_not_use_the_cache(self):
        keys = set(caches['public']._cache)
        for name in ('account_login', 'account_reset_password'):
            response = self.client.get(reverse(name))
            self.assertNotIn('X-Public-Cache', response.headers)
        self.assertEqual(set(caches['public']._cache), keys)


class BulkWriteScanTests(SimpleTestCase):
    """Escritas em massa não disparam sinais; uma escrita nova fora da lista falha até ser revisada."""

    APPS = ('accounts', 'audit', 'bookings', 'imports', 'notices', 'outbox', 'panel', 'reports', 'schedule', 'system_settings', 'ui')
    MODELS = (
        'Semester', 'Allocation', 'AllocationException', 'TimeSlot', 'Space', 'Teacher', 'Course', 'Subject',
        'ClassGroup', 'ClassOffering', 'TeachingAssignment', 'Booking', 'BookingRequest', 'User',
    )
    MODEL_FILES = ('schedule/models.py', 'bookings/models.py', 'accounts/models.py')
    WRITE = re.compile(r'bulk_create\(|bulk_update\(|\.update\(|cursor\(|teachers\.(set|add|remove|clear)\(')
    REVIEWED = {
        ('accounts/management/commands/set_passwords.py', "User.objects.bulk_update(users, ['password'])"),
        ('accounts/management/commands/clear_data.py', 'with transaction.atomic(), connection.cursor() as cursor:'),
        ('accounts/utils.py', 'with connection.cursor() as cursor:'),
        ('imports/worker.py', 'with connection.cursor() as cursor:'),
        ('schedule/models.py', 'SpaceName.objects.bulk_create(SpaceName(space=space, name=name) for name in names)'),
        ('schedule/models.py', 'AllocationException.objects.filter(pk__in=moved_ids).update(allocation=version)'),
        ('schedule/models.py', 'self.bulk_create('),
        ('schedule/models.py', 'TeachingAssignment.objects.bulk_create('),
        ('schedule/models.py', 'TeachingAssignment.objects.filter(pk__in=current).update(is_current=True)'),
        ('schedule/models.py', 'TeachingAssignment.objects.filter(pk__in=former).update(is_current=False)'),
        ('schedule/models.py', 'allocation.teachers.add(*teachers)'),
        ('schedule/models.py', 'version.teachers.set(self.teachers)'),
        ('schedule/models.py', 'self.teachers.set(teachers)'),
    }

    def found(self):
        base = Path(settings.BASE_DIR)
        result = set()
        for app in self.APPS:
            for path in (base / app).rglob('*.py'):
                relative = path.relative_to(base).as_posix()
                if '/tests/' in relative or '/migrations/' in relative:
                    continue
                for line in path.read_text().splitlines():
                    text = line.strip()
                    if not self.WRITE.search(text):
                        continue
                    if 'cursor(' in text or 'teachers.' in text or any(re.search(rf'\b{model}\b', text) for model in self.MODELS) or (
                        relative in self.MODEL_FILES and text.startswith('self.bulk_')
                    ):
                        result.add((relative, text))
        return result

    def test_every_bulk_write_was_reviewed(self):
        self.assertEqual(self.found() - self.REVIEWED, set())

    def test_explicit_invalidations_are_in_place(self):
        models = (Path(settings.BASE_DIR) / 'schedule/models.py').read_text()
        clear_data = (Path(settings.BASE_DIR) / 'accounts/management/commands/clear_data.py').read_text()
        self.assertEqual(models.count('public_cache.invalidate_on_commit()'), 3)
        self.assertIn('public_cache.invalidate_on_commit()', clear_data)


class JsonSerializerTests(SimpleTestCase):
    """O Redis guarda JSON, e não pickle: um valor gravado por terceiros nunca vira objeto Python arbitrário."""

    def test_round_trip_of_cached_shapes(self):
        serializer = JsonSerializer()
        value = [(1, '2026/1', date(2026, 2, 2), date(2026, 7, 1))]
        self.assertEqual(serializer.loads(serializer.dumps(value)), [[1, '2026/1', date(2026, 2, 2), date(2026, 7, 1)]])
        self.assertEqual(serializer.loads(serializer.dumps('<p>grade</p>')), '<p>grade</p>')
        self.assertEqual(serializer.dumps(7), 7)

    def test_pickled_payload_is_not_unpickled(self):
        import pickle

        with self.assertRaises(ValueError):
            JsonSerializer().loads(pickle.dumps(object()))

    def test_unknown_type_is_refused_when_writing(self):
        with self.assertRaises(TypeError):
            JsonSerializer().dumps({'x': object()})


class TolerantCacheTests(SimpleTestCase):
    """Com o Redis fora, os limites de tentativa deixam de valer e o login não falha."""

    def test_operations_do_not_raise_when_redis_is_unavailable(self):
        cache = TolerantRedisCache('redis://127.0.0.1:1/0', {'OPTIONS': {'socket_connect_timeout': 0.01}})
        with self.assertLogs('config', 'WARNING'):
            self.assertEqual(cache.get('chave', []), [])
            cache.set('chave', [1.0], 10)
            self.assertTrue(cache.add('trava', True, 10))
            self.assertFalse(cache.delete('chave'))
