"""Ator da requisição e registro do acesso às funcionalidades (D5, D13).

O ator é definido em volta da chamada da view, para que as operações do model
registrem as ações sem conhecer a requisição. O acesso é registrado a partir do
`audit_resource` declarado na view, como a permissão é declarada em
`permission_required`. Fragmentos e modais pedidos pelo htmx são renderização da
tela atual, e não acesso a uma funcionalidade.
"""

from audit import catalog
from audit.context import Actor, acting_as
from audit.models import AuditLog


def request_actor(request):
    user = getattr(request, 'user', None)
    return Actor(
        user=user if user is not None and user.is_authenticated else None,
        ip_address=request.META.get('REMOTE_ADDR') or None,
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        origin=catalog.INTERFACE,
    )


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.audit_resource = None
        with acting_as(request_actor(request)):
            response = self.get_response(request)
            self.record_access(request, response)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.audit_resource = getattr(view_func, 'audit_resource', None) or getattr(
            getattr(view_func, 'view_class', None), 'audit_resource', None,
        )
        return None

    def record_access(self, request, response):
        """Registra o acesso a uma tela do fluxo de utilização, e só ele."""
        if not request.audit_resource or request.method != 'GET':
            return
        if response.status_code != 200 or getattr(request, 'htmx', False):
            return
        match = request.resolver_match
        AuditLog.objects.record(
            catalog.ACCESS,
            request.audit_resource,
            metadata={'rota': match.url_name if match else '', 'caminho': request.path},
        )
