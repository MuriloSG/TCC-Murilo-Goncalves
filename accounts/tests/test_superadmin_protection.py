from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import SuperadminOnlyOperation, User
from accounts.tests.roles import management_role, requester_role


class SuperadminEmailProtectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        teacher = requester_role()
        administrator = management_role()
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
            email='editor@ifnmg.edu.br', name='Editor', role=management_role(),
        )


class SuperadminProtectionViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        teacher = requester_role()
        administrator = management_role()
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=administrator)
        cls.superadmin = User.objects.register(email='super@ifnmg.edu.br', name='Super', role=teacher)
        cls.superadmin.set_superadmin(True)
        cls.other_superadmin = User.objects.register(email='outro@ifnmg.edu.br', name='Outro', role=teacher)
        cls.other_superadmin.set_superadmin(True)

    def edit_url(self, user):
        return f'/usuarios/{user.pk}/editar/'

    def reload(self, user):
        return User.objects.get(pk=user.pk)

    def test_email_is_read_only_for_regular_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.edit_url(self.superadmin))
        self.assertTrue(response.context['form'].fields['email'].widget.attrs.get('readonly'))
        self.assertContains(response, 'readonly')

    def test_email_is_editable_for_active_superadmin(self):
        self.client.force_login(self.other_superadmin)
        response = self.client.get(self.edit_url(self.superadmin))
        self.assertNotIn('readonly', response.context['form'].fields['email'].widget.attrs)

    def test_forged_email_change_by_regular_admin_is_refused_with_error(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.edit_url(self.superadmin), {'name': 'Novo', 'email': 'outro.mail@ifnmg.edu.br'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Somente um superadmin ativo pode alterar o e-mail')
        superadmin = self.reload(self.superadmin)
        self.assertEqual((superadmin.name, superadmin.email), ('Super', 'super@ifnmg.edu.br'))

    def test_superadmin_flag_sent_in_requests_is_ignored(self):
        self.client.force_login(self.other_superadmin)
        for url, data in [
            (self.edit_url(self.superadmin), {'name': 'Super', 'email': 'super@ifnmg.edu.br', 'is_superadmin': ''}),
            (f'/usuarios/{self.superadmin.pk}/perfil/', {'role': management_role().pk, 'is_superadmin': 'false'}),
            (self.edit_url(self.admin), {'name': 'Admin', 'email': 'admin@ifnmg.edu.br', 'is_superadmin': 'on'}),
            (f'/usuarios/{self.admin.pk}/perfil/', {'role': management_role().pk, 'is_superadmin': 'true'}),
        ]:
            with self.subTest(url):
                self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertTrue(self.reload(self.superadmin).is_superadmin)
        self.assertFalse(self.reload(self.admin).is_superadmin)

    def test_regular_admin_cannot_deactivate_or_change_role_of_superadmin(self):
        self.client.force_login(self.admin)
        response = self.client.post(f'/usuarios/{self.superadmin.pk}/desativar/', follow=True)
        self.assertContains(response, 'Somente um superadmin ativo pode alterar')
        response = self.client.post(
            f'/usuarios/{self.superadmin.pk}/perfil/', {'role': management_role().pk},
        )
        self.assertContains(response, 'Somente um superadmin ativo pode alterar')
        superadmin = self.reload(self.superadmin)
        self.assertTrue(superadmin.is_active)
        self.assertEqual(superadmin.role.code, 'SOLICITACAO')

    def test_superadmin_deactivates_another_superadmin_who_keeps_the_flag(self):
        self.client.force_login(self.other_superadmin)
        self.client.post(f'/usuarios/{self.superadmin.pk}/desativar/')
        superadmin = self.reload(self.superadmin)
        self.assertFalse(superadmin.is_active)
        self.assertTrue(superadmin.is_superadmin)
