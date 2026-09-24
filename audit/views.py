"""Consulta dos registros de auditoria (D12).

A lista é somente leitura: não existe rota que altere ou exclua um registro.
"""

from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView

from accounts import permissions
from audit import catalog
from audit.forms import AuditFilterForm
from audit.models import AuditLog
from ui.pagination import paginate
from ui.views import ModalView


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
