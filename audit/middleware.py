"""Define o ator da requisição e registra o acesso pelo `audit_resource` da view, exceto nos pedidos htmx."""

from allauth.account.adapter import get_adapter
from django.core.exceptions import ImproperlyConfigured, PermissionDenied

from audit import catalog
from audit.context import Actor, acting_as
from audit.models import AuditLog


def client_ip(request):
    """IP pela mesma regra de proxy confiável dos limites do allauth; sem proxy declarado, o `REMOTE_ADDR`."""
    try:
        return get_adapter().get_client_ip(request)
    except (ImproperlyConfigured, PermissionDenied):
        return request.META.get('REMOTE_ADDR') or None


def request_actor(request):
    user = getattr(request, 'user', None)
    return Actor(
        user=user if user is not None and user.is_authenticated else None,
        ip_address=client_ip(request),
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
