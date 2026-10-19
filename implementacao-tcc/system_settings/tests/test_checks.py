from django.test import SimpleTestCase, override_settings

from system_settings.checks import DEVELOPMENT_REDIS_PASSWORD, DEVELOPMENT_SECRETS, deployment_settings

PRODUCTION = {
    'SECRET_KEY': 'segredo-proprio-da-instalacao',
    'CREDENTIALS_KEY': 'chave-propria-da-instalacao',
    'REDIS_URL': 'redis://:senha-propria@redis:6379/0',
    'SECURE_COOKIES': True,
}


class DeploymentCheckTests(SimpleTestCase):
    def ids(self):
        return [problem.id for problem in deployment_settings(None)]

    def test_production_values_pass(self):
        with override_settings(**PRODUCTION):
            self.assertEqual(self.ids(), [])

    def test_development_defaults_are_refused(self):
        values = PRODUCTION | DEVELOPMENT_SECRETS | {
            'REDIS_URL': f'redis://:{DEVELOPMENT_REDIS_PASSWORD}@redis:6379/0', 'SECURE_COOKIES': False,
        }
        with override_settings(**values):
            self.assertEqual(
                self.ids(),
                ['system_settings.E001', 'system_settings.E001', 'system_settings.E002', 'system_settings.W002'],
            )

    def test_redis_without_password_is_warned(self):
        with override_settings(**(PRODUCTION | {'REDIS_URL': 'redis://redis:6379/0'})):
            self.assertEqual(self.ids(), ['system_settings.W001'])

    def test_without_redis_nothing_is_said_about_it(self):
        with override_settings(**(PRODUCTION | {'REDIS_URL': ''})):
            self.assertEqual(self.ids(), [])
