from django.contrib.auth.decorators import login_required
from django.urls import path

from tutorials import views

urlpatterns = [
    path('ajuda/', login_required(views.HelpCenterView.as_view()), name='help_center'),
]
