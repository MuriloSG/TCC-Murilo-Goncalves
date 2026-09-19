"""Classe base das views de ação que abrem em modal (D16)."""

import json
from urllib.parse import urlsplit

from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.base import TemplateResponseMixin, View
from django_htmx.http import HttpResponseClientRedirect


class ModalView(TemplateResponseMixin, View):
    """Responde com o fragmento do modal quando a requisição vem do htmx.

    Sem o htmx, a mesma URL responde com a página completa de `template_name`,
    que inclui o mesmo fragmento. No sucesso, o htmx recebe HX-Redirect em vez de
    um redirecionamento, e a página de origem é recarregada. Quando a origem é a
    própria URL de destino, os parâmetros dela (busca e filtro) são mantidos.
    """

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
        """Redireciona para `url`: pelo htmx, recarrega a tela de origem ou, quando
        a ação continua numa próxima etapa (`continues_in_modal`), abre `url` no
        mesmo modal, sem mudar o endereço da página.
        """
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
