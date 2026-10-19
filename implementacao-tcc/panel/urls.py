from django.contrib.auth.decorators import login_required
from django.urls import path

from panel import views

urlpatterns = [
    path('painel/', login_required(views.PanelView.as_view()), name='panel'),
    path('painel/pendencias/<slug:key>/', login_required(views.PanelIssueView.as_view()), name='panel_issue'),
]
