from django.apps import AppConfig


class ScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedule'
    verbose_name = 'Ensalamento'

    def ready(self):
        from imports.registry import register
        from schedule.imports import SpaceAllocationImport

        register(SpaceAllocationImport())
