from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookings'
    verbose_name = 'Agenda'

    def ready(self):
        """Registra a fonte de ocupação, as notificações e a invalidação do cache público."""
        from bookings.models import Booking, BookingRequest
        from bookings.notifications import EVENTS
        from bookings.occupancy import BookingSource
        from notices.events import register as register_event
        from schedule import public_cache
        from schedule.occupancy import register_source

        register_source(BookingSource(), public=True)
        public_cache.watch(Booking)
        public_cache.watch(BookingRequest)
        for name, event in EVENTS.items():
            register_event(name, event)
