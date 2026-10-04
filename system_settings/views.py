"""Tela do servidor de e-mail (D9 da Change configurar-servidor-de-email).

A página e o formulário exigem CONFIGURACAO.EDITAR. A senha gravada nunca entra
no contexto: a tela só sabe se ela existe.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from accounts import permissions
from accounts.views import OperationFormView
from audit import catalog
from outbox.models import OutboxEntry
from system_settings.forms import SmtpForm
from system_settings.models import Security, SystemSetting


def stored_smtp():
    return SystemSetting.objects.filter(kind=SystemSetting.Kind.SMTP).first()


class SmtpDetailView(TemplateView):
    permission_required = permissions.SETTINGS_EDIT
    audit_resource = catalog.SETTINGS
    template_name = 'system_settings/smtp_detail.html'

    def get_context_data(self, **kwargs):
        setting = stored_smtp()
        problem = None
        if setting is not None:
            try:
                SystemSetting.objects.smtp()
            except ValidationError as error:
                problem = ' '.join(error.messages)
        value = setting.value if setting else {}
        return super().get_context_data(
            setting=setting,
            problem=problem,
            smtp={key: item for key, item in value.items() if key != 'password'},
            security_label=dict(Security.choices).get(value.get('security'), ''),
            has_password=bool(value.get('password')),
            pending=OutboxEntry.objects.filter(status=OutboxEntry.Status.PENDING).count(),
            **kwargs,
        )


class SmtpUpdateView(OperationFormView):
    permission_required = permissions.SETTINGS_EDIT
    audit_resource = catalog.SETTINGS
    form_class = SmtpForm
    template_name = 'system_settings/smtp_form.html'
    modal_template_name = 'system_settings/smtp_form_modal.html'
    success_url = reverse_lazy('settings_email')
    submit_label = 'Salvar servidor de e-mail'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.setting = stored_smtp()
        self.title = 'Editar servidor de e-mail' if self.setting else 'Cadastrar servidor de e-mail'

    def get_initial(self):
        if self.setting is None:
            return {'port': 587, 'security': 'STARTTLS'}
        return {key: item for key, item in self.setting.value.items() if key != 'password'}

    def get_form_kwargs(self):
        has_password = bool(self.setting and self.setting.value.get('password'))
        return super().get_form_kwargs() | {'has_password': has_password}

    def perform(self, data):
        SystemSetting.objects.save_smtp(**data)
        messages.success(self.request, 'Servidor de e-mail salvo.')
