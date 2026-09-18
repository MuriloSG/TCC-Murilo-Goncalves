from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase

from accounts.models import Role, User

PASSWORD = 'Senha-forte-123'


def create_superadmin(*args, passwords=(PASSWORD, PASSWORD), inputs=()):
    with (
        mock.patch('accounts.management.commands.create_superadmin.getpass', side_effect=passwords),
        mock.patch('builtins.input', side_effect=inputs),
    ):
        call_command('create_superadmin', *args, stdout=StringIO())


class CreateSuperadminTests(TestCase):
    def test_creates_active_superadmin_with_administrator_role(self):
        create_superadmin(inputs=[' Super@IFNMG.edu.br ', 'Super Admin'])
        user = User.objects.get()
        self.assertEqual((user.email, user.name), ('super@ifnmg.edu.br', 'Super Admin'))
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_superadmin)
        self.assertEqual(user.role.code, 'ADMINISTRADOR')
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)

    def test_accepts_email_and_name_as_options(self):
        create_superadmin('--email', 'super@ifnmg.edu.br', '--name', 'Super Admin')
        self.assertTrue(User.objects.get(email='super@ifnmg.edu.br').is_superadmin)

    def test_refuses_email_in_use_pointing_to_set_superadmin(self):
        User.objects.register(email='maria@ifnmg.edu.br', name='Maria', role=Role.objects.get(code='DOCENTE'))
        with self.assertRaisesMessage(CommandError, 'set_superadmin'):
            create_superadmin('--email', 'Maria@ifnmg.edu.br', '--name', 'Maria')
        self.assertFalse(User.objects.get().is_superadmin)

    def test_refuses_passwords_that_do_not_match(self):
        with self.assertRaisesMessage(CommandError, 'não conferem'):
            create_superadmin('--email', 'super@ifnmg.edu.br', '--name', 'Super', passwords=(PASSWORD, 'Outra-senha-456'))
        self.assertFalse(User.objects.exists())

    def test_refuses_weak_passwords(self):
        cases = {
            'numeric': '93847261530',
            'common': 'password123',
            'short': 'Ab1-x',
            'similar to email': 'superadmin.ifnmg',
            'similar to name': 'Joaquim Barbosa',
        }
        for case, password in cases.items():
            with self.subTest(case):
                with self.assertRaises(CommandError):
                    create_superadmin(
                        '--email', 'superadmin@ifnmg.edu.br', '--name', 'Joaquim Barbosa',
                        passwords=(password, password),
                    )
                self.assertFalse(User.objects.exists())

    def test_refuses_invalid_email(self):
        with self.assertRaises(CommandError):
            create_superadmin('--email', 'super.ifnmg.edu.br', '--name', 'Super')
        self.assertFalse(User.objects.exists())


class SetSuperadminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')

    def call(self, *args):
        call_command('set_superadmin', *args, stdout=StringIO())

    def test_grants_superadmin(self):
        user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria', role=self.teacher)
        self.call('Maria@IFNMG.edu.br', '--grant')
        user.refresh_from_db()
        self.assertTrue(user.is_superadmin)
        self.assertEqual(user.role, self.teacher)

    def test_revokes_superadmin_when_someone_keeps_the_capability(self):
        User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=self.administrator)
        user = User.objects.register(email='super@ifnmg.edu.br', name='Super', role=self.teacher)
        user.set_superadmin(True)
        self.call('super@ifnmg.edu.br', '--revoke')
        user.refresh_from_db()
        self.assertFalse(user.is_superadmin)

    def test_revoke_refused_by_administrative_continuity(self):
        user = User.objects.register(email='super@ifnmg.edu.br', name='Super', role=self.teacher)
        user.set_superadmin(True)
        with self.assertRaisesMessage(CommandError, 'capacidade administrativa'):
            self.call('super@ifnmg.edu.br', '--revoke')
        user.refresh_from_db()
        self.assertTrue(user.is_superadmin)

    def test_unknown_email(self):
        with self.assertRaisesMessage(CommandError, 'Não existe usuário'):
            self.call('ninguem@ifnmg.edu.br', '--grant')

    def test_requires_exactly_one_action(self):
        User.objects.register(email='maria@ifnmg.edu.br', name='Maria', role=self.teacher)
        for args in [(), ('--grant', '--revoke')]:
            with self.subTest(args):
                with self.assertRaises(CommandError):
                    self.call('maria@ifnmg.edu.br', *args)
