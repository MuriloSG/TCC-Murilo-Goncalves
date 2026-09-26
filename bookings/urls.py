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
]
