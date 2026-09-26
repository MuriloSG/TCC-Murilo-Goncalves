from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookings'
    verbose_name = 'Agenda'

    def ready(self):
        """Registra os agendamentos aprovados como fonte de ocupação e as transições que notificam."""
        from bookings.notifications import EVENTS
        from bookings.occupancy import BookingSource
        from notices.events import register as register_event
        from schedule.occupancy import register_source

        register_source(BookingSource(), public=True)
        for name, event in EVENTS.items():
            register_event(name, event)
