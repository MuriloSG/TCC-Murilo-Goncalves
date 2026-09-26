from django.contrib.auth.decorators import login_required
from django.urls import path

from bookings import views

urlpatterns = [
    path('agenda/', login_required(views.AgendaGridView.as_view()), name='agenda_grid'),
    path('agenda/solicitar/', login_required(views.BookingRequestCreateView.as_view()), name='agenda_request_create'),
    path('agenda/minhas-solicitacoes/', login_required(views.MyBookingRequestListView.as_view()), name='agenda_my_requests'),
    path('agenda/minhas-solicitacoes/<int:pk>/', login_required(views.MyBookingRequestDetailView.as_view()), name='agenda_my_request'),
    path(
        'agenda/minhas-solicitacoes/<int:pk>/aceitar/',
        login_required(views.AcceptSuggestionView.as_view()),
        name='agenda_my_request_accept',
    ),
    path(
        'agenda/minhas-solicitacoes/<int:pk>/recusar/',
        login_required(views.DeclineSuggestionView.as_view()),
        name='agenda_my_request_decline',
    ),
    path('agenda/solicitacoes/', login_required(views.BookingRequestReviewListView.as_view()), name='agenda_review_list'),
    path('agenda/solicitacoes/<int:pk>/', login_required(views.BookingRequestReviewDetailView.as_view()), name='agenda_review_detail'),
    path('agenda/solicitacoes/<int:pk>/aprovar/', login_required(views.ApproveView.as_view()), name='agenda_review_approve'),
    path('agenda/solicitacoes/<int:pk>/rejeitar/', login_required(views.RejectView.as_view()), name='agenda_review_reject'),
    path('agenda/solicitacoes/<int:pk>/sugerir/', login_required(views.SuggestView.as_view()), name='agenda_review_suggest'),
]
