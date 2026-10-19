from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from accounts import permissions
from accounts.models import Role, User
from accounts.tests.roles import management_role, requester_role

PASSWORD = 'Senha-forte-123'


def create_superadmin(*args, passwords=(PASSWORD, PASSWORD), inputs=()):
    with (
        mock.patch('accounts.management.commands.create_superadmin.getpass', side_effect=passwords),
        mock.patch('builtins.input', side_effect=inputs),
    ):
        call_command('create_superadmin', *args, stdout=StringIO())


class CreateSuperadminTests(TestCase):
    def test_creates_active_superadmin_without_role(self):
        create_superadmin(inputs=[' Super@IFNMG.edu.br ', 'Super Admin'])
        user = User.objects.get()
        self.assertEqual((user.email, user.name), ('super@ifnmg.edu.br', 'Super Admin'))
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_superadmin)
        self.assertIsNone(user.role)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)

    def test_creates_superadmin_without_any_role_registered(self):
        Role.objects.all().delete()
        create_superadmin('--email', 'super@ifnmg.edu.br', '--name', 'Super Admin')
        user = User.objects.get()
        self.assertTrue(user.has_perms(permissions.ALL_PERMISSIONS))
        self.assertTrue(user.has_administrative_capability())

    def test_refuses_email_in_use_pointing_to_set_superadmin(self):
        User.objects.register(email='maria@ifnmg.edu.br', name='Maria', role=requester_role())
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
        cls.administrator = management_role()
        cls.teacher = requester_role()

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


@override_settings(ENVIRONMENT='local')
class DeleteUsersTests(TestCase):
    def setUp(self):
        self.role = requester_role()
        self.superadmin = User.objects.create_superadmin('root@ifnmg.edu.br', 'Root', PASSWORD)
        self.user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=self.role)

    def delete_users(self, *args):
        output = StringIO()
        call_command('delete_users', *args, stdout=output)
        return output.getvalue()

    def test_deletes_users_and_their_links_keeping_roles_and_superadmins(self):
        from allauth.account.models import EmailAddress
        from audit import catalog
        from audit.context import acting_as_user
        from audit.models import AuditLog
        from imports.models import Import

        EmailAddress.objects.create(user=self.user, email=self.user.email)
        importation = Import.objects.create(
            kind='USUARIO', status=Import.Status.CONCLUDED, file_name='a.csv',
            created_by=self.user, resolved_by=self.superadmin,
        )
        kept = Import.objects.create(
            kind='USUARIO', status=Import.Status.CONCLUDED, file_name='b.csv',
            created_by=self.superadmin, resolved_by=self.user,
        )
        with acting_as_user(self.user):
            AuditLog.objects.record(catalog.UPDATE, catalog.USER, resource_id=self.user.pk)
        roles = Role.objects.count()

        self.assertIn('1 usuários excluídos', self.delete_users('--yes'))

        self.assertEqual(list(User.objects.all()), [self.superadmin])
        self.assertEqual(Role.objects.count(), roles)
        self.assertFalse(EmailAddress.objects.filter(email='ana@ifnmg.edu.br').exists())
        self.assertFalse(Import.objects.filter(pk=importation.pk).exists())
        kept.refresh_from_db()
        self.assertIsNone(kept.resolved_by)
        self.assertFalse(AuditLog.objects.filter(user_id=self.user.pk).exists())
        self.assertTrue(AuditLog.objects.filter(resource_id=str(self.user.pk), user=None).exists())
        self.assertFalse(self.superadmin.roles.exists())

    def test_refused_without_active_superadmin(self):
        User.objects.filter(pk=self.superadmin.pk).update(is_superadmin=False)
        with self.assertRaises(CommandError):
            self.delete_users('--yes')
        self.assertEqual(User.objects.count(), 2)

    def test_answer_other_than_yes_keeps_everything(self):
        with mock.patch('builtins.input', return_value='não'):
            self.assertIn('Nada foi excluído', self.delete_users())
        self.assertEqual(User.objects.count(), 2)


@override_settings(ENVIRONMENT='local')
class SetPasswordsTests(TestCase):
    def test_sets_the_default_password_for_every_user(self):
        superadmin = User.objects.create_superadmin('root@ifnmg.edu.br', 'Root', PASSWORD)
        user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=requester_role())
        output = StringIO()
        call_command('set_passwords', '--yes', stdout=output)
        for account in (superadmin, user):
            account.refresh_from_db()
            self.assertTrue(account.check_password('senha123#'))
            self.assertNotIn('senha123#', account.password)
        self.assertIn('2 usuários', output.getvalue())

    def test_answer_other_than_yes_keeps_passwords(self):
        user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=requester_role())
        with mock.patch('builtins.input', return_value='não'):
            call_command('set_passwords', stdout=StringIO())
        user.refresh_from_db()
        self.assertFalse(user.has_usable_password())
