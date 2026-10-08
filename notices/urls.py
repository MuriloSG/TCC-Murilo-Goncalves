from django.contrib.auth.decorators import login_required
from django.urls import path

from notices import views

urlpatterns = [
    path(
        'notificacoes/',
        login_required(views.NoticeListView.as_view()),
        name='notice_list',
    ),
    path(
        'notificacoes/nova/',
        login_required(views.NoticeCreateView.as_view()),
        name='notice_create',
    ),
    path(
        'notificacoes/opcoes/usuarios/',
        login_required(views.NoticeUserOptionsView.as_view()),
        name='notice_user_options',
    ),
    path(
        'notificacoes/publicar/',
        login_required(views.NoticePublishView.as_view()),
        name='notice_publish',
    ),
    path(
        'notificacoes/<int:pk>/abrir/',
        login_required(views.NotificationOpenView.as_view()),
        name='notification_open',
    ),
    path(
        'notificacoes/sino/',
        login_required(views.NotificationsPanelView.as_view()),
        name='notifications_panel',
    ),
    path(
        'notificacoes/lidas/',
        login_required(views.NotificationsReadAllView.as_view()),
        name='notifications_read_all',
    ),
]
