from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from notices.models import Notification

PANEL_SIZE = 10


def panel_context(request):
    """Dados do sino, iguais no painel da página e no fragmento buscado após um aviso."""
    user = request.user
    if not user.is_authenticated:
        return {'request': request, 'origin': panel_origin(request), 'items': [], 'unread': 0}
    return {
        'request': request,
        'origin': panel_origin(request),
        'items': Notification.objects.for_user(user)[:PANEL_SIZE],
        'unread': Notification.objects.unread_count(user),
    }


def safe_origin(request, origin):
    if origin and url_has_allowed_host_and_scheme(origin, {request.get_host()}, request.is_secure()):
        return origin
    return ''


def panel_origin(request):
    """Tela para onde as ações do sino voltam, recebida em `origem` porque o fragmento tem outra rota."""
    if request.path == reverse('notifications_panel'):
        return safe_origin(request, request.GET.get('origem', '')) or reverse('home')
    return request.get_full_path()


def redirect_target(request, notification=None):
    """Destino da notificação, a origem ou a página inicial; a origem só vale se for do próprio sistema."""
    if notification is not None and notification.target_url:
        return notification.target_url
    return safe_origin(request, request.POST.get('next', '')) or reverse('home')
