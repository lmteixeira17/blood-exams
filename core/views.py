"""
Views for the blood exams management system.
"""

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .ai_service import process_exam
from .forms import ExamUploadForm, ProfileForm, RegistrationForm
from .models import AIAnalysis, Biomarker, Exam, ExamResult


def register_view(request):
    """User registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Conta criada com sucesso! Bem-vindo.')
            return redirect('dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'core/register.html', {'form': form})


@login_required
def dashboard_view(request):
    """Main dashboard with summary stats and charts."""
    user_exams = Exam.objects.filter(user=request.user, status='completed')
    total_exams = user_exams.count()
    last_exam = user_exams.first()

    # Get key biomarker trends for charts
    chart_data = {}
    if total_exams > 0:
        # Get most common biomarkers for this user
        top_biomarkers = (
            ExamResult.objects
            .filter(exam__user=request.user, exam__status='completed')
            .values('biomarker__id', 'biomarker__name', 'biomarker__code', 'biomarker__unit')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )

        for bm in top_biomarkers:
            results = (
                ExamResult.objects
                .filter(
                    exam__user=request.user,
                    exam__status='completed',
                    biomarker_id=bm['biomarker__id'],
                )
                .select_related('exam')
                .order_by('exam__exam_date')
            )
            if results.count() >= 1:
                chart_data[bm['biomarker__code']] = {
                    'name': bm['biomarker__name'],
                    'unit': bm['biomarker__unit'],
                    'dates': [r.exam.exam_date.isoformat() for r in results],
                    'values': [float(r.value) for r in results],
                    'ref_min': [float(r.ref_min) if r.ref_min else None for r in results],
                    'ref_max': [float(r.ref_max) if r.ref_max else None for r in results],
                }

    # Recent exams
    recent_exams = user_exams[:5]

    # Abnormal count from last exam
    abnormal_count = 0
    if last_exam:
        abnormal_count = last_exam.results.filter(is_abnormal=True).count()

    context = {
        'total_exams': total_exams,
        'last_exam': last_exam,
        'abnormal_count': abnormal_count,
        'chart_data_json': json.dumps(chart_data),
        'recent_exams': recent_exams,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def upload_view(request):
    """Upload a new blood exam."""
    if request.method == 'POST':
        form = ExamUploadForm(request.POST, request.FILES)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.user = request.user

            # Detect file type
            ext = exam.file.name.lower().split('.')[-1]
            exam.file_type = 'pdf' if ext == 'pdf' else 'image'
            exam.save()

            # Process exam (synchronous)
            success = process_exam(exam)

            if success:
                messages.success(request, 'Exame processado com sucesso!')
                return redirect('exam_detail', exam_id=exam.id)
            else:
                messages.warning(
                    request,
                    'O exame foi enviado mas houve um erro no processamento. '
                    'Verifique os detalhes abaixo.'
                )
                return redirect('exam_detail', exam_id=exam.id)
    else:
        form = ExamUploadForm()

    return render(request, 'core/upload.html', {'form': form})


@login_required
def exam_detail_view(request, exam_id):
    """View details of a single exam."""
    exam = get_object_or_404(Exam, id=exam_id, user=request.user)
    results = exam.results.select_related('biomarker').order_by('biomarker__category', 'biomarker__name')
    analysis = getattr(exam, 'analysis', None)

    # Group results by category
    grouped_results = {}
    for r in results:
        cat = r.biomarker.category
        if cat not in grouped_results:
            grouped_results[cat] = []
        grouped_results[cat].append(r)

    # Get historical values for comparison
    history_comparison = {}
    previous_exam = (
        Exam.objects
        .filter(user=request.user, status='completed', exam_date__lt=exam.exam_date)
        .first()
    )
    if previous_exam:
        prev_results = {
            r.biomarker_id: r for r in previous_exam.results.select_related('biomarker')
        }
        for r in results:
            if r.biomarker_id in prev_results:
                prev = prev_results[r.biomarker_id]
                diff = float(r.value - prev.value)
                pct = (diff / float(prev.value) * 100) if float(prev.value) != 0 else 0
                history_comparison[r.biomarker_id] = {
                    'previous_value': prev.value,
                    'diff': diff,
                    'pct': round(pct, 1),
                }

    context = {
        'exam': exam,
        'grouped_results': grouped_results,
        'analysis': analysis,
        'history_comparison': history_comparison,
        'previous_exam': previous_exam,
    }
    return render(request, 'core/exam_detail.html', context)


@login_required
def exam_history_view(request):
    """View all exams with timeline."""
    exams = Exam.objects.filter(user=request.user).order_by('-exam_date')

    # Get biomarker comparison across exams
    comparison_data = {}
    completed_exams = exams.filter(status='completed')[:10]

    if completed_exams.count() >= 2:
        # Find biomarkers present in all exams
        all_biomarker_ids = set()
        for exam in completed_exams:
            ids = set(exam.results.values_list('biomarker_id', flat=True))
            if not all_biomarker_ids:
                all_biomarker_ids = ids
            else:
                all_biomarker_ids &= ids

        biomarkers = Biomarker.objects.filter(id__in=all_biomarker_ids).order_by('category', 'name')
        for bm in biomarkers:
            values = []
            for exam in reversed(list(completed_exams)):
                result = exam.results.filter(biomarker=bm).first()
                if result:
                    values.append({
                        'date': exam.exam_date.isoformat(),
                        'value': float(result.value),
                        'is_abnormal': result.is_abnormal,
                    })
            if values:
                comparison_data[bm.id] = {
                    'name': bm.name,
                    'unit': bm.unit,
                    'category': bm.category,
                    'values': values,
                }

    context = {
        'exams': exams,
        'comparison_data': comparison_data,
    }
    return render(request, 'core/exam_history.html', context)


@login_required
def biomarker_chart_view(request, code):
    """Detailed chart for a single biomarker over time."""
    biomarker = get_object_or_404(Biomarker, code=code)

    results = (
        ExamResult.objects
        .filter(exam__user=request.user, exam__status='completed', biomarker=biomarker)
        .select_related('exam')
        .order_by('exam__exam_date')
    )

    chart_data = {
        'name': biomarker.name,
        'code': biomarker.code,
        'unit': biomarker.unit,
        'category': biomarker.category,
        'description': biomarker.description,
        'dates': [r.exam.exam_date.isoformat() for r in results],
        'values': [float(r.value) for r in results],
        'ref_min': [float(r.ref_min) if r.ref_min else None for r in results],
        'ref_max': [float(r.ref_max) if r.ref_max else None for r in results],
    }

    # Get reference ranges for this user
    gender = ''
    if hasattr(request.user, 'profile'):
        gender = request.user.profile.gender
    ref_range = biomarker.get_ref_range(gender)

    context = {
        'biomarker': biomarker,
        'chart_data_json': json.dumps(chart_data),
        'ref_min': ref_range[0],
        'ref_max': ref_range[1],
        'results': results,
    }
    return render(request, 'core/biomarker_chart.html', context)


@login_required
def profile_view(request):
    """Edit user profile."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)

    return render(request, 'core/profile.html', {'form': form})


@login_required
def exam_delete_view(request, exam_id):
    """Delete an exam."""
    exam = get_object_or_404(Exam, id=exam_id, user=request.user)
    if request.method == 'POST':
        exam.file.delete()
        exam.delete()
        messages.success(request, 'Exame excluído com sucesso.')
        return redirect('exam_history')
    return redirect('exam_detail', exam_id=exam_id)


@login_required
def exam_reprocess_view(request, exam_id):
    """Reprocess an exam with AI."""
    exam = get_object_or_404(Exam, id=exam_id, user=request.user)
    if request.method == 'POST':
        # Clear old results
        exam.results.all().delete()
        if hasattr(exam, 'analysis'):
            exam.analysis.delete()
        exam.status = 'pending'
        exam.error_message = ''
        exam.save()

        success = process_exam(exam)
        if success:
            messages.success(request, 'Exame reprocessado com sucesso!')
        else:
            messages.error(request, 'Erro ao reprocessar o exame.')

    return redirect('exam_detail', exam_id=exam_id)


# ---- API endpoints for charts ----

@login_required
def api_biomarker_data(request, code):
    """API endpoint returning biomarker history as JSON (for Chart.js)."""
    biomarker = get_object_or_404(Biomarker, code=code)
    results = (
        ExamResult.objects
        .filter(exam__user=request.user, exam__status='completed', biomarker=biomarker)
        .select_related('exam')
        .order_by('exam__exam_date')
    )
    data = {
        'name': biomarker.name,
        'unit': biomarker.unit,
        'dates': [r.exam.exam_date.isoformat() for r in results],
        'values': [float(r.value) for r in results],
        'ref_min': [float(r.ref_min) if r.ref_min else None for r in results],
        'ref_max': [float(r.ref_max) if r.ref_max else None for r in results],
    }
    return JsonResponse(data)


# ---- Admin panel ----

@user_passes_test(lambda u: u.is_superuser)
def admin_users_view(request):
    """User management for superusers."""
    users = (
        User.objects
        .annotate(exam_count=Count('exams'))
        .order_by('-date_joined')
    )

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        target_user = get_object_or_404(User, id=user_id)

        if action == 'toggle_active':
            target_user.is_active = not target_user.is_active
            target_user.save()
            status = 'ativado' if target_user.is_active else 'desativado'
            messages.success(request, f'Usuário {target_user.username} {status}.')
        elif action == 'toggle_subscriber':
            target_user.profile.is_active_subscriber = not target_user.profile.is_active_subscriber
            target_user.profile.save()
            status = 'ativada' if target_user.profile.is_active_subscriber else 'desativada'
            messages.success(request, f'Assinatura de {target_user.username} {status}.')

        return redirect('admin_users')

    context = {'users': users}
    return render(request, 'core/admin_users.html', context)


def health_view(request):
    """Health check endpoint."""
    return JsonResponse({'status': 'ok'})
