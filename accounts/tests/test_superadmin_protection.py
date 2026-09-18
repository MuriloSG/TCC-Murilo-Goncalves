from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Role, SuperadminOnlyOperation, User


class SuperadminEmailProtectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        teacher = Role.objects.get(code='DOCENTE')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=administrator)
        cls.superadmin = User.objects.register(email='super@ifnmg.edu.br', name='Super', role=teacher)
        cls.superadmin.set_superadmin(True)
        cls.other_superadmin = User.objects.register(email='outro@ifnmg.edu.br', name='Outro', role=teacher)
        cls.other_superadmin.set_superadmin(True)

    def reload(self, user):
        return User.objects.get(pk=user.pk)

    def test_regular_admin_cannot_change_superadmin_email(self):
        target = self.reload(self.superadmin)
        with self.assertRaises(SuperadminOnlyOperation) as raised:
            target.update_details(self.reload(self.admin), name='Super', email='novo@ifnmg.edu.br')
        self.assertIsInstance(raised.exception, ValidationError)
        self.assertTrue(raised.exception.messages)
        self.assertEqual(target.email, 'super@ifnmg.edu.br')
        self.assertEqual(self.reload(self.superadmin).email, 'super@ifnmg.edu.br')

    def test_regular_admin_cannot_change_inactive_superadmin_email(self):
        User.objects.filter(pk=self.superadmin.pk).update(is_active=False)
        target = self.reload(self.superadmin)
        with self.assertRaises(SuperadminOnlyOperation):
            target.update_details(self.reload(self.admin), name='Super', email='novo@ifnmg.edu.br')
        self.assertEqual(self.reload(self.superadmin).email, 'super@ifnmg.edu.br')

    def test_regular_admin_cannot_change_name_and_email_together(self):
        target = self.reload(self.superadmin)
        with self.assertRaises(SuperadminOnlyOperation):
            target.update_details(self.reload(self.admin), name='Novo nome', email='novo@ifnmg.edu.br')
        reloaded = self.reload(self.superadmin)
        self.assertEqual((reloaded.name, reloaded.email), ('Super', 'super@ifnmg.edu.br'))

    def test_regular_admin_can_change_superadmin_name(self):
        target = self.reload(self.superadmin)
        target.update_details(self.reload(self.admin), name='Super Admin', email=' SUPER@ifnmg.edu.br ')
        reloaded = self.reload(self.superadmin)
        self.assertEqual((reloaded.name, reloaded.email), ('Super Admin', 'super@ifnmg.edu.br'))
        self.assertTrue(reloaded.is_superadmin)

    def test_active_superadmin_can_change_another_superadmin_email(self):
        target = self.reload(self.other_superadmin)
        target.update_details(self.reload(self.superadmin), name='Outro', email='novo.super@ifnmg.edu.br')
        self.assertEqual(self.reload(self.other_superadmin).email, 'novo.super@ifnmg.edu.br')

    def test_inactive_superadmin_cannot_change_superadmin_email(self):
        executor = self.reload(self.superadmin)
        executor.is_active = False
        target = self.reload(self.other_superadmin)
        with self.assertRaises(SuperadminOnlyOperation):
            target.update_details(executor, name='Outro', email='novo.super@ifnmg.edu.br')
        self.assertEqual(self.reload(self.other_superadmin).email, 'outro@ifnmg.edu.br')

    def test_protection_uses_the_stored_superadmin_status(self):
        stale = self.reload(self.admin)
        User.objects.filter(pk=self.admin.pk).update(is_superadmin=True)
        with self.assertRaises(SuperadminOnlyOperation):
            stale.update_details(self.regular_executor(), name='Admin', email='novo@ifnmg.edu.br')
        self.assertEqual(self.reload(self.admin).email, 'admin@ifnmg.edu.br')

    def regular_executor(self):
        return User.objects.register(
            email='editor@ifnmg.edu.br', name='Editor', role=Role.objects.get(code='ADMINISTRADOR'),
        )

    def test_regular_user_email_can_be_changed_by_regular_admin(self):
        target = self.reload(self.admin)
        target.update_details(self.regular_executor(), name='Admin', email='admin.novo@ifnmg.edu.br')
        self.assertEqual(self.reload(self.admin).email, 'admin.novo@ifnmg.edu.br')

    def test_register_always_creates_regular_user(self):
        user = User.objects.register(
            email='novo@ifnmg.edu.br', name='Novo', role=Role.objects.get(code='ADMINISTRADOR'),
        )
        self.assertFalse(self.reload(user).is_superadmin)
