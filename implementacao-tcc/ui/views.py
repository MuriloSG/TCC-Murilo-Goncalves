"""Classes base da interface: ações em modal e opções de um campo de seleção."""

import json
from urllib.parse import urlsplit

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.generic.base import TemplateResponseMixin, View
from django_htmx.http import HttpResponseClientRedirect

from ui.pagination import OPTIONS_PAGE_SIZE, paginate


class ModalView(TemplateResponseMixin, View):
    """Responde com o fragmento do modal ao htmx e com a página completa sem ele."""

    modal_template_name = None
    close_url = None
    continues_in_modal = False

    def get_template_names(self):
        if self.request.htmx:
            return [self.modal_template_name]
        return super().get_template_names()

    def get_close_url(self):
        """Destino do "Fechar" na página completa: a tela de origem da ação."""
        return self.close_url or self.success_url

    def get_context_data(self, **kwargs):
        return super().get_context_data(close_url=self.get_close_url(), **kwargs)

    def redirect_to(self, url):
        """Pelo htmx, recarrega a origem ou, com `continues_in_modal`, abre `url` no mesmo modal."""
        url = str(url)
        if not self.request.htmx:
            return HttpResponseRedirect(url)
        if self.continues_in_modal:
            response = HttpResponse()
            response['HX-Location'] = json.dumps({'path': url, 'target': '#modal', 'push': 'false'})
            return response
        current = self.request.htmx.current_url_abs_path
        if current and urlsplit(current).path == urlsplit(url).path:
            url = current
        return HttpResponseClientRedirect(url)

    def form_valid(self, form):
        return self.redirect_to(self.get_success_url())


class OptionsView(View):
    """Opções de um campo de seleção, paginadas no servidor, sem conhecer o domínio."""

    http_method_names = ['get']
    page_size = OPTIONS_PAGE_SIZE

    def get_queryset(self, term):
        raise NotImplementedError

    def label(self, item):
        return str(item)

    def get(self, request, *args, **kwargs):
        page = paginate(request, self.get_queryset(request.GET.get('busca', '').strip()), self.page_size)
        return JsonResponse({
            'opcoes': [{'valor': str(item.pk), 'rotulo': self.label(item)} for item in page.object_list],
            'tem_mais': page.has_next(),
        })
