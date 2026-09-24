"""Consulta dos registros de auditoria (D12).

A lista é somente leitura: não existe rota que altere ou exclua um registro.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView

from accounts import permissions
from audit import catalog
from audit.forms import AuditFilterForm, user_option_label
from audit.models import AuditLog
from ui.pagination import paginate
from ui.views import ModalView, OptionsView


class AuditLogListView(ListView):
    permission_required = permissions.AUDIT_VIEW
    audit_resource = catalog.AUDIT
    template_name = 'audit/log_list.html'
    context_object_name = 'entries'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters = AuditFilterForm(request.GET)
        self.criteria = self.filters.criteria()

    def get_queryset(self):
        return AuditLog.objects.search(**self.criteria).select_related('user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            filters=self.filters,
            filtered=any(value for value in self.criteria.values()),
            **kwargs,
        )
        context['page'] = paginate(self.request, self.object_list)
        context['entries'] = context['page'].object_list
        return context


class AuditLogDetailView(ModalView, DetailView):
    permission_required = permissions.AUDIT_VIEW
    audit_resource = catalog.AUDIT
    model = AuditLog
    template_name = 'audit/log_detail.html'
    modal_template_name = 'audit/log_detail_modal.html'
    context_object_name = 'entry'
    close_url = reverse_lazy('audit_log_list')


class UserOptionsView(OptionsView):
    """Opções do filtro por usuário, paginadas no servidor (D5)."""

    permission_required = permissions.AUDIT_VIEW

    def get_queryset(self, term):
        users = get_user_model().objects.order_by('name', 'email')
        if term:
            users = users.filter(Q(name__icontains=term) | Q(email__icontains=term))
        return users

    def label(self, user):
        return user_option_label(user)
