from django.contrib.auth.decorators import login_required
from django.urls import path

from schedule import views

urlpatterns = [
    path('espacos/', login_required(views.SpaceListView.as_view()), name='spaces_list'),
    path('espacos/novo/', login_required(views.SpaceCreateView.as_view()), name='spaces_create'),
    path('espacos/<int:pk>/editar/', login_required(views.SpaceUpdateView.as_view()), name='spaces_update'),
    path('espacos/<int:pk>/desativar/', login_required(views.SpaceDeactivateView.as_view()), name='spaces_deactivate'),
    path('espacos/<int:pk>/reativar/', login_required(views.SpaceReactivateView.as_view()), name='spaces_reactivate'),
    path('espacos/<int:pk>/excluir/', login_required(views.SpaceDeleteView.as_view()), name='spaces_delete'),
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
    path(
        'ensalamento/importacoes/<int:pk>/espacos/decidir/',
        login_required(views.SpaceDecisionView.as_view()),
        name='space_allocation_import_decide',
    ),
    path(
        'ensalamento/importacoes/<int:pk>/espacos/desfazer/',
        login_required(views.SpaceWithdrawView.as_view()),
        name='space_allocation_import_withdraw',
    ),
    path(
        'ensalamento/importacoes/<int:pk>/espacos/associar/',
        login_required(views.SpaceAssociateView.as_view()),
        name='space_allocation_import_associate',
    ),
    path(
        'ensalamento/importacoes/<int:pk>/atualizar/',
        login_required(views.SpaceRefreshView.as_view()),
        name='space_allocation_import_refresh',
    ),
]
