from django.apps import AppConfig


class SystemSettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'system_settings'
    verbose_name = 'Configurações do sistema'

    def ready(self):
        from django.core.checks import Tags, register

        from system_settings.checks import deployment_settings

        register(deployment_settings, Tags.security, deploy=True)
