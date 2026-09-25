from django.contrib.auth.decorators import login_required
from django.urls import path

from schedule import views

urlpatterns = [
    path(
        'ensalamento/',
        login_required(views.SpaceAllocationGridView.as_view()),
        name='space_allocation_grid',
    ),
    path(
        'ensalamento/importacoes/',
        login_required(views.SpaceAllocationImportListView.as_view()),
        name='space_allocation_import_list',
    ),
    path(
        'ensalamento/importacoes/nova/',
        login_required(views.SpaceAllocationImportUploadView.as_view()),
        name='space_allocation_import_upload',
    ),
    path(
        'ensalamento/importacoes/<int:pk>/',
        login_required(views.SpaceAllocationImportDetailView.as_view()),
        name='space_allocation_import_detail',
    ),
    path(
        'ensalamento/importacoes/<int:pk>/confirmar/',
        login_required(views.SpaceAllocationImportConfirmView.as_view()),
        name='space_allocation_import_confirm',
    ),
    path(
        'ensalamento/importacoes/<int:pk>/descartar/',
        login_required(views.SpaceAllocationImportDiscardView.as_view()),
        name='space_allocation_import_discard',
    ),
    path(
        'ensalamento/importacoes/<int:pk>/excluir/',
        login_required(views.SpaceAllocationImportDeleteView.as_view()),
        name='space_allocation_import_delete',
    ),
]
