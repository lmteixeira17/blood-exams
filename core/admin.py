"""
Django admin configuration for blood exams.
"""

from django.contrib import admin

from .models import (
    AIAnalysis, Biomarker, BiomarkerTrendAnalysis, Exam,
    ExamResult, ExamValidation, UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'gender', 'date_of_birth', 'is_active_subscriber', 'created_at']
    list_filter = ['gender', 'is_active_subscriber']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']


@admin.register(Biomarker)
class BiomarkerAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'unit', 'category', 'ref_min_male', 'ref_max_male']
    list_filter = ['category']
    search_fields = ['name', 'code', 'aliases']
    ordering = ['category', 'name']


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['user', 'exam_date', 'lab_name', 'file_type', 'status', 'uploaded_at']
    list_filter = ['status', 'file_type']
    search_fields = ['user__username', 'lab_name']
    date_hierarchy = 'exam_date'


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ['exam', 'biomarker', 'value', 'is_abnormal']
    list_filter = ['is_abnormal', 'biomarker__category']
    search_fields = ['biomarker__name', 'exam__user__username']


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ['exam', 'model_used', 'input_tokens', 'output_tokens', 'created_at']
    readonly_fields = ['input_tokens', 'output_tokens']


@admin.register(ExamValidation)
class ExamValidationAdmin(admin.ModelAdmin):
    list_display = ['exam', 'biomarker_code', 'severity', 'category', 'message', 'resolved']
    list_filter = ['severity', 'category', 'resolved']
    search_fields = ['biomarker_code', 'message']
    list_editable = ['resolved']


@admin.register(BiomarkerTrendAnalysis)
class BiomarkerTrendAnalysisAdmin(admin.ModelAdmin):
    list_display = ['user', 'biomarker', 'result_count', 'model_used', 'created_at']
    list_filter = ['model_used']
    search_fields = ['biomarker__name', 'user__username']
    readonly_fields = ['input_tokens', 'output_tokens']
