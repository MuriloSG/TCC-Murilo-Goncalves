from django.apps import AppConfig


class ScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedule'
    verbose_name = 'Ensalamento'

    def ready(self):
        """Registra a importação do ensalamento e os models cujas gravações invalidam o cache público."""
        from accounts.models import User
        from imports.registry import register
        from schedule import models, public_cache
        from schedule.imports import SpaceAllocationImport

        register(SpaceAllocationImport())
        for model in (
            models.Semester, models.Allocation, models.AllocationException, models.TimeSlot, models.Space,
            models.Teacher, models.Course, models.Subject, models.ClassGroup, models.ClassOffering,
            models.TeachingAssignment,
        ):
            public_cache.watch(model)
        public_cache.watch(User, fields=public_cache.USER_PUBLIC_FIELDS)
