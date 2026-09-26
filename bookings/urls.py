from django.contrib.auth.decorators import login_required
from django.urls import path

from bookings import views

urlpatterns = [
    path('agenda/', login_required(views.AgendaGridView.as_view()), name='agenda_grid'),
]
