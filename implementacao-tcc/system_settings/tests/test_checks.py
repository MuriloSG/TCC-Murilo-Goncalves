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

    def test_deployment_checks(self):
        with self.subTest('valores de produção'):
            with override_settings(**PRODUCTION):
                self.assertEqual(self.ids(), [])
        with self.subTest('padrões de desenvolvimento'):
            values = PRODUCTION | DEVELOPMENT_SECRETS | {
                'REDIS_URL': f'redis://:{DEVELOPMENT_REDIS_PASSWORD}@redis:6379/0', 'SECURE_COOKIES': False,
            }
            with override_settings(**values):
                self.assertEqual(
                    self.ids(),
                    ['system_settings.E001', 'system_settings.E001', 'system_settings.E002', 'system_settings.W002'],
                )
        with self.subTest('Redis sem senha'):
            with override_settings(**(PRODUCTION | {'REDIS_URL': 'redis://redis:6379/0'})):
                self.assertEqual(self.ids(), ['system_settings.W001'])
        with self.subTest('sem Redis'):
            with override_settings(**(PRODUCTION | {'REDIS_URL': ''})):
                self.assertEqual(self.ids(), [])
