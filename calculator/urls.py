from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('history/', views.history_view, name='history_view'),
    path('manifest.json', views.manifest_view, name='pwa_manifest'),
    path('sw.js', views.service_worker_view, name='pwa_sw'),
    path('favicon.ico', views.favicon_view, name='pwa_favicon'),
    path('api/calculate/', views.calculate_api, name='api_calculate'),
    path('api/save/', views.save_calculation_api, name='api_save'),
    path('api/calculations/<int:pk>/', views.get_calculation_api, name='api_get_calculation'),
    path('calculations/<int:pk>/delete/', views.delete_calculation_view, name='delete_calculation'),
]
