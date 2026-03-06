"""
Views for the blood exams management system.
"""

import json
import logging
import threading

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import close_old_connections
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .ai_service import generate_trend_analysis, process_exam
from .forms import AdminUserForm, CompleteProfileForm, ExamUploadForm, ProfileForm, RegistrationForm, UserMedicationForm
from .models import AIAnalysis, Biomarker, Exam, ExamMedication, ExamResult, Medication, UserMedication

logger = logging.getLogger(__name__)


def _process_exam_in_thread(exam_id):
    """Run exam processing in a background thread."""
    try:
        close_old_connections()
        exam = Exam.objects.get(id=exam_id)
        process_exam(exam)
    except Exception:
        logger.exception("Background processing failed for exam %s", exam_id)
        try:
            exam = Exam.objects.get(id=exam_id)
            if exam.status != "error":
                exam.status = "error"
                exam.error_message = "Erro inesperado no processamento em background."
                exam.save(update_fields=["status", "error_message"])
        except Exception:
            pass
    finally:
        close_old_connections()


def get_effective_user(request):
    """Return impersonated user if admin is viewing-as, else request.user."""
    if request.user.is_superuser:
        uid = request.session.get('_impersonate_user_id')
        if uid:
            try:
                return User.objects.get(id=uid)
            except User.DoesNotExist:
                del request.session['_impersonate_user_id']
    return request.user


def register_view(request):
    """User registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Conta criada com sucesso! Bem-vindo.')
            return redirect('dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'core/register.html', {'form': form})


@login_required
def complete_profile_view(request):
    """Collect required profile data (DOB and gender) on first login."""
    profile = request.user.profile
    if profile.date_of_birth and profile.gender:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CompleteProfileForm(request.POST)
        if form.is_valid():
            profile.date_of_birth = form.cleaned_data['date_of_birth']
            profile.gender = form.cleaned_data['gender']
            profile.save()
            return redirect('dashboard')
    else:
        form = CompleteProfileForm()

    return render(request, 'core/complete_profile.html', {'form': form})


@login_required
def dashboard_view(request):
    """Main dashboard with summary stats and charts."""
    effective_user = get_effective_user(request)
    user_exams = Exam.objects.filter(user=effective_user, status='completed')
    total_exams = user_exams.count()
    last_exam = user_exams.first()

    chart_data = {}
    category_health = {}
    critical_biomarkers = []
    normal_count = 0
    total_results = 0
    abnormal_count = 0
    analysis_data = None

    if total_exams > 0 and last_exam:
        # All results from the last exam
        last_results = last_exam.results.select_related('biomarker')
        total_results = last_results.count()
        abnormal_count = last_results.filter(is_abnormal=True).count()
        normal_count = total_results - abnormal_count

        # Category health for radar chart: % normal per category
        cat_stats = {}
        for r in last_results:
            cat = r.biomarker.category
            if cat not in cat_stats:
                cat_stats[cat] = {'total': 0, 'normal': 0}
            cat_stats[cat]['total'] += 1
            if not r.is_abnormal:
                cat_stats[cat]['normal'] += 1
        for cat, stats in cat_stats.items():
            if stats['total'] > 0:
                category_health[cat] = {
                    'pct_normal': round(stats['normal'] / stats['total'] * 100)
                }

        # Critical biomarkers for gauge and deviation bar charts
        for r in last_results.filter(is_abnormal=True):
            if r.ref_min is not None and r.ref_max is not None:
                val = float(r.value)
                rmin = float(r.ref_min)
                rmax = float(r.ref_max)
                if val > rmax and rmax > 0:
                    deviation = round((val - rmax) / rmax * 100, 1)
                    status = 'high'
                elif val < rmin and rmin > 0:
                    deviation = round((rmin - val) / rmin * 100, 1)
                    status = 'low'
                else:
                    continue
                critical_biomarkers.append({
                    'name': r.biomarker.name,
                    'code': r.biomarker.code,
                    'unit': r.biomarker.unit,
                    'value': val,
                    'ref_min': rmin,
                    'ref_max': rmax,
                    'deviation': deviation,
                    'status': status,
                })
        critical_biomarkers.sort(key=lambda x: x['deviation'], reverse=True)

        # AI analysis from last exam (enrich with biomarker codes for links)
        try:
            analysis = last_exam.analysis
            name_to_code = {
                r.biomarker.name.lower(): r.biomarker.code for r in last_results
            }

            def _enrich_with_codes(items):
                enriched = []
                for item in (items or []):
                    copy = dict(item)
                    if not copy.get('code'):
                        bm_name = copy.get('biomarker', '').lower()
                        copy['code'] = name_to_code.get(bm_name, '')
                    enriched.append(copy)
                return enriched

            analysis_data = {
                'summary': analysis.summary,
                'alerts': _enrich_with_codes(analysis.alerts),
                'improvements': _enrich_with_codes(analysis.improvements),
                'deteriorations': _enrich_with_codes(analysis.deteriorations),
                'recommendations': analysis.recommendations,
            }
        except AIAnalysis.DoesNotExist:
            pass

        # Evolution charts - top biomarkers across all exams
        top_biomarkers = (
            ExamResult.objects
            .filter(exam__user=effective_user, exam__status='completed')
            .values('biomarker__id', 'biomarker__name', 'biomarker__code',
                    'biomarker__unit', 'biomarker__category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        for bm in top_biomarkers:
            results = (
                ExamResult.objects
                .filter(
                    exam__user=effective_user,
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
                    'category': bm['biomarker__category'],
                    'dates': [r.exam.exam_date.isoformat() for r in results],
                    'values': [float(r.value) for r in results],
                    'ref_min': [float(r.ref_min) if r.ref_min else None for r in results],
                    'ref_max': [float(r.ref_max) if r.ref_max else None for r in results],
                }

    # Biomarker Correlation Analysis
    correlation_data = None
    if total_exams > 0 and last_exam:
        from .correlations import analyze_correlations
        gender = ''
        if hasattr(effective_user, 'profile'):
            gender = effective_user.profile.gender
        correlation_data = analyze_correlations(last_results, gender)

    # Recent exams
    recent_exams = user_exams[:5]

    context = {
        'total_exams': total_exams,
        'last_exam': last_exam,
        'abnormal_count': abnormal_count,
        'normal_count': normal_count,
        'total_results': total_results,
        'chart_data_json': json.dumps(chart_data),
        'category_health_json': json.dumps(category_health),
        'critical_biomarkers_json': json.dumps(critical_biomarkers),
        'analysis_data': analysis_data,
        'analysis_data_json': json.dumps(analysis_data),
        'correlation_data': correlation_data,
        'recent_exams': recent_exams,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def upload_view(request):
    """Upload a new blood exam."""
    effective_user = get_effective_user(request)
    if request.method == 'POST':
        form = ExamUploadForm(request.POST, request.FILES)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.user = effective_user

            # Detect file type
            ext = exam.file.name.lower().split('.')[-1]
            exam.file_type = 'pdf' if ext == 'pdf' else 'image'
            exam.save()

            # Auto-link active medications to this exam
            active_meds = UserMedication.objects.filter(
                user=effective_user, is_active=True
            ).select_related('medication')
            for um in active_meds:
                ExamMedication.objects.create(
                    exam=exam,
                    medication=um.medication,
                    dose=um.dose,
                    frequency=um.frequency,
                )

            # Process exam in background thread
            thread = threading.Thread(
                target=_process_exam_in_thread,
                args=(exam.id,),
                daemon=True,
            )
            thread.start()

            return redirect('exam_processing', exam_id=exam.id)
    else:
        form = ExamUploadForm()

    return render(request, 'core/upload.html', {'form': form})


@login_required
def exam_processing_view(request, exam_id):
    """Show processing status page with auto-polling."""
    effective_user = get_effective_user(request)
    exam = get_object_or_404(Exam, id=exam_id, user=effective_user)
    if exam.status in ('completed', 'error'):
        return redirect('exam_detail', exam_id=exam.id)
    return render(request, 'core/exam_processing.html', {'exam': exam})


@login_required
def exam_status_api(request, exam_id):
    """JSON endpoint for polling exam processing status."""
    effective_user = get_effective_user(request)
    exam = get_object_or_404(Exam, id=exam_id, user=effective_user)
    return JsonResponse({
        'status': exam.status,
        'result_count': exam.results.count(),
    })


@login_required
def exam_detail_view(request, exam_id):
    """View details of a single exam."""
    effective_user = get_effective_user(request)
    exam = get_object_or_404(Exam, id=exam_id, user=effective_user)
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
        .filter(user=effective_user, status='completed', exam_date__lt=exam.exam_date)
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

    # Medications linked to this exam
    exam_medications = ExamMedication.objects.filter(
        exam=exam
    ).select_related('medication').order_by('medication__name')

    context = {
        'exam': exam,
        'grouped_results': grouped_results,
        'analysis': analysis,
        'history_comparison': history_comparison,
        'previous_exam': previous_exam,
        'exam_medications': exam_medications,
    }
    return render(request, 'core/exam_detail.html', context)


@login_required
def exam_history_view(request):
    """View all exams with timeline."""
    effective_user = get_effective_user(request)
    exams = Exam.objects.filter(user=effective_user).order_by('-exam_date')

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
    effective_user = get_effective_user(request)
    biomarker = get_object_or_404(Biomarker, code=code)

    results = (
        ExamResult.objects
        .filter(exam__user=effective_user, exam__status='completed', biomarker=biomarker)
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
    if hasattr(effective_user, 'profile'):
        gender = effective_user.profile.gender
    ref_range = biomarker.get_ref_range(gender)

    # Trend analysis is loaded asynchronously via AJAX to avoid blocking page render
    has_enough_for_trend = results.count() >= 2

    context = {
        'biomarker': biomarker,
        'chart_data_json': json.dumps(chart_data),
        'ref_min': ref_range[0],
        'ref_max': ref_range[1],
        'results': results,
        'has_enough_for_trend': has_enough_for_trend,
    }
    return render(request, 'core/biomarker_chart.html', context)


@login_required
def biomarker_trend_api(request, code):
    """AJAX endpoint: generate/return trend analysis for a biomarker."""
    effective_user = get_effective_user(request)
    biomarker = get_object_or_404(Biomarker, code=code)

    results = (
        ExamResult.objects
        .filter(exam__user=effective_user, exam__status='completed', biomarker=biomarker)
        .select_related('exam')
        .order_by('exam__exam_date')
    )

    if results.count() < 2:
        return JsonResponse({'status': 'insufficient_data'})

    gender = ''
    if hasattr(effective_user, 'profile'):
        gender = effective_user.profile.gender
    ref_range = biomarker.get_ref_range(gender)

    analysis = generate_trend_analysis(
        biomarker, results, ref_range[0], ref_range[1], effective_user
    )

    if analysis:
        return JsonResponse({'status': 'ok', 'analysis': analysis})
    return JsonResponse({'status': 'error'})


@login_required
def profile_view(request):
    """Edit user profile."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            password_changed = bool(form.cleaned_data.get('new_password'))
            form.save()
            if password_changed:
                # Keep user logged in after password change
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Perfil e senha atualizados com sucesso!')
            else:
                messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)

    return render(request, 'core/profile.html', {'form': form})


@login_required
def exam_delete_view(request, exam_id):
    """Delete an exam."""
    effective_user = get_effective_user(request)
    exam = get_object_or_404(Exam, id=exam_id, user=effective_user)
    if request.method == 'POST':
        exam.file.delete()
        exam.delete()
        messages.success(request, 'Exame excluído com sucesso.')
        return redirect('exam_history')
    return redirect('exam_detail', exam_id=exam_id)


@login_required
def exam_reprocess_view(request, exam_id):
    """Reprocess an exam with AI (background)."""
    effective_user = get_effective_user(request)
    exam = get_object_or_404(Exam, id=exam_id, user=effective_user)
    if request.method == 'POST':
        # Clear old results
        exam.results.all().delete()
        if hasattr(exam, 'analysis'):
            exam.analysis.delete()
        exam.status = 'pending'
        exam.error_message = ''
        exam.save()

        thread = threading.Thread(
            target=_process_exam_in_thread,
            args=(exam.id,),
            daemon=True,
        )
        thread.start()

        return redirect('exam_processing', exam_id=exam.id)

    return redirect('exam_detail', exam_id=exam_id)


# ---- API endpoints for charts ----

@login_required
def api_biomarker_data(request, code):
    """API endpoint returning biomarker history as JSON (for Chart.js)."""
    effective_user = get_effective_user(request)
    biomarker = get_object_or_404(Biomarker, code=code)
    results = (
        ExamResult.objects
        .filter(exam__user=effective_user, exam__status='completed', biomarker=biomarker)
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

def _is_superuser(u):
    return u.is_superuser


@user_passes_test(_is_superuser)
def admin_users_view(request):
    """User management list for superusers."""
    users = (
        User.objects
        .select_related('profile')
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


@user_passes_test(_is_superuser)
def admin_user_create_view(request):
    """Create a new user (admin panel)."""
    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuário {user.username} criado com sucesso.')
            return redirect('admin_users')
    else:
        form = AdminUserForm()

    return render(request, 'core/admin_user_form.html', {
        'form': form,
        'page_title': 'Novo Usu\u00e1rio',
    })


@user_passes_test(_is_superuser)
def admin_user_edit_view(request, user_id):
    """Edit an existing user (admin panel)."""
    target_user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = AdminUserForm(request.POST, editing_user=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuário {target_user.username} atualizado.')
            return redirect('admin_users')
    else:
        form = AdminUserForm(editing_user=target_user)

    return render(request, 'core/admin_user_form.html', {
        'form': form,
        'editing_user': target_user,
        'page_title': f'Editar: {target_user.username}',
    })


@user_passes_test(_is_superuser)
def admin_user_delete_view(request, user_id):
    """Delete a user (admin panel). POST only."""
    target_user = get_object_or_404(User, id=user_id)

    if target_user.is_superuser:
        messages.error(request, 'Não é possível excluir um administrador.')
        return redirect('admin_users')

    if request.method == 'POST':
        username = target_user.username
        target_user.delete()
        messages.success(request, f'Usuário {username} excluído.')

    return redirect('admin_users')


@user_passes_test(_is_superuser)
def admin_view_as_user(request, user_id):
    """Start impersonating a user (admin only)."""
    target = get_object_or_404(User, id=user_id)
    request.session['_impersonate_user_id'] = target.id
    name = target.get_full_name() or target.username
    messages.info(request, f'Visualizando como {name}.')
    return redirect('dashboard')


@user_passes_test(_is_superuser)
def admin_stop_impersonation(request):
    """Stop impersonating and return to admin panel."""
    request.session.pop('_impersonate_user_id', None)
    return redirect('admin_users')


# ---- Medication management ----

@login_required
def medications_view(request):
    """List user medications with active/inactive tabs."""
    effective_user = get_effective_user(request)
    active_meds = UserMedication.objects.filter(
        user=effective_user, is_active=True
    ).select_related('medication')
    inactive_meds = UserMedication.objects.filter(
        user=effective_user, is_active=False
    ).select_related('medication')

    context = {
        'active_meds': active_meds,
        'inactive_meds': inactive_meds,
    }
    return render(request, 'core/medications.html', context)


@login_required
def medication_add_view(request):
    """Add a new medication."""
    effective_user = get_effective_user(request)
    if request.method == 'POST':
        form = UserMedicationForm(request.POST)
        if form.is_valid():
            med = form.save(commit=False)
            med.user = effective_user
            med.save()
            messages.success(request, f'{med.medication.name} adicionado com sucesso.')
            return redirect('medications')
    else:
        form = UserMedicationForm()

    return render(request, 'core/medication_form.html', {
        'form': form,
        'page_title': 'Adicionar Medicamento',
    })


@login_required
def medication_edit_view(request, med_id):
    """Edit an existing medication."""
    effective_user = get_effective_user(request)
    user_med = get_object_or_404(UserMedication, id=med_id, user=effective_user)

    if request.method == 'POST':
        form = UserMedicationForm(request.POST, instance=user_med)
        if form.is_valid():
            form.save()
            messages.success(request, f'{user_med.medication.name} atualizado.')
            return redirect('medications')
    else:
        form = UserMedicationForm(instance=user_med)

    return render(request, 'core/medication_form.html', {
        'form': form,
        'page_title': f'Editar: {user_med.medication.name}',
        'editing': True,
    })


@login_required
def medication_toggle_view(request, med_id):
    """Toggle medication active/inactive status."""
    effective_user = get_effective_user(request)
    user_med = get_object_or_404(UserMedication, id=med_id, user=effective_user)

    if request.method == 'POST':
        user_med.is_active = not user_med.is_active
        if not user_med.is_active and not user_med.end_date:
            from datetime import date
            user_med.end_date = date.today()
        user_med.save()
        status = 'reativado' if user_med.is_active else 'desativado'
        messages.success(request, f'{user_med.medication.name} {status}.')

    return redirect('medications')


@login_required
def medication_delete_view(request, med_id):
    """Delete a medication."""
    effective_user = get_effective_user(request)
    user_med = get_object_or_404(UserMedication, id=med_id, user=effective_user)

    if request.method == 'POST':
        name = user_med.medication.name
        user_med.delete()
        messages.success(request, f'{name} removido.')

    return redirect('medications')


@login_required
def exam_medications_view(request, exam_id):
    """Manage medications linked to a specific exam."""
    effective_user = get_effective_user(request)
    exam = get_object_or_404(Exam, id=exam_id, user=effective_user)

    if request.method == 'POST':
        # Clear existing exam medications and re-create from form
        ExamMedication.objects.filter(exam=exam).delete()
        selected_ids = request.POST.getlist('medications')
        for um_id in selected_ids:
            try:
                user_med = UserMedication.objects.select_related('medication').get(
                    id=um_id, user=effective_user
                )
                ExamMedication.objects.create(
                    exam=exam,
                    medication=user_med.medication,
                    dose=user_med.dose,
                    frequency=user_med.frequency,
                )
            except UserMedication.DoesNotExist:
                continue
        messages.success(request, 'Medicamentos do exame atualizados.')
        return redirect('exam_detail', exam_id=exam.id)

    # Get all user medications that were active around the exam date
    all_user_meds = UserMedication.objects.filter(
        user=effective_user
    ).select_related('medication').order_by('medication__name')

    # Pre-select: medications already linked to this exam
    linked_med_ids = set(
        ExamMedication.objects.filter(exam=exam).values_list('medication_id', flat=True)
    )

    # Build list with pre-selection info
    med_list = []
    for um in all_user_meds:
        was_active = um.is_active or (
            um.start_date <= exam.exam_date and
            (um.end_date is None or um.end_date >= exam.exam_date)
        )
        med_list.append({
            'user_med': um,
            'checked': um.medication_id in linked_med_ids,
            'was_active': was_active,
        })

    context = {
        'exam': exam,
        'med_list': med_list,
        'has_linked': bool(linked_med_ids),
    }
    return render(request, 'core/exam_medications.html', context)


def health_view(request):
    """Health check endpoint."""
    return JsonResponse({'status': 'ok'})
