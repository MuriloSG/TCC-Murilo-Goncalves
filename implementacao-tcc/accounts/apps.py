from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Contas'

    def ready(self):
        from accounts.emails import PASSWORD_LINK, PASSWORD_RESET, password_link, password_reset
        from accounts.imports import UserImport
        from accounts.notifications import ROLE_CHANGED, role_changed
        from notices.events import register as register_event
        from imports.registry import register as register_import
        from outbox.handlers import register

        register(PASSWORD_LINK, password_link)
        register(PASSWORD_RESET, password_reset)
        register_event(ROLE_CHANGED, role_changed)
        register_import(UserImport())
