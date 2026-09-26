from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookings'
    verbose_name = 'Agenda'

    def ready(self):
        """Registra os agendamentos aprovados como fonte de ocupação das Grades e do calendário público."""
        from bookings.occupancy import BookingSource
        from schedule.occupancy import register_source

        register_source(BookingSource(), public=True)
