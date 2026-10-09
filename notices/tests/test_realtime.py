import asyncio
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.security.websocket import OriginValidator
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.conf import settings
from django.test import Client, TestCase, TransactionTestCase, override_settings

from accounts.models import Role, User
from config import asgi
from notices import catalog
from notices.consumers import CHANGED, NotificationsConsumer, group_name
from notices.models import Notification

TEST_CHANNEL = 'canal-de-teste'


def receive(channel, timeout=0.5):
    """Próxima mensagem do canal, ou None quando nada chegou no tempo esperado."""
    layer = get_channel_layer()

    async def read():
        try:
            return await asyncio.wait_for(layer.receive(channel), timeout)
        except TimeoutError:
            return None

    return async_to_sync(read)()


class ChannelTests(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        self.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', Role.objects.get(code='DOCENTE'))

    def connect_as(self, user):
        communicator = WebsocketCommunicator(NotificationsConsumer.as_asgi(), '/ws/notificacoes/')
        communicator.scope['user'] = user
        return communicator

    async def test_authenticated_user_receives_the_event(self):
        communicator = self.connect_as(self.ana)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await get_channel_layer().group_send(group_name(self.ana.pk), {'type': CHANGED})
        self.assertEqual(await communicator.receive_json_from(), {'evento': 'notificacoes'})
        await communicator.disconnect()

    async def test_event_of_another_user_does_not_arrive(self):
        communicator = self.connect_as(self.ana)
        await communicator.connect()
        await get_channel_layer().group_send(group_name(self.ana.pk + 1), {'type': CHANGED})
        self.assertTrue(await communicator.receive_nothing(timeout=0.3))
        await communicator.disconnect()

    async def test_visitor_is_refused(self):
        communicator = self.connect_as(AnonymousUser())
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_deactivation_closes_the_open_connection(self):
        await database_sync_to_async(User.objects.create_superadmin)('super@ifnmg.edu.br', 'Super', 'Senha-forte-123')
        communicator = self.connect_as(self.ana)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await database_sync_to_async(self.ana.deactivate)()
        self.assertEqual((await communicator.receive_output(timeout=2))['type'], 'websocket.close')

    async def test_inactive_user_is_refused(self):
        self.ana.is_active = False
        communicator = self.connect_as(self.ana)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)


@override_settings(ALLOWED_HOSTS=['ifagenda.example'], DEBUG=False)
class OriginTests(TransactionTestCase):
    """Handshake pela pilha real do `config.asgi`, com a sessão em cookie e o `Origin` variando."""

    serialized_rollback = True

    def setUp(self):
        self.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', Role.objects.get(code='DOCENTE'))

    def session_cookie(self, user):
        client = Client()
        client.force_login(user)
        return f'{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}'.encode()

    def communicator(self, origin=None, user=None):
        headers = []
        if origin is not None:
            headers.append((b'origin', origin.encode()))
        if user is not None:
            headers.append((b'cookie', self.session_cookie(user)))
        return WebsocketCommunicator(asgi.websocket_application(), '/ws/notificacoes/', headers=headers)

    def test_project_application_validates_the_origin(self):
        self.assertIsInstance(asgi.application.application_mapping['websocket'], OriginValidator)

    async def test_allowed_origin_with_session_connects_and_receives_the_event(self):
        communicator = await self.prepared('https://ifagenda.example', self.ana)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await get_channel_layer().group_send(group_name(self.ana.pk), {'type': CHANGED})
        self.assertEqual(await communicator.receive_json_from(), {'evento': 'notificacoes'})
        await communicator.disconnect()

    async def test_foreign_origin_is_refused_even_with_session(self):
        for origin in ('https://outro-site.example', 'https://ifagenda.example.outro.com', 'null'):
            with self.subTest(origin=origin):
                communicator = await self.prepared(origin, self.ana)
                connected, _ = await communicator.connect()
                self.assertFalse(connected)

    async def test_missing_origin_is_refused_even_with_session(self):
        communicator = await self.prepared(None, self.ana)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_allowed_origin_without_session_is_refused(self):
        communicator = await self.prepared('https://ifagenda.example', None)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def prepared(self, origin, user):
        return await database_sync_to_async(self.communicator)(origin, user)


@override_settings(ALLOWED_HOSTS=[], DEBUG=False)
class EmptyAllowedHostsTests(TransactionTestCase):
    serialized_rollback = True

    async def test_empty_list_outside_debug_refuses_every_origin(self):
        communicator = WebsocketCommunicator(
            asgi.websocket_application(), '/ws/notificacoes/', headers=[(b'origin', b'http://localhost:8000')],
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)


class AnnounceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        docente = Role.objects.get(code='DOCENTE')
        cls.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', docente)
        cls.bruno = User.objects.register('bruno@ifnmg.edu.br', 'Bruno', docente)

    def setUp(self):
        async_to_sync(get_channel_layer().group_add)(group_name(self.ana.pk), TEST_CHANNEL)

    def notify(self, recipient=None):
        return Notification.objects.notify(
            recipient or self.ana, catalog.INFORMATION, 'Nova versão do sistema', 'Mensagem.',
        )

    def test_event_is_sent_only_after_the_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.notify()
            self.assertIsNone(receive(TEST_CHANNEL, timeout=0.2))
        self.assertEqual(receive(TEST_CHANNEL), {'type': CHANGED})

    def test_undone_transaction_announces_nothing(self):
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    self.notify()
                    raise RuntimeError('operação desfeita')
        self.assertIsNone(receive(TEST_CHANNEL, timeout=0.2))

    def test_publication_announces_each_recipient(self):
        with self.captureOnCommitCallbacks(execute=True):
            Notification.objects.publish(
                catalog.INFORMATION, 'Nova versão do sistema', 'Mensagem.', [self.ana, self.bruno],
            )
        self.assertEqual(receive(TEST_CHANNEL), {'type': CHANGED})

    def test_notification_of_another_user_does_not_announce_this_one(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.notify(recipient=self.bruno)
        self.assertIsNone(receive(TEST_CHANNEL, timeout=0.2))

    def test_channel_failure_does_not_undo_the_notification(self):
        with patch('notices.realtime.get_channel_layer', side_effect=RuntimeError('canal fora do ar')):
            with self.assertLogs('notices.realtime', level='ERROR'):
                with self.captureOnCommitCallbacks(execute=True):
                    self.notify()
        self.assertEqual(Notification.objects.for_user(self.ana).count(), 1)
        self.assertEqual(Notification.objects.unread_count(self.ana), 1)
