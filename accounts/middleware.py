from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


class PermissionMiddleware:
    """Aplica a permissão que a view declara em `permission_required` (D14).

    A autenticação é exigida na URL, com login_required. Mesmo assim, um anônimo
    que chegue a uma view com permissão é mandado ao login, para que esquecer o
    login_required numa rota não deixe a view aberta.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        permission = getattr(view_func, 'permission_required', None) or getattr(
            getattr(view_func, 'view_class', None), 'permission_required', None,
        )
        if permission is None:
            return None
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.has_perm(permission):
            raise PermissionDenied
        return None
