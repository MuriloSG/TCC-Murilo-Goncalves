from django.contrib.auth.decorators import login_required
from django.urls import path

from reports import views

urlpatterns = [
    path('relatorios/mapa-de-calor/', login_required(views.HeatmapView.as_view()), name='report_heatmap'),
    path(
        'relatorios/mapa-de-calor/<slug:day>/<int:slot>/',
        login_required(views.HeatmapCellView.as_view()),
        name='report_heatmap_cell',
    ),
    path('relatorios/solicitacoes/', login_required(views.RequestsReportView.as_view()), name='report_requests'),
]
