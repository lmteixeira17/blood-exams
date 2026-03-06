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
    path('complete-profile/', views.complete_profile_view, name='complete_profile'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # Exam operations
    path('upload/', views.upload_view, name='upload'),
    path('exam/<int:exam_id>/', views.exam_detail_view, name='exam_detail'),
    path('exam/<int:exam_id>/processing/', views.exam_processing_view, name='exam_processing'),
    path('exam/<int:exam_id>/status/', views.exam_status_api, name='exam_status_api'),
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
    path('admin-panel/user/new/', views.admin_user_create_view, name='admin_user_create'),
    path('admin-panel/user/<int:user_id>/edit/', views.admin_user_edit_view, name='admin_user_edit'),
    path('admin-panel/user/<int:user_id>/delete/', views.admin_user_delete_view, name='admin_user_delete'),
    path('admin-panel/user/<int:user_id>/view-as/', views.admin_view_as_user, name='admin_view_as'),
    path('admin-panel/stop-impersonation/', views.admin_stop_impersonation, name='admin_stop_impersonation'),

    # Medications
    path('medications/', views.medications_view, name='medications'),
    path('medications/add/', views.medication_add_view, name='medication_add'),
    path('medications/<int:med_id>/edit/', views.medication_edit_view, name='medication_edit'),
    path('medications/<int:med_id>/toggle/', views.medication_toggle_view, name='medication_toggle'),
    path('medications/<int:med_id>/delete/', views.medication_delete_view, name='medication_delete'),
    path('exam/<int:exam_id>/medications/', views.exam_medications_view, name='exam_medications'),

    # Health
    path('health/', views.health_view, name='health'),
]
