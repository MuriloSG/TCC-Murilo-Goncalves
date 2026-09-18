from django.urls import path

from accounts import views

urlpatterns = [
    path('inicio/', views.HomeView.as_view(), name='home'),
]
