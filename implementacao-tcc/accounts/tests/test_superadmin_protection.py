from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import SuperadminOnlyOperation, User
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import management_role, requester_role


class SuperadminEmailProtectionTests(IsolatedCasesMixin, TestCase):
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

    def regular_executor(self):
        return User.objects.register(
            email='editor@ifnmg.edu.br', name='Editor', role=management_role(),
        )

    def test_superadmin_email_changes_only_by_an_active_superadmin(self):
        with self.case('administrador comum, superadmin ativo'):
            target = self.reload(self.superadmin)
            with self.assertRaises(SuperadminOnlyOperation) as raised:
                target.update_details(self.reload(self.admin), name='Super', email='novo@ifnmg.edu.br')
            self.assertIsInstance(raised.exception, ValidationError)
            self.assertTrue(raised.exception.messages)
            self.assertEqual(target.email, 'super@ifnmg.edu.br')
            self.assertEqual(self.reload(self.superadmin).email, 'super@ifnmg.edu.br')
        with self.case('administrador comum, superadmin inativo'):
            User.objects.filter(pk=self.superadmin.pk).update(is_active=False)
            target = self.reload(self.superadmin)
            with self.assertRaises(SuperadminOnlyOperation):
                target.update_details(self.reload(self.admin), name='Super', email='novo@ifnmg.edu.br')
            self.assertEqual(self.reload(self.superadmin).email, 'super@ifnmg.edu.br')
        with self.case('superadmin inativo'):
            executor = self.reload(self.superadmin)
            executor.is_active = False
            target = self.reload(self.other_superadmin)
            with self.assertRaises(SuperadminOnlyOperation):
                target.update_details(executor, name='Outro', email='novo.super@ifnmg.edu.br')
            self.assertEqual(self.reload(self.other_superadmin).email, 'outro@ifnmg.edu.br')
        with self.case('situação gravada'):
            stale = self.reload(self.admin)
            User.objects.filter(pk=self.admin.pk).update(is_superadmin=True)
            with self.assertRaises(SuperadminOnlyOperation):
                stale.update_details(self.regular_executor(), name='Admin', email='novo@ifnmg.edu.br')
            self.assertEqual(self.reload(self.admin).email, 'admin@ifnmg.edu.br')

    def test_allowed_changes(self):
        with self.case('nome pelo administrador comum'):
            target = self.reload(self.superadmin)
            target.update_details(self.reload(self.admin), name='Super Admin', email=' SUPER@ifnmg.edu.br ')
            reloaded = self.reload(self.superadmin)
            self.assertEqual((reloaded.name, reloaded.email), ('Super Admin', 'super@ifnmg.edu.br'))
            self.assertTrue(reloaded.is_superadmin)
        with self.case('e-mail por superadmin ativo'):
            target = self.reload(self.other_superadmin)
            target.update_details(self.reload(self.superadmin), name='Outro', email='novo.super@ifnmg.edu.br')
            self.assertEqual(self.reload(self.other_superadmin).email, 'novo.super@ifnmg.edu.br')


class SuperadminProtectionViewTests(IsolatedCasesMixin, TestCase):
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

    def test_email_field_follows_the_protection(self):
        with self.case('somente leitura'):
            self.client.force_login(self.admin)
            response = self.client.get(self.edit_url(self.superadmin))
            self.assertTrue(response.context['form'].fields['email'].widget.attrs.get('readonly'))
            self.assertContains(response, 'readonly')
        with self.case('editável'):
            self.client.force_login(self.other_superadmin)
            response = self.client.get(self.edit_url(self.superadmin))
            self.assertNotIn('readonly', response.context['form'].fields['email'].widget.attrs)
        with self.case('POST forjado'):
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
