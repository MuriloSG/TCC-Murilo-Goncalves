from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View

from accounts import permissions
from accounts.middleware import PermissionMiddleware
from accounts.models import User
from accounts.tests.roles import management_role, requester_role


class ClassView(View):
    permission_required = permissions.USER_VIEW


def function_view(request):
    return HttpResponse()


function_view.permission_required = permissions.USER_VIEW


def open_view(request):
    return HttpResponse()


class PermissionMiddlewareTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.register(
            email='admin@ifnmg.edu.br', name='Admin', role=management_role(),
        )
        cls.teacher = User.objects.register(
            email='docente@ifnmg.edu.br', name='Docente', role=requester_role(),
        )

    def process(self, view, user):
        request = RequestFactory().get('/usuarios/?pagina=2')
        request.user = user
        middleware = PermissionMiddleware(lambda request: HttpResponse())
        return middleware.process_view(request, view, (), {})

    def test_reads_the_permission_of_the_view_and_sends_the_anonymous_to_the_login(self):
        with self.subTest('views de classe e de função'):
            for view in (ClassView.as_view(), function_view):
                with self.subTest(view):
                    self.assertIsNone(self.process(view, self.admin))
                    with self.assertRaises(PermissionDenied):
                        self.process(view, self.teacher)
        with self.subTest('anônimo'):
            response = self.process(ClassView.as_view(), AnonymousUser())
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response['Location'], '/contas/login/?next=/usuarios/%3Fpagina%3D2')
