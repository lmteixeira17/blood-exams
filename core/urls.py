"""
URL configuration for the core app.
"""

from django.urls import path

from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Auth
    path('register/', views.register_view, name='register'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # Exam operations
    path('upload/', views.upload_view, name='upload'),
    path('exam/<int:exam_id>/', views.exam_detail_view, name='exam_detail'),
    path('exam/<int:exam_id>/delete/', views.exam_delete_view, name='exam_delete'),
    path('exam/<int:exam_id>/reprocess/', views.exam_reprocess_view, name='exam_reprocess'),
    path('history/', views.exam_history_view, name='exam_history'),

    # Biomarker charts
    path('biomarker/<str:code>/', views.biomarker_chart_view, name='biomarker_chart'),
    path('biomarker/<str:code>/trend/', views.biomarker_trend_api, name='biomarker_trend_api'),

    # API
    path('api/biomarker/<str:code>/', views.api_biomarker_data, name='api_biomarker_data'),

    # Admin
    path('admin-panel/', views.admin_users_view, name='admin_users'),

    # Health
    path('health/', views.health_view, name='health'),
]
