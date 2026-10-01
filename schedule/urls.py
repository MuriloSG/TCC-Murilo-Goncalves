from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from schedule import public_views, views

urlpatterns = [
    path('calendario/', csrf_exempt(public_views.PublicCalendarView.as_view()), name='public_calendar'),
    path('espacos/', login_required(views.SpaceListView.as_view()), name='spaces_list'),
    path('espacos/novo/', login_required(views.SpaceCreateView.as_view()), name='spaces_create'),
    path('espacos/<int:pk>/editar/', login_required(views.SpaceUpdateView.as_view()), name='spaces_update'),
    path('espacos/<int:pk>/desativar/', login_required(views.SpaceDeactivateView.as_view()), name='spaces_deactivate'),
    path('espacos/<int:pk>/reativar/', login_required(views.SpaceReactivateView.as_view()), name='spaces_reactivate'),
    path('espacos/<int:pk>/excluir/', login_required(views.SpaceDeleteView.as_view()), name='spaces_delete'),
    path('disciplinas/', login_required(views.SubjectListView.as_view()), name='subjects_list'),
    path('disciplinas/nova/', login_required(views.SubjectCreateView.as_view()), name='subjects_create'),
    path('disciplinas/<int:pk>/', login_required(views.SubjectDetailView.as_view()), name='subjects_detail'),
    path('disciplinas/<int:pk>/editar/', login_required(views.SubjectUpdateView.as_view()), name='subjects_update'),
    path('disciplinas/<int:pk>/excluir/', login_required(views.SubjectDeleteView.as_view()), name='subjects_delete'),
    path('turmas/', login_required(views.ClassGroupListView.as_view()), name='class_groups_list'),
    path('turmas/nova/', login_required(views.ClassGroupCreateView.as_view()), name='class_groups_create'),
    path('turmas/<int:pk>/', login_required(views.ClassGroupDetailView.as_view()), name='class_groups_detail'),
    path('turmas/<int:pk>/editar/', login_required(views.ClassGroupUpdateView.as_view()), name='class_groups_update'),
    path('turmas/<int:pk>/excluir/', login_required(views.ClassGroupDeleteView.as_view()), name='class_groups_delete'),
    path(
        'ensalamento/',
        login_required(views.SpaceAllocationGridView.as_view()),
        name='space_allocation_grid',
    ),
    path(
        'ensalamento/ocorrencias/cancelar/',
        login_required(views.OccurrenceCancelView.as_view()),
        name='space_allocation_occurrence_cancel',
    ),
    path(
        'ensalamento/recorrencias/encerrar/',
        login_required(views.RecurrenceEndView.as_view()),
        name='space_allocation_recurrence_end',
    ),
    path(
        'ensalamento/recorrencias/criar/',
        login_required(views.RecurrenceCreateView.as_view()),
        name='space_allocation_recurrence_create',
    ),
    path(
        'ensalamento/recorrencias/alterar/',
        login_required(views.RecurrenceChangeView.as_view()),
        name='space_allocation_recurrence_change',
    ),
    path(
        'ensalamento/excecoes/',
        login_required(views.AllocationExceptionListView.as_view()),
        name='space_allocation_exception_list',
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
