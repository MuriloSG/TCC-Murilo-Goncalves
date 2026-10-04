from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.test import TestCase, override_settings

from audit.models import AuditLog
from system_settings.models import SystemSetting
from system_settings.tests.base import SMTP_PASSWORD, configure_smtp, smtp_settings

VALID = {
    'host': 'smtp.ifnmg.edu.br',
    'port': 587,
    'security': 'STARTTLS',
    'username': 'agenda',
    'password': SMTP_PASSWORD,
    'from_email': 'IFAgenda <agenda@ifnmg.edu.br>',
}


class SaveSmtpTests(TestCase):
    def test_creates_and_updates_a_single_setting(self):
        SystemSetting.objects.save_smtp(**VALID)
        SystemSetting.objects.save_smtp(**(VALID | {'host': 'smtp2.ifnmg.edu.br'}))
        self.assertEqual(SystemSetting.objects.count(), 1)
        self.assertEqual(SystemSetting.objects.smtp().host, 'smtp2.ifnmg.edu.br')

    def test_database_refuses_duplicate_kind(self):
        configure_smtp()
        with self.assertRaises(IntegrityError):
            SystemSetting.objects.create(kind='smtp', value={})

    def test_invalid_data_is_refused_without_saving(self):
        cases = {
            'host': {'host': '  '},
            'port': {'port': 70000},
            'from_email': {'from_email': 'agenda'},
            'password': {'password': ''},
            'security': {'security': 'NENHUMA'},
        }
        for field, values in cases.items():
            with self.subTest(field):
                with self.assertRaises(ValidationError) as raised:
                    SystemSetting.objects.save_smtp(**(VALID | values))
                self.assertIn(field, raised.exception.message_dict)
        self.assertFalse(SystemSetting.objects.exists())

    def test_password_without_user_is_refused(self):
        with self.assertRaises(ValidationError) as raised:
            smtp_settings(username='').validate()
        self.assertIn('username', raised.exception.message_dict)

    def test_relay_without_credentials_is_accepted(self):
        SystemSetting.objects.save_smtp(**(VALID | {'username': '', 'password': '', 'security': 'NENHUMA', 'port': 25}))
        self.assertEqual(SystemSetting.objects.smtp().password, '')

    def test_blank_password_keeps_the_stored_one(self):
        SystemSetting.objects.save_smtp(**VALID)
        SystemSetting.objects.save_smtp(**(VALID | {'port': 465, 'security': 'SSL', 'password': ''}))
        smtp = SystemSetting.objects.smtp()
        self.assertEqual((smtp.port, smtp.password), (465, SMTP_PASSWORD))

    def test_removing_the_user_drops_the_password(self):
        SystemSetting.objects.save_smtp(**VALID)
        SystemSetting.objects.save_smtp(**(VALID | {'username': '', 'password': ''}))
        self.assertEqual(SystemSetting.objects.get().value['password'], '')

    def test_audit_has_no_password(self):
        SystemSetting.objects.save_smtp(**VALID)
        SystemSetting.objects.save_smtp(**(VALID | {'password': ''}))
        logs = AuditLog.objects.filter(resource='CONFIGURACAO').order_by('pk')
        self.assertEqual([log.action for log in logs], ['CRIAR', 'ALTERAR'])
        self.assertEqual([log.new_values['credencial'] for log in logs], ['alterada', 'mantida'])
        for log in logs:
            self.assertNotIn(SMTP_PASSWORD, str(log.new_values))


class EncryptionTests(TestCase):
    def test_password_is_encrypted_in_the_database(self):
        configure_smtp()
        with connection.cursor() as cursor:
            cursor.execute('SELECT value::text FROM system_settings_systemsetting')
            stored = cursor.fetchone()[0]
        self.assertNotIn(SMTP_PASSWORD, stored)
        self.assertEqual(SystemSetting.objects.smtp().password, SMTP_PASSWORD)

    def test_other_key_makes_the_setting_invalid(self):
        configure_smtp()
        with override_settings(CREDENTIALS_KEY='outra-chave'), self.assertRaises(ValidationError):
            SystemSetting.objects.smtp()

    def test_repr_hides_the_password(self):
        self.assertNotIn(SMTP_PASSWORD, repr(smtp_settings()))


class SchemaTests(TestCase):
    def test_unknown_field_is_refused(self):
        value = smtp_settings().to_value() | {'extra': 'x'}
        with self.assertRaises(ValidationError):
            SystemSetting(kind='smtp', value=value).clean()

    def test_missing_setting_is_none(self):
        self.assertIsNone(SystemSetting.objects.smtp())
