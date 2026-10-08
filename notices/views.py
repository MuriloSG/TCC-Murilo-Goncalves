"""Telas das notificações; abrir e marcar como lida são POST com CSRF e funcionam sem JavaScript."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic.base import TemplateView, View
from django.views.generic.edit import FormView

from audit import catalog as audit_catalog

from accounts import permissions
from accounts.utils import add_operation_error
from notices import catalog
from notices.forms import NoticeForm
from notices.models import MESSAGE_MAX_LENGTH, Notice, Notification, resolve_recipients
from ui.pagination import paginate
from notices.utils import panel_context, redirect_target
from ui.views import OptionsView


class NotificationOpenView(View):
    """Marca a notificação do usuário como lida e leva ao destino dela."""

    http_method_names = ['post']

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_as_read()
        return HttpResponseRedirect(redirect_target(request, notification))


class NotificationsReadAllView(View):
    """Marca como lidas todas as notificações não lidas do usuário."""

    http_method_names = ['post']

    def post(self, request):
        Notification.objects.mark_all_as_read(request.user)
        return HttpResponseRedirect(redirect_target(request))


class NotificationsPanelView(TemplateView):
    """Fragmento do sino que a interface busca após um aviso do canal e ao reconectar."""

    template_name = 'ui/components/notifications.html'

    def get_context_data(self, **kwargs):
        return panel_context(self.request)


class NoticeListView(TemplateView):
    """Só as publicações globais; as direcionadas ficam na consulta da auditoria."""

    permission_required = permissions.NOTICE_PUBLISH
    audit_resource = audit_catalog.NOTICE
    template_name = 'notices/notice_list.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            page=paginate(self.request, Notice.objects.global_ones()),
            **kwargs,
        )


class NoticeUserOptionsView(OptionsView):
    """Opções de destinatários paginadas no servidor."""

    permission_required = permissions.NOTICE_PUBLISH

    def get_queryset(self, term):
        people = resolve_recipients(catalog.ALL_USERS).order_by('name')
        if term:
            people = people.filter(Q(name__icontains=term) | Q(email__icontains=term))
        return people

    def label(self, item):
        return f'{item.name} ({item.email})'


class NoticeCreateView(FormView):
    """Primeira etapa: os dados da notificação, que seguem para a revisão."""

    permission_required = permissions.NOTICE_PUBLISH
    template_name = 'notices/notice_form.html'
    review_template_name = 'notices/notice_review.html'
    form_class = NoticeForm
    step = 'criar'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if 'voltar' in request.POST:
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(step=self.step, **kwargs)
        message = context['form']['message'].value() or ''
        context.update(
            message_limit=MESSAGE_MAX_LENGTH,
            message_length=len(message),
            active_users=resolve_recipients(catalog.ALL_USERS).count(),
        )
        return context

    def form_valid(self, form):
        return render(self.request, self.review_template_name, review_context(self.request, form))


class NoticePublishView(FormView):
    """Segunda etapa: publica o que foi revisado e leva à mensagem de sucesso."""

    permission_required = permissions.NOTICE_PUBLISH
    template_name = 'notices/notice_review.html'
    form_class = NoticeForm
    http_method_names = ['post']
    success_url = reverse_lazy('notice_list')

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            notice = Notification.objects.publish_manually(
                data['type'],
                data['title'],
                data['message'],
                data['destination'],
                role=data.get('role'),
                users=data.get('users') or (),
                published_by=self.request.user,
            )
        except ValidationError as error:
            add_operation_error(form, error)
            return self.form_invalid(form)
        reached = notice.recipients_count
        people = 'destinatário' if reached == 1 else 'destinatários'
        messages.success(self.request, f'Notificação "{notice.title}" publicada para {reached} {people}.')
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if getattr(form, 'cleaned_data', {}).get('type'):
            return self.render_to_response(review_context(self.request, form))
        return HttpResponseRedirect(reverse('notice_create'))


def review_context(request, form):
    """Contexto da revisão, montado a partir do que foi preenchido, sem gravar nada."""
    return {
        'form': form,
        'step': 'revisar',
        'preview': form.preview(),
        'destination_label': form.destination_label(),
        'reached': form.recipients().count(),
        'values': form.resubmit_values(),
        'back_url': reverse('notice_create'),
        'publish_url': reverse('notice_publish'),
    }
