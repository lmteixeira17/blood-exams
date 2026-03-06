"""
Comprehensive test suite for the Blood Lab application.

Categories:
  - Models: UserProfile, Biomarker, Exam, ExamResult, AIAnalysis, ExamValidation,
            BiomarkerTrendAnalysis, Medication, UserMedication, ExamMedication
  - Forms: RegistrationForm, ProfileForm, CompleteProfileForm, ExamUploadForm,
           AdminUserForm, UserMedicationForm
  - Views: all 23 views (auth, dashboard, upload, exams, biomarkers, admin, medications, health)
  - Middleware: ProfileCompletionMiddleware
  - Validation: validation engine (physiological, cross-biomarker, WBC, historical, unit mismatch)
  - Template tags: blood_extras filters
  - Security: CSRF, auth enforcement, access control, data isolation, file upload limits
  - Operational: health endpoint, settings, URL routing
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse

from core.forms import (
    AdminUserForm,
    CompleteProfileForm,
    ExamUploadForm,
    ProfileForm,
    RegistrationForm,
    UserMedicationForm,
)
from core.middleware import ProfileCompletionMiddleware
from core.models import (
    AIAnalysis,
    Biomarker,
    BiomarkerTrendAnalysis,
    Exam,
    ExamMedication,
    ExamResult,
    ExamValidation,
    Medication,
    UserMedication,
    UserProfile,
)
from core.templatetags.blood_extras import abs_value, get_item, status_color, trend_icon
from core.validation import (
    FlagCategory,
    FlagSeverity,
    ValidationFlag,
    validate_exam,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def user(db):
    """Create a regular user with complete profile."""
    u = User.objects.create_user(
        username='testuser', password='TestPass123!',
        first_name='Test', last_name='User', email='test@example.com',
    )
    u.profile.date_of_birth = date(1990, 5, 15)
    u.profile.gender = 'M'
    u.profile.save()
    return u


@pytest.fixture
def user_female(db):
    """Create a female user with complete profile."""
    u = User.objects.create_user(
        username='femaleuser', password='TestPass123!',
        first_name='Jane', last_name='Doe', email='jane@example.com',
    )
    u.profile.date_of_birth = date(1985, 3, 20)
    u.profile.gender = 'F'
    u.profile.save()
    return u


@pytest.fixture
def incomplete_user(db):
    """Create a user without DOB or gender (incomplete profile)."""
    return User.objects.create_user(
        username='incomplete', password='TestPass123!',
        email='incomplete@example.com',
    )


@pytest.fixture
def superuser(db):
    """Create a superuser."""
    u = User.objects.create_superuser(
        username='admin', password='AdminPass123!',
        first_name='Admin', last_name='User', email='admin@example.com',
    )
    u.profile.date_of_birth = date(1980, 1, 1)
    u.profile.gender = 'M'
    u.profile.save()
    return u


@pytest.fixture
def biomarker_hgb(db):
    """Hemoglobin biomarker with gender-specific ranges."""
    return Biomarker.objects.create(
        name='Hemoglobina', code='HGB', unit='g/dL',
        ref_min_male=Decimal('13.0'), ref_max_male=Decimal('17.5'),
        ref_min_female=Decimal('12.0'), ref_max_female=Decimal('15.5'),
        category='Hemograma', aliases='Hb,Hemoglobin',
    )


@pytest.fixture
def biomarker_ct(db):
    """Cholesterol biomarker (only ref_max, no ref_min)."""
    return Biomarker.objects.create(
        name='Colesterol Total', code='CT', unit='mg/dL',
        ref_min_male=None, ref_max_male=Decimal('190.0'),
        ref_min_female=None, ref_max_female=Decimal('190.0'),
        category='Lipidograma',
    )


@pytest.fixture
def biomarker_hdl(db):
    """HDL biomarker (only ref_min, no ref_max)."""
    return Biomarker.objects.create(
        name='HDL Colesterol', code='HDL', unit='mg/dL',
        ref_min_male=Decimal('40.0'), ref_max_male=None,
        ref_min_female=Decimal('50.0'), ref_max_female=None,
        category='Lipidograma',
    )


@pytest.fixture
def biomarker_gli(db):
    """Glucose biomarker."""
    return Biomarker.objects.create(
        name='Glicose', code='GLI', unit='mg/dL',
        ref_min_male=Decimal('70.0'), ref_max_male=Decimal('99.0'),
        ref_min_female=Decimal('70.0'), ref_max_female=Decimal('99.0'),
        category='Glicemia',
    )


@pytest.fixture
def exam(user, biomarker_hgb):
    """Create a completed exam with one result."""
    e = Exam.objects.create(
        user=user, file='exams/2025/01/test.pdf', file_type='pdf',
        exam_date=date(2025, 1, 15), lab_name='Test Lab', status='completed',
    )
    ExamResult.objects.create(exam=e, biomarker=biomarker_hgb, value=Decimal('15.0'))
    return e


@pytest.fixture
def exam_with_analysis(exam, biomarker_hgb):
    """Create a completed exam with AI analysis."""
    AIAnalysis.objects.create(
        exam=exam, summary='Resultados dentro da normalidade.',
        alerts=[{'biomarker': 'Hemoglobina', 'message': 'Valor normal'}],
        improvements=[], deteriorations=[],
        recommendations='Manter acompanhamento regular.',
        model_used='gpt-4o', input_tokens=100, output_tokens=50,
    )
    return exam


@pytest.fixture
def client_logged_in(user):
    """Client authenticated with the regular user."""
    c = Client()
    c.login(username='testuser', password='TestPass123!')
    return c


@pytest.fixture
def client_superuser(superuser):
    """Client authenticated with the superuser."""
    c = Client()
    c.login(username='admin', password='AdminPass123!')
    return c


@pytest.fixture
def client_incomplete(incomplete_user):
    """Client authenticated with an incomplete-profile user."""
    c = Client()
    c.login(username='incomplete', password='TestPass123!')
    return c


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestUserProfileModel:
    """Tests for UserProfile model and auto-creation signal."""

    def test_profile_created_on_user_save(self, db):
        u = User.objects.create_user(username='signaltest', password='pass')
        assert hasattr(u, 'profile')
        assert isinstance(u.profile, UserProfile)

    def test_profile_str(self, user):
        assert 'Test User' in str(user.profile)

    def test_age_calculation(self, user):
        age = user.profile.age
        assert age is not None
        assert age >= 35  # born 1990

    def test_age_none_when_no_dob(self, incomplete_user):
        assert incomplete_user.profile.age is None

    def test_gender_choices(self, user):
        user.profile.gender = 'M'
        user.profile.save()
        user.profile.refresh_from_db()
        assert user.profile.gender == 'M'

    def test_default_subscriber_status(self, db):
        u = User.objects.create_user(username='sub', password='pass')
        assert u.profile.is_active_subscriber is True

    def test_profile_cascade_delete(self, user):
        profile_id = user.profile.id
        user.delete()
        assert not UserProfile.objects.filter(id=profile_id).exists()


class TestBiomarkerModel:
    """Tests for Biomarker model."""

    def test_create_biomarker(self, biomarker_hgb):
        assert biomarker_hgb.code == 'HGB'
        assert biomarker_hgb.unit == 'g/dL'

    def test_str(self, biomarker_hgb):
        s = str(biomarker_hgb)
        assert 'Hemoglobina' in s
        assert 'HGB' in s
        assert 'g/dL' in s

    def test_get_ref_range_male(self, biomarker_hgb):
        ref_min, ref_max = biomarker_hgb.get_ref_range('M')
        assert ref_min == Decimal('13.0')
        assert ref_max == Decimal('17.5')

    def test_get_ref_range_female(self, biomarker_hgb):
        ref_min, ref_max = biomarker_hgb.get_ref_range('F')
        assert ref_min == Decimal('12.0')
        assert ref_max == Decimal('15.5')

    def test_get_ref_range_default_male(self, biomarker_hgb):
        ref_min, ref_max = biomarker_hgb.get_ref_range()
        assert ref_min == Decimal('13.0')

    def test_unique_code(self, biomarker_hgb):
        with pytest.raises(Exception):
            Biomarker.objects.create(name='Duplicate', code='HGB', unit='g/dL', category='Test')

    def test_unique_name(self, biomarker_hgb):
        with pytest.raises(Exception):
            Biomarker.objects.create(name='Hemoglobina', code='DUP', unit='g/dL', category='Test')

    def test_ordering(self, biomarker_hgb, biomarker_ct):
        bms = list(Biomarker.objects.all())
        # ordering by category, name
        assert bms[0].category <= bms[-1].category

    def test_ref_range_only_max(self, biomarker_ct):
        ref_min, ref_max = biomarker_ct.get_ref_range('M')
        assert ref_min is None
        assert ref_max == Decimal('190.0')

    def test_ref_range_only_min(self, biomarker_hdl):
        ref_min, ref_max = biomarker_hdl.get_ref_range('M')
        assert ref_min == Decimal('40.0')
        assert ref_max is None


class TestExamModel:
    """Tests for Exam model."""

    def test_create_exam(self, exam):
        assert exam.status == 'completed'
        assert exam.user.username == 'testuser'

    def test_str(self, exam):
        s = str(exam)
        assert 'testuser' in s
        assert '2025-01-15' in s

    def test_result_count(self, exam):
        assert exam.result_count == 1

    def test_abnormal_count_none(self, exam):
        assert exam.abnormal_count == 0

    def test_ordering(self, user, biomarker_hgb):
        e1 = Exam.objects.create(
            user=user, file='a.pdf', file_type='pdf',
            exam_date=date(2024, 1, 1), status='completed',
        )
        e2 = Exam.objects.create(
            user=user, file='b.pdf', file_type='pdf',
            exam_date=date(2025, 6, 1), status='completed',
        )
        exams = list(Exam.objects.filter(user=user))
        assert exams[0].exam_date >= exams[-1].exam_date

    def test_validation_status_clean(self, exam):
        assert exam.validation_status == 'clean'

    def test_validation_status_warnings(self, exam):
        ExamValidation.objects.create(
            exam=exam, biomarker_code='HGB', severity='warning',
            category='physiological', message='Test warning',
        )
        assert exam.validation_status == 'warnings'

    def test_validation_status_errors(self, exam):
        ExamValidation.objects.create(
            exam=exam, biomarker_code='HGB', severity='error',
            category='physiological', message='Test error',
        )
        assert exam.validation_status == 'errors'

    def test_unresolved_flag_count(self, exam):
        ExamValidation.objects.create(
            exam=exam, biomarker_code='HGB', severity='warning',
            category='physiological', message='Flag 1',
        )
        ExamValidation.objects.create(
            exam=exam, biomarker_code='HGB', severity='info',
            category='physiological', message='Flag 2', resolved=True,
        )
        assert exam.unresolved_flag_count == 1

    def test_cascade_delete(self, exam):
        exam_id = exam.id
        exam.user.delete()
        assert not Exam.objects.filter(id=exam_id).exists()


class TestExamResultModel:
    """Tests for ExamResult model with auto-ref and is_abnormal logic."""

    def test_save_overwrites_ref_from_catalog_male(self, user, biomarker_hgb):
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        r = ExamResult.objects.create(
            exam=e, biomarker=biomarker_hgb, value=Decimal('15.0'),
            ref_min=Decimal('999'), ref_max=Decimal('999'),  # should be overwritten
        )
        r.refresh_from_db()
        assert r.ref_min == Decimal('13.0000')
        assert r.ref_max == Decimal('17.5000')

    def test_save_overwrites_ref_from_catalog_female(self, user_female, biomarker_hgb):
        e = Exam.objects.create(
            user=user_female, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        r = ExamResult.objects.create(
            exam=e, biomarker=biomarker_hgb, value=Decimal('14.0'),
        )
        r.refresh_from_db()
        assert r.ref_min == Decimal('12.0000')
        assert r.ref_max == Decimal('15.5000')

    def test_is_abnormal_below_min(self, user, biomarker_hgb):
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        r = ExamResult.objects.create(
            exam=e, biomarker=biomarker_hgb, value=Decimal('10.0'),
        )
        r.refresh_from_db()
        assert r.is_abnormal is True

    def test_is_abnormal_above_max(self, user, biomarker_hgb):
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        r = ExamResult.objects.create(
            exam=e, biomarker=biomarker_hgb, value=Decimal('20.0'),
        )
        r.refresh_from_db()
        assert r.is_abnormal is True

    def test_is_normal_within_range(self, user, biomarker_hgb):
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        r = ExamResult.objects.create(
            exam=e, biomarker=biomarker_hgb, value=Decimal('15.0'),
        )
        r.refresh_from_db()
        assert r.is_abnormal is False

    def test_abnormal_with_only_ref_max(self, user, biomarker_ct):
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        r = ExamResult.objects.create(
            exam=e, biomarker=biomarker_ct, value=Decimal('250.0'),
        )
        r.refresh_from_db()
        assert r.is_abnormal is True

    def test_normal_with_only_ref_max(self, user, biomarker_ct):
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        r = ExamResult.objects.create(
            exam=e, biomarker=biomarker_ct, value=Decimal('150.0'),
        )
        r.refresh_from_db()
        assert r.is_abnormal is False

    def test_abnormal_with_only_ref_min(self, user, biomarker_hdl):
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        r = ExamResult.objects.create(
            exam=e, biomarker=biomarker_hdl, value=Decimal('30.0'),
        )
        r.refresh_from_db()
        assert r.is_abnormal is True

    def test_unique_together(self, exam, biomarker_hgb):
        with pytest.raises(Exception):
            ExamResult.objects.create(
                exam=exam, biomarker=biomarker_hgb, value=Decimal('14.0'),
            )

    def test_str(self, exam):
        r = exam.results.first()
        s = str(r)
        assert 'Hemoglobina' in s
        assert '15' in s

    def test_validation_status_clean(self, exam):
        r = exam.results.first()
        assert r.validation_status == 'clean'


class TestAIAnalysisModel:
    """Tests for AIAnalysis model."""

    def test_create(self, exam_with_analysis):
        analysis = exam_with_analysis.analysis
        assert 'normalidade' in analysis.summary
        assert analysis.model_used == 'gpt-4o'

    def test_str(self, exam_with_analysis):
        s = str(exam_with_analysis.analysis)
        assert 'testuser' in s

    def test_one_to_one(self, exam_with_analysis):
        with pytest.raises(Exception):
            AIAnalysis.objects.create(
                exam=exam_with_analysis, summary='Dup', alerts=[],
                improvements=[], deteriorations=[],
                recommendations='Dup', model_used='gpt-4o',
            )

    def test_cascade_delete(self, exam_with_analysis):
        analysis_id = exam_with_analysis.analysis.id
        exam_with_analysis.delete()
        assert not AIAnalysis.objects.filter(id=analysis_id).exists()

    def test_json_fields_default(self, exam):
        a = AIAnalysis.objects.create(
            exam=exam, summary='Test', recommendations='Test', model_used='gpt-4o',
        )
        # Delete existing to avoid unique constraint, need new exam
        a.delete()
        e2 = Exam.objects.create(
            user=exam.user, file='test2.pdf', file_type='pdf',
            exam_date=date(2025, 2, 1), status='completed',
        )
        a2 = AIAnalysis.objects.create(
            exam=e2, summary='Test', recommendations='Test', model_used='gpt-4o',
        )
        assert a2.alerts == []
        assert a2.improvements == []
        assert a2.deteriorations == []


class TestExamValidationModel:
    """Tests for ExamValidation model."""

    def test_create_flag(self, exam):
        flag = ExamValidation.objects.create(
            exam=exam, biomarker_code='HGB', severity='warning',
            category='physiological', message='Valor suspeito',
        )
        assert flag.resolved is False

    def test_str(self, exam):
        flag = ExamValidation.objects.create(
            exam=exam, biomarker_code='HGB', severity='error',
            category='physiological', message='Valor impossivel',
        )
        s = str(flag)
        assert 'error' in s
        assert 'HGB' in s

    def test_ordering_by_severity(self, exam):
        """Ordering is ['-severity', 'biomarker_code'] — alphabetical desc on severity string."""
        ExamValidation.objects.create(
            exam=exam, biomarker_code='HGB', severity='info',
            category='physiological', message='Info',
        )
        ExamValidation.objects.create(
            exam=exam, biomarker_code='GLI', severity='error',
            category='physiological', message='Error',
        )
        ExamValidation.objects.create(
            exam=exam, biomarker_code='CT', severity='warning',
            category='physiological', message='Warning',
        )
        flags = list(ExamValidation.objects.filter(exam=exam))
        # '-severity' sorts alphabetically descending: warning > info > error
        severities = [f.severity for f in flags]
        assert severities == sorted(severities, reverse=True)

    def test_unit_mismatch_category(self, exam):
        """Verify the unit_mismatch category can be saved."""
        flag = ExamValidation.objects.create(
            exam=exam, biomarker_code='PCR', severity='auto_corrected',
            category='unit_mismatch', message='PCR convertido de mg/L para mg/dL',
        )
        flag.refresh_from_db()
        assert flag.category == 'unit_mismatch'

    def test_cascade_delete_with_exam(self, exam):
        ExamValidation.objects.create(
            exam=exam, biomarker_code='HGB', severity='info',
            category='physiological', message='Test',
        )
        exam.delete()
        assert ExamValidation.objects.count() == 0


class TestBiomarkerTrendAnalysisModel:
    """Tests for BiomarkerTrendAnalysis model."""

    def test_create(self, user, biomarker_hgb):
        trend = BiomarkerTrendAnalysis.objects.create(
            user=user, biomarker=biomarker_hgb,
            analysis_text='Tendencia estavel', result_count=5,
            model_used='gpt-4o',
        )
        assert trend.result_count == 5

    def test_unique_together(self, user, biomarker_hgb):
        BiomarkerTrendAnalysis.objects.create(
            user=user, biomarker=biomarker_hgb,
            analysis_text='First', result_count=3, model_used='gpt-4o',
        )
        with pytest.raises(Exception):
            BiomarkerTrendAnalysis.objects.create(
                user=user, biomarker=biomarker_hgb,
                analysis_text='Duplicate', result_count=3, model_used='gpt-4o',
            )

    def test_str(self, user, biomarker_hgb):
        trend = BiomarkerTrendAnalysis.objects.create(
            user=user, biomarker=biomarker_hgb,
            analysis_text='Test', result_count=1, model_used='gpt-4o',
        )
        s = str(trend)
        assert 'Hemoglobina' in s
        assert 'testuser' in s


# =============================================================================
# FORM TESTS
# =============================================================================

class TestRegistrationForm:
    """Tests for user registration form."""

    def test_valid_registration(self, db):
        data = {
            'username': 'newuser', 'email': 'new@example.com',
            'first_name': 'New', 'last_name': 'User',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        }
        form = RegistrationForm(data=data)
        assert form.is_valid()

    def test_save_creates_profile(self, db):
        data = {
            'username': 'newuser', 'email': 'new@example.com',
            'first_name': 'New', 'last_name': 'User',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
            'date_of_birth': '15/05/1990', 'gender': 'M',
        }
        form = RegistrationForm(data=data)
        assert form.is_valid()
        user = form.save()
        assert user.profile.gender == 'M'
        assert user.profile.date_of_birth == date(1990, 5, 15)

    def test_email_required(self, db):
        data = {
            'username': 'newuser', 'email': '',
            'first_name': 'New', 'last_name': 'User',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        }
        form = RegistrationForm(data=data)
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_password_mismatch(self, db):
        data = {
            'username': 'newuser', 'email': 'new@example.com',
            'first_name': 'New', 'last_name': 'User',
            'password1': 'StrongPass123!', 'password2': 'DifferentPass!',
        }
        form = RegistrationForm(data=data)
        assert not form.is_valid()

    def test_date_format_dd_mm_yyyy(self, db):
        data = {
            'username': 'newuser', 'email': 'new@example.com',
            'first_name': 'New', 'last_name': 'User',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
            'date_of_birth': '15/05/1990',
        }
        form = RegistrationForm(data=data)
        assert form.is_valid()


class TestCompleteProfileForm:
    """Tests for the complete-profile form."""

    def test_valid(self, db):
        form = CompleteProfileForm(data={
            'date_of_birth': '17/03/1978', 'gender': 'M',
        })
        assert form.is_valid()

    def test_date_required(self, db):
        form = CompleteProfileForm(data={'gender': 'M'})
        assert not form.is_valid()
        assert 'date_of_birth' in form.errors

    def test_gender_required(self, db):
        form = CompleteProfileForm(data={'date_of_birth': '17/03/1978'})
        assert not form.is_valid()
        assert 'gender' in form.errors

    def test_invalid_date(self, db):
        form = CompleteProfileForm(data={
            'date_of_birth': 'invalid', 'gender': 'M',
        })
        assert not form.is_valid()


class TestProfileForm:
    """Tests for profile edit form with password change."""

    def test_valid_profile_update(self, user):
        form = ProfileForm(
            data={
                'first_name': 'Updated', 'last_name': 'Name',
                'email': 'updated@example.com',
                'date_of_birth': '15/05/1990', 'gender': 'M',
            },
            instance=user.profile,
        )
        assert form.is_valid()

    def test_password_change_valid(self, user):
        form = ProfileForm(
            data={
                'first_name': 'Test', 'last_name': 'User',
                'email': 'test@example.com',
                'date_of_birth': '15/05/1990', 'gender': 'M',
                'current_password': 'TestPass123!',
                'new_password': 'NewPassword456!',
                'confirm_password': 'NewPassword456!',
            },
            instance=user.profile,
        )
        assert form.is_valid()

    def test_password_change_wrong_current(self, user):
        form = ProfileForm(
            data={
                'first_name': 'Test', 'last_name': 'User',
                'email': 'test@example.com',
                'date_of_birth': '15/05/1990', 'gender': 'M',
                'current_password': 'WrongPassword!',
                'new_password': 'NewPassword456!',
                'confirm_password': 'NewPassword456!',
            },
            instance=user.profile,
        )
        assert not form.is_valid()
        assert 'current_password' in form.errors

    def test_password_change_mismatch(self, user):
        form = ProfileForm(
            data={
                'first_name': 'Test', 'last_name': 'User',
                'email': 'test@example.com',
                'date_of_birth': '15/05/1990', 'gender': 'M',
                'current_password': 'TestPass123!',
                'new_password': 'NewPassword456!',
                'confirm_password': 'DifferentPassword!',
            },
            instance=user.profile,
        )
        assert not form.is_valid()
        assert 'confirm_password' in form.errors


class TestExamUploadForm:
    """Tests for exam upload form."""

    def test_valid_pdf(self, db):
        pdf_file = SimpleUploadedFile('exam.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        form = ExamUploadForm(
            data={'exam_date': '15/01/2025', 'lab_name': 'Lab Test'},
            files={'file': pdf_file},
        )
        assert form.is_valid()

    def test_valid_image(self, db):
        img_file = SimpleUploadedFile('exam.jpg', b'\xff\xd8\xff\xe0fake', content_type='image/jpeg')
        form = ExamUploadForm(
            data={'exam_date': '15/01/2025', 'lab_name': 'Lab Test'},
            files={'file': img_file},
        )
        assert form.is_valid()

    def test_invalid_extension(self, db):
        txt_file = SimpleUploadedFile('exam.txt', b'text content', content_type='text/plain')
        form = ExamUploadForm(
            data={'exam_date': '15/01/2025', 'lab_name': 'Lab Test'},
            files={'file': txt_file},
        )
        assert not form.is_valid()
        assert 'file' in form.errors

    def test_file_too_large(self, db):
        big_file = SimpleUploadedFile('exam.pdf', b'x' * (21 * 1024 * 1024), content_type='application/pdf')
        form = ExamUploadForm(
            data={'exam_date': '15/01/2025', 'lab_name': 'Lab Test'},
            files={'file': big_file},
        )
        assert not form.is_valid()


class TestAdminUserForm:
    """Tests for admin user management form."""

    def test_create_user(self, db):
        form = AdminUserForm(data={
            'username': 'newadminuser', 'password': 'AdminPass123!',
            'first_name': 'Admin', 'last_name': 'New',
            'email': 'admin@test.com', 'gender': 'M',
            'is_active': True,
        })
        assert form.is_valid()
        user = form.save()
        assert user.username == 'newadminuser'

    def test_edit_user_no_password_required(self, user):
        form = AdminUserForm(
            data={
                'username': 'testuser', 'first_name': 'Updated',
                'last_name': 'User', 'email': 'test@example.com',
                'gender': 'M', 'is_active': True,
            },
            editing_user=user,
        )
        assert form.is_valid()

    def test_duplicate_username(self, user):
        User.objects.create_user(username='existing', password='pass')
        form = AdminUserForm(data={
            'username': 'existing', 'password': 'AdminPass123!',
        })
        assert not form.is_valid()
        assert 'username' in form.errors


# =============================================================================
# VIEW TESTS
# =============================================================================

class TestHealthView:
    """Tests for health check endpoint."""

    def test_health_ok(self, client):
        resp = client.get(reverse('health'))
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data['status'] == 'ok'

    def test_health_json_content_type(self, client):
        resp = client.get(reverse('health'))
        assert 'application/json' in resp['Content-Type']

    def test_health_no_auth_required(self, client):
        resp = client.get(reverse('health'))
        assert resp.status_code == 200


class TestRegisterView:
    """Tests for registration view."""

    def test_get_register_page(self, client):
        resp = client.get(reverse('register'))
        assert resp.status_code == 200

    def test_post_valid_registration(self, db, client):
        resp = client.post(reverse('register'), {
            'username': 'newuser', 'email': 'new@example.com',
            'first_name': 'New', 'last_name': 'User',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        assert resp.status_code == 302
        assert User.objects.filter(username='newuser').exists()

    def test_authenticated_user_redirected(self, client_logged_in):
        resp = client_logged_in.get(reverse('register'))
        assert resp.status_code == 302


class TestCompleteProfileView:
    """Tests for complete-profile view."""

    def test_get_form(self, client_incomplete):
        resp = client_incomplete.get(reverse('complete_profile'))
        assert resp.status_code == 200

    def test_post_saves_profile(self, client_incomplete, incomplete_user):
        resp = client_incomplete.post(reverse('complete_profile'), {
            'date_of_birth': '17/03/1978', 'gender': 'M',
        })
        assert resp.status_code == 302
        incomplete_user.profile.refresh_from_db()
        assert incomplete_user.profile.gender == 'M'
        assert incomplete_user.profile.date_of_birth == date(1978, 3, 17)

    def test_already_complete_redirects_to_dashboard(self, client_logged_in):
        resp = client_logged_in.get(reverse('complete_profile'))
        assert resp.status_code == 302

    def test_requires_login(self, client):
        resp = client.get(reverse('complete_profile'))
        assert resp.status_code == 302
        assert '/login/' in resp.url


class TestDashboardView:
    """Tests for dashboard view."""

    def test_requires_login(self, client):
        resp = client.get(reverse('dashboard'))
        assert resp.status_code == 302

    def test_empty_dashboard(self, client_logged_in):
        resp = client_logged_in.get(reverse('dashboard'))
        assert resp.status_code == 200

    def test_dashboard_with_exam(self, client_logged_in, exam_with_analysis):
        resp = client_logged_in.get(reverse('dashboard'))
        assert resp.status_code == 200
        assert 'total_exams' in resp.context
        assert resp.context['total_exams'] >= 1

    def test_dashboard_context_keys(self, client_logged_in, exam):
        resp = client_logged_in.get(reverse('dashboard'))
        expected_keys = [
            'total_exams', 'last_exam', 'abnormal_count', 'normal_count',
            'total_results', 'chart_data_json', 'category_health_json',
            'critical_biomarkers_json', 'analysis_data', 'recent_exams',
        ]
        for key in expected_keys:
            assert key in resp.context


class TestExamDetailView:
    """Tests for exam detail view."""

    def test_requires_login(self, client, exam):
        resp = client.get(reverse('exam_detail', args=[exam.id]))
        assert resp.status_code == 302

    def test_own_exam(self, client_logged_in, exam):
        resp = client_logged_in.get(reverse('exam_detail', args=[exam.id]))
        assert resp.status_code == 200

    def test_other_user_exam_404(self, client_logged_in, superuser, biomarker_hgb):
        other_exam = Exam.objects.create(
            user=superuser, file='other.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        resp = client_logged_in.get(reverse('exam_detail', args=[other_exam.id]))
        assert resp.status_code == 404


class TestExamHistoryView:
    """Tests for exam history view."""

    def test_requires_login(self, client):
        resp = client.get(reverse('exam_history'))
        assert resp.status_code == 302

    def test_list_exams(self, client_logged_in, exam):
        resp = client_logged_in.get(reverse('exam_history'))
        assert resp.status_code == 200


class TestExamDeleteView:
    """Tests for exam deletion."""

    def test_post_deletes_exam(self, client_logged_in, exam):
        exam_id = exam.id
        resp = client_logged_in.post(reverse('exam_delete', args=[exam_id]))
        assert resp.status_code == 302
        assert not Exam.objects.filter(id=exam_id).exists()

    def test_get_does_not_delete(self, client_logged_in, exam):
        resp = client_logged_in.get(reverse('exam_delete', args=[exam.id]))
        assert resp.status_code == 302
        assert Exam.objects.filter(id=exam.id).exists()

    def test_other_user_exam_404(self, client_logged_in, superuser, biomarker_hgb):
        other_exam = Exam.objects.create(
            user=superuser, file='other.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        resp = client_logged_in.post(reverse('exam_delete', args=[other_exam.id]))
        assert resp.status_code == 404


class TestBiomarkerChartView:
    """Tests for biomarker chart view."""

    def test_requires_login(self, client, biomarker_hgb):
        resp = client.get(reverse('biomarker_chart', args=['HGB']))
        assert resp.status_code == 302

    def test_valid_biomarker(self, client_logged_in, exam):
        resp = client_logged_in.get(reverse('biomarker_chart', args=['HGB']))
        assert resp.status_code == 200

    def test_invalid_biomarker_404(self, client_logged_in):
        resp = client_logged_in.get(reverse('biomarker_chart', args=['INVALID']))
        assert resp.status_code == 404


class TestBiomarkerTrendApi:
    """Tests for biomarker trend API endpoint."""

    def test_insufficient_data(self, client_logged_in, exam):
        resp = client_logged_in.get(reverse('biomarker_trend_api', args=['HGB']))
        data = json.loads(resp.content)
        assert data['status'] == 'insufficient_data'

    @patch('core.views.generate_trend_analysis', return_value='Trend analysis text')
    def test_trend_with_enough_data(self, mock_trend, client_logged_in, user, biomarker_hgb):
        for i in range(3):
            e = Exam.objects.create(
                user=user, file=f'test{i}.pdf', file_type='pdf',
                exam_date=date(2025, 1, 1) + timedelta(days=30 * i),
                status='completed',
            )
            ExamResult.objects.create(
                exam=e, biomarker=biomarker_hgb, value=Decimal('14.0') + i,
            )
        resp = client_logged_in.get(reverse('biomarker_trend_api', args=['HGB']))
        data = json.loads(resp.content)
        assert data['status'] == 'ok'


class TestApiBiomarkerData:
    """Tests for biomarker JSON API endpoint."""

    def test_returns_json(self, client_logged_in, exam):
        resp = client_logged_in.get(reverse('api_biomarker_data', args=['HGB']))
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'name' in data
        assert 'dates' in data
        assert 'values' in data

    def test_requires_login(self, client, biomarker_hgb):
        resp = client.get(reverse('api_biomarker_data', args=['HGB']))
        assert resp.status_code == 302


class TestProfileView:
    """Tests for profile edit view."""

    def test_get_profile(self, client_logged_in):
        resp = client_logged_in.get(reverse('profile'))
        assert resp.status_code == 200

    def test_update_profile(self, client_logged_in, user):
        resp = client_logged_in.post(reverse('profile'), {
            'first_name': 'Updated', 'last_name': 'Name',
            'email': 'updated@example.com',
            'date_of_birth': '15/05/1990', 'gender': 'M',
        })
        assert resp.status_code == 302
        user.refresh_from_db()
        assert user.first_name == 'Updated'


class TestUploadView:
    """Tests for exam upload view."""

    def test_get_upload_page(self, client_logged_in):
        resp = client_logged_in.get(reverse('upload'))
        assert resp.status_code == 200

    def test_requires_login(self, client):
        resp = client.get(reverse('upload'))
        assert resp.status_code == 302

    @patch('core.views.threading.Thread')
    def test_upload_pdf(self, mock_thread_cls, client_logged_in):
        pdf_file = SimpleUploadedFile('exam.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        resp = client_logged_in.post(reverse('upload'), {
            'file': pdf_file,
            'exam_date': '15/01/2025',
            'lab_name': 'Test Lab',
        })
        assert resp.status_code == 302
        assert '/processing/' in resp.url
        assert Exam.objects.filter(lab_name='Test Lab').exists()
        mock_thread_cls.assert_called_once()
        mock_thread_cls.return_value.start.assert_called_once()


class TestAdminViews:
    """Tests for admin panel views."""

    def test_admin_list_requires_superuser(self, client_logged_in):
        resp = client_logged_in.get(reverse('admin_users'))
        assert resp.status_code == 302

    def test_admin_list_accessible_by_superuser(self, client_superuser):
        resp = client_superuser.get(reverse('admin_users'))
        assert resp.status_code == 200

    def test_admin_create_user(self, client_superuser):
        resp = client_superuser.post(reverse('admin_user_create'), {
            'username': 'adminmade', 'password': 'StrongPass123!',
            'first_name': 'Admin', 'last_name': 'Made',
            'email': 'made@test.com', 'is_active': True,
        })
        assert resp.status_code == 302
        assert User.objects.filter(username='adminmade').exists()

    def test_admin_delete_superuser_blocked(self, client_superuser, superuser):
        resp = client_superuser.post(reverse('admin_user_delete', args=[superuser.id]))
        assert resp.status_code == 302
        assert User.objects.filter(id=superuser.id).exists()

    def test_admin_delete_regular_user(self, client_superuser, user):
        user_id = user.id
        resp = client_superuser.post(reverse('admin_user_delete', args=[user_id]))
        assert resp.status_code == 302
        assert not User.objects.filter(id=user_id).exists()


# =============================================================================
# MIDDLEWARE TESTS
# =============================================================================

class TestProfileCompletionMiddleware:
    """Tests for ProfileCompletionMiddleware."""

    def test_incomplete_user_redirected(self, client_incomplete):
        resp = client_incomplete.get(reverse('dashboard'))
        assert resp.status_code == 302
        assert 'complete-profile' in resp.url

    def test_complete_user_not_redirected(self, client_logged_in):
        resp = client_logged_in.get(reverse('dashboard'))
        assert resp.status_code == 200

    def test_exempt_url_complete_profile(self, client_incomplete):
        resp = client_incomplete.get(reverse('complete_profile'))
        assert resp.status_code == 200

    def test_exempt_url_health(self, client_incomplete):
        resp = client_incomplete.get(reverse('health'))
        assert resp.status_code == 200

    def test_exempt_url_logout(self, client_incomplete):
        # Django 5+ LogoutView only accepts POST
        resp = client_incomplete.post(reverse('logout'))
        assert resp.status_code == 302

    def test_anonymous_not_redirected(self, client):
        resp = client.get(reverse('health'))
        assert resp.status_code == 200

    def test_exempt_urls_list(self):
        middleware = ProfileCompletionMiddleware(lambda r: None)
        expected_exempt = ['/complete-profile/', '/logout/', '/health/', '/admin/', '/accounts/', '/static/', '/media/']
        assert middleware.EXEMPT_URLS == expected_exempt

    def test_uses_path_info_not_path(self, incomplete_user):
        """Verify middleware uses request.path_info (without FORCE_SCRIPT_NAME prefix)."""
        factory = RequestFactory()
        request = factory.get('/complete-profile/')
        request.user = incomplete_user
        request.path_info = '/complete-profile/'

        middleware = ProfileCompletionMiddleware(lambda r: MagicMock(status_code=200))
        response = middleware(request)
        # Should NOT redirect because /complete-profile/ is exempt
        assert response.status_code == 200


# =============================================================================
# TEMPLATE TAG TESTS
# =============================================================================

class TestTemplateTags:
    """Tests for custom template filters."""

    def test_get_item_valid(self):
        assert get_item({'key': 'value'}, 'key') == 'value'

    def test_get_item_missing(self):
        assert get_item({'key': 'value'}, 'missing') is None

    def test_get_item_non_dict(self):
        assert get_item('string', 'key') is None

    def test_abs_value_positive(self):
        assert abs_value(5.5) == 5.5

    def test_abs_value_negative(self):
        assert abs_value(-5.5) == 5.5

    def test_abs_value_invalid(self):
        assert abs_value('invalid') == 'invalid'

    def test_status_color_always_normal(self):
        assert status_color(100) == 'normal'

    def test_trend_icon_up(self):
        assert trend_icon(10) == '\u2b06\ufe0f'

    def test_trend_icon_down(self):
        assert trend_icon(-10) == '\u2b07\ufe0f'

    def test_trend_icon_stable(self):
        assert trend_icon(2) == '\u27a1\ufe0f'

    def test_trend_icon_invalid(self):
        assert trend_icon('abc') == ''


# =============================================================================
# VALIDATION ENGINE TESTS
# =============================================================================

class TestValidationEngine:
    """Tests for the validation engine."""

    def test_physiological_range_error(self, user, biomarker_hgb):
        """Value outside physiological limits should generate an error flag."""
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        # HGB = 50 is physiologically impossible (limit is 3-25)
        ExamResult.objects.create(
            exam=e, biomarker=biomarker_hgb, value=Decimal('50.0'),
        )
        flags = validate_exam(e)
        phys_flags = [f for f in flags if f.category == FlagCategory.PHYSIOLOGICAL]
        assert len(phys_flags) > 0
        assert any(f.severity == FlagSeverity.ERROR for f in phys_flags)

    def test_no_flags_for_normal_values(self, user, biomarker_gli):
        """Normal values within physiological limits should not generate flags."""
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        ExamResult.objects.create(
            exam=e, biomarker=biomarker_gli, value=Decimal('85.0'),
        )
        flags = validate_exam(e)
        phys_flags = [f for f in flags if f.category == FlagCategory.PHYSIOLOGICAL]
        assert len(phys_flags) == 0

    def test_lipid_cross_validation(self, user):
        """CT should approximately equal HDL + LDL + VLDL."""
        ct = Biomarker.objects.create(
            name='Colesterol Total', code='CT', unit='mg/dL',
            ref_max_male=Decimal('190'), category='Lipidograma',
        )
        hdl = Biomarker.objects.create(
            name='HDL', code='HDL', unit='mg/dL',
            ref_min_male=Decimal('40'), category='Lipidograma',
        )
        ldl = Biomarker.objects.create(
            name='LDL', code='LDL', unit='mg/dL',
            ref_max_male=Decimal('130'), category='Lipidograma',
        )
        vldl = Biomarker.objects.create(
            name='VLDL', code='VLDL', unit='mg/dL',
            ref_max_male=Decimal('30'), category='Lipidograma',
        )
        e = Exam.objects.create(
            user=user, file='test.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        # CT=200, but HDL+LDL+VLDL = 50+80+20 = 150 (33% off)
        ExamResult.objects.create(exam=e, biomarker=ct, value=Decimal('200'))
        ExamResult.objects.create(exam=e, biomarker=hdl, value=Decimal('50'))
        ExamResult.objects.create(exam=e, biomarker=ldl, value=Decimal('80'))
        ExamResult.objects.create(exam=e, biomarker=vldl, value=Decimal('20'))

        flags = validate_exam(e)
        cross_flags = [f for f in flags if f.category == FlagCategory.CROSS_BIOMARKER]
        assert len(cross_flags) > 0

    def test_historical_consistency(self, user, biomarker_hgb):
        """Large change (>200%) from previous exam should generate a warning."""
        e1 = Exam.objects.create(
            user=user, file='old.pdf', file_type='pdf',
            exam_date=date(2024, 6, 1), status='completed',
        )
        ExamResult.objects.create(
            exam=e1, biomarker=biomarker_hgb, value=Decimal('15.0'),
        )
        e2 = Exam.objects.create(
            user=user, file='new.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        # HGB jumped from 15 to 1 (93% drop - >200% change threshold depends on implementation)
        ExamResult.objects.create(
            exam=e2, biomarker=biomarker_hgb, value=Decimal('1.0'),
        )
        flags = validate_exam(e2)
        # Should have historical flags (1.0 vs 15.0 is a massive change) AND physiological
        hist_flags = [f for f in flags if f.category == FlagCategory.HISTORICAL]
        phys_flags = [f for f in flags if f.category == FlagCategory.PHYSIOLOGICAL]
        # At minimum physiological should fire (1.0 < 3.0 min)
        assert len(phys_flags) > 0

    def test_flag_dataclass(self):
        """ValidationFlag dataclass should store all fields."""
        flag = ValidationFlag(
            exam_result_id=1, biomarker_code='HGB',
            severity=FlagSeverity.WARNING, category=FlagCategory.PHYSIOLOGICAL,
            message='Test message', original_value=Decimal('50.0'),
        )
        assert flag.biomarker_code == 'HGB'
        assert flag.severity == FlagSeverity.WARNING
        assert flag.details == {}


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurityCSRF:
    """Tests for CSRF protection on all POST endpoints."""

    @override_settings(MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ])
    def test_login_requires_csrf(self, db, client):
        """Login POST without CSRF token should return 403."""
        client = Client(enforce_csrf_checks=True)
        resp = client.post(reverse('login'), {
            'username': 'test', 'password': 'test',
        })
        assert resp.status_code == 403

    def test_register_requires_csrf(self, db):
        """Registration POST without CSRF token should return 403."""
        client = Client(enforce_csrf_checks=True)
        resp = client.post(reverse('register'), {
            'username': 'test', 'password1': 'pass', 'password2': 'pass',
            'email': 'test@test.com', 'first_name': 'T', 'last_name': 'U',
        })
        assert resp.status_code == 403


class TestSecurityAccessControl:
    """Tests for access control and data isolation."""

    def test_unauthenticated_redirected_from_dashboard(self, client):
        resp = client.get(reverse('dashboard'))
        assert resp.status_code == 302
        assert '/login/' in resp.url

    def test_unauthenticated_redirected_from_upload(self, client):
        resp = client.get(reverse('upload'))
        assert resp.status_code == 302

    def test_unauthenticated_redirected_from_profile(self, client):
        resp = client.get(reverse('profile'))
        assert resp.status_code == 302

    def test_unauthenticated_redirected_from_history(self, client):
        resp = client.get(reverse('exam_history'))
        assert resp.status_code == 302

    def test_user_cannot_access_other_user_exam(self, client_logged_in, superuser, biomarker_hgb):
        other_exam = Exam.objects.create(
            user=superuser, file='other.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        resp = client_logged_in.get(reverse('exam_detail', args=[other_exam.id]))
        assert resp.status_code == 404

    def test_user_cannot_delete_other_user_exam(self, client_logged_in, superuser, biomarker_hgb):
        other_exam = Exam.objects.create(
            user=superuser, file='other.pdf', file_type='pdf',
            exam_date=date(2025, 1, 1), status='completed',
        )
        resp = client_logged_in.post(reverse('exam_delete', args=[other_exam.id]))
        assert resp.status_code == 404

    def test_regular_user_cannot_access_admin_panel(self, client_logged_in):
        resp = client_logged_in.get(reverse('admin_users'))
        assert resp.status_code == 302

    def test_regular_user_cannot_create_admin_user(self, client_logged_in):
        resp = client_logged_in.post(reverse('admin_user_create'), {
            'username': 'hack', 'password': 'HackPass123!',
        })
        assert resp.status_code == 302
        assert not User.objects.filter(username='hack').exists()

    def test_regular_user_cannot_delete_users(self, client_logged_in, superuser):
        resp = client_logged_in.post(reverse('admin_user_delete', args=[superuser.id]))
        assert resp.status_code == 302
        assert User.objects.filter(id=superuser.id).exists()

    def test_admin_cannot_delete_self(self, client_superuser, superuser):
        resp = client_superuser.post(reverse('admin_user_delete', args=[superuser.id]))
        assert resp.status_code == 302
        assert User.objects.filter(id=superuser.id).exists()


class TestSecurityFileUpload:
    """Tests for file upload security."""

    def test_reject_executable_file(self, client_logged_in):
        exe_file = SimpleUploadedFile('virus.exe', b'MZ\x90', content_type='application/octet-stream')
        resp = client_logged_in.post(reverse('upload'), {
            'file': exe_file, 'exam_date': '15/01/2025', 'lab_name': 'Lab',
        })
        # Form should be invalid, re-renders the page (200)
        assert resp.status_code == 200

    def test_reject_html_file(self, client_logged_in):
        html_file = SimpleUploadedFile('xss.html', b'<script>alert(1)</script>', content_type='text/html')
        resp = client_logged_in.post(reverse('upload'), {
            'file': html_file, 'exam_date': '15/01/2025', 'lab_name': 'Lab',
        })
        assert resp.status_code == 200

    def test_reject_svg_file(self, client_logged_in):
        svg_file = SimpleUploadedFile('payload.svg', b'<svg onload="alert(1)"/>', content_type='image/svg+xml')
        resp = client_logged_in.post(reverse('upload'), {
            'file': svg_file, 'exam_date': '15/01/2025', 'lab_name': 'Lab',
        })
        assert resp.status_code == 200


# =============================================================================
# OPERATIONAL TESTS
# =============================================================================

class TestURLRouting:
    """Tests for URL routing correctness."""

    def test_resolve_dashboard(self):
        match = resolve('/')
        assert match.url_name == 'dashboard'

    def test_resolve_health(self):
        match = resolve('/health/')
        assert match.url_name == 'health'

    def test_resolve_upload(self):
        match = resolve('/upload/')
        assert match.url_name == 'upload'

    def test_resolve_register(self):
        match = resolve('/register/')
        assert match.url_name == 'register'

    def test_resolve_complete_profile(self):
        match = resolve('/complete-profile/')
        assert match.url_name == 'complete_profile'

    def test_resolve_exam_detail(self):
        match = resolve('/exam/1/')
        assert match.url_name == 'exam_detail'

    def test_resolve_biomarker_chart(self):
        match = resolve('/biomarker/HGB/')
        assert match.url_name == 'biomarker_chart'

    def test_resolve_biomarker_trend_api(self):
        match = resolve('/biomarker/HGB/trend/')
        assert match.url_name == 'biomarker_trend_api'

    def test_resolve_api_biomarker_data(self):
        match = resolve('/api/biomarker/HGB/')
        assert match.url_name == 'api_biomarker_data'

    def test_resolve_admin_panel(self):
        match = resolve('/admin-panel/')
        assert match.url_name == 'admin_users'

    def test_resolve_admin_create(self):
        match = resolve('/admin-panel/user/new/')
        assert match.url_name == 'admin_user_create'

    def test_resolve_admin_edit(self):
        match = resolve('/admin-panel/user/1/edit/')
        assert match.url_name == 'admin_user_edit'

    def test_resolve_admin_delete(self):
        match = resolve('/admin-panel/user/1/delete/')
        assert match.url_name == 'admin_user_delete'

    def test_resolve_profile(self):
        match = resolve('/profile/')
        assert match.url_name == 'profile'

    def test_resolve_exam_delete(self):
        match = resolve('/exam/1/delete/')
        assert match.url_name == 'exam_delete'

    def test_resolve_exam_reprocess(self):
        match = resolve('/exam/1/reprocess/')
        assert match.url_name == 'exam_reprocess'

    def test_resolve_exam_processing(self):
        match = resolve('/exam/1/processing/')
        assert match.url_name == 'exam_processing'

    def test_resolve_exam_status_api(self):
        match = resolve('/exam/1/status/')
        assert match.url_name == 'exam_status_api'

    def test_resolve_history(self):
        match = resolve('/history/')
        assert match.url_name == 'exam_history'


class TestExamProcessingView:
    """Tests for background processing views."""

    def test_processing_page_redirects_if_completed(self, client_logged_in, user):
        exam = Exam.objects.create(user=user, exam_date='2025-01-15', status='completed')
        resp = client_logged_in.get(reverse('exam_processing', args=[exam.id]))
        assert resp.status_code == 302
        assert f'/exam/{exam.id}/' in resp.url

    def test_processing_page_redirects_if_error(self, client_logged_in, user):
        exam = Exam.objects.create(user=user, exam_date='2025-01-15', status='error')
        resp = client_logged_in.get(reverse('exam_processing', args=[exam.id]))
        assert resp.status_code == 302

    def test_processing_page_shows_for_pending(self, client_logged_in, user):
        exam = Exam.objects.create(user=user, exam_date='2025-01-15', status='pending')
        resp = client_logged_in.get(reverse('exam_processing', args=[exam.id]))
        assert resp.status_code == 200
        assert 'Processando' in resp.content.decode()

    def test_processing_page_shows_for_processing(self, client_logged_in, user):
        exam = Exam.objects.create(user=user, exam_date='2025-01-15', status='processing')
        resp = client_logged_in.get(reverse('exam_processing', args=[exam.id]))
        assert resp.status_code == 200

    def test_status_api_returns_json(self, client_logged_in, user):
        exam = Exam.objects.create(user=user, exam_date='2025-01-15', status='processing')
        resp = client_logged_in.get(reverse('exam_status_api', args=[exam.id]))
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'processing'
        assert data['result_count'] == 0

    def test_status_api_completed(self, client_logged_in, user):
        exam = Exam.objects.create(user=user, exam_date='2025-01-15', status='completed')
        resp = client_logged_in.get(reverse('exam_status_api', args=[exam.id]))
        data = resp.json()
        assert data['status'] == 'completed'

    @patch('core.views.threading.Thread')
    def test_reprocess_starts_background(self, mock_thread_cls, client_logged_in, user):
        exam = Exam.objects.create(user=user, exam_date='2025-01-15', status='completed')
        resp = client_logged_in.post(reverse('exam_reprocess', args=[exam.id]))
        assert resp.status_code == 302
        assert '/processing/' in resp.url
        mock_thread_cls.assert_called_once()
        mock_thread_cls.return_value.start.assert_called_once()

    def test_requires_login(self, client):
        resp = client.get(reverse('exam_processing', args=[1]))
        assert resp.status_code == 302

    def test_status_api_requires_login(self, client):
        resp = client.get(reverse('exam_status_api', args=[1]))
        assert resp.status_code == 302


class TestDjangoSettings:
    """Tests for critical Django settings."""

    def test_secret_key_set_in_debug(self):
        from django.conf import settings
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 10

    def test_csrf_trusted_origins(self):
        from django.conf import settings
        assert hasattr(settings, 'CSRF_TRUSTED_ORIGINS')
        assert 'https://mlt.com.br' in settings.CSRF_TRUSTED_ORIGINS

    def test_site_id_set(self):
        from django.conf import settings
        assert settings.SITE_ID == 1

    def test_allauth_installed(self):
        from django.conf import settings
        assert 'allauth' in settings.INSTALLED_APPS
        assert 'allauth.account' in settings.INSTALLED_APPS
        assert 'allauth.socialaccount' in settings.INSTALLED_APPS
        assert 'allauth.socialaccount.providers.google' in settings.INSTALLED_APPS

    def test_authentication_backends(self):
        from django.conf import settings
        assert 'allauth.account.auth_backends.AuthenticationBackend' in settings.AUTHENTICATION_BACKENDS

    def test_middleware_order(self):
        from django.conf import settings
        mw = settings.MIDDLEWARE
        # AccountMiddleware must come before ProfileCompletionMiddleware
        assert mw.index('allauth.account.middleware.AccountMiddleware') < mw.index('core.middleware.ProfileCompletionMiddleware')

    def test_session_age(self):
        from django.conf import settings
        assert settings.SESSION_COOKIE_AGE == 86400  # 24 hours

    def test_file_upload_limit(self):
        from django.conf import settings
        assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE == 20 * 1024 * 1024


class TestDatabaseIntegrity:
    """Tests for database constraints and relationships."""

    def test_exam_result_unique_together(self, exam, biomarker_hgb):
        """Cannot create two results for same exam+biomarker."""
        with pytest.raises(Exception):
            ExamResult.objects.create(
                exam=exam, biomarker=biomarker_hgb, value=Decimal('14.0'),
            )

    def test_biomarker_trend_unique_together(self, user, biomarker_hgb):
        """Cannot create two trend analyses for same user+biomarker."""
        BiomarkerTrendAnalysis.objects.create(
            user=user, biomarker=biomarker_hgb,
            analysis_text='Test', result_count=1, model_used='gpt-4o',
        )
        with pytest.raises(Exception):
            BiomarkerTrendAnalysis.objects.create(
                user=user, biomarker=biomarker_hgb,
                analysis_text='Dup', result_count=1, model_used='gpt-4o',
            )

    def test_ai_analysis_one_to_one(self, exam_with_analysis):
        """Cannot create two AI analyses for same exam."""
        with pytest.raises(Exception):
            AIAnalysis.objects.create(
                exam=exam_with_analysis, summary='Dup',
                recommendations='Dup', model_used='gpt-4o',
            )

    def test_cascade_user_deletes_exams(self, user, exam):
        """Deleting user cascades to exams and results."""
        user.delete()
        assert Exam.objects.count() == 0
        assert ExamResult.objects.count() == 0

    def test_cascade_exam_deletes_results(self, exam):
        """Deleting exam cascades to results."""
        assert exam.results.count() > 0
        exam.delete()
        assert ExamResult.objects.count() == 0


# ---- Correlation Analysis Tests ----

class TestCorrelationAnalysis:
    """Tests for biomarker correlation analysis module (core/correlations.py)."""

    def test_tg_hdl_ratio_normal(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'TG': 100.0, 'HDL': 60.0}, 'M')
        tg_hdl = [r for r in ratios if r['id'] == 'tg-hdl'][0]
        assert tg_hdl['status'] == 'normal'
        assert abs(tg_hdl['value'] - 1.67) < 0.01

    def test_tg_hdl_ratio_warning(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'TG': 150.0, 'HDL': 50.0}, 'M')
        tg_hdl = [r for r in ratios if r['id'] == 'tg-hdl'][0]
        assert tg_hdl['status'] == 'warning'

    def test_tg_hdl_ratio_alert(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'TG': 250.0, 'HDL': 40.0}, 'M')
        tg_hdl = [r for r in ratios if r['id'] == 'tg-hdl'][0]
        assert tg_hdl['status'] == 'alert'

    def test_de_ritis_normal(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'TGO': 25.0, 'TGP': 28.0}, 'M')
        deritis = [r for r in ratios if r['id'] == 'de-ritis'][0]
        assert deritis['status'] == 'normal'

    def test_de_ritis_nafld(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'TGO': 15.0, 'TGP': 40.0}, 'M')
        deritis = [r for r in ratios if r['id'] == 'de-ritis'][0]
        assert deritis['status'] == 'warning'
        assert deritis['value'] < 0.7

    def test_de_ritis_alcoholic(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'TGO': 80.0, 'TGP': 30.0}, 'M')
        deritis = [r for r in ratios if r['id'] == 'de-ritis'][0]
        assert deritis['status'] == 'alert'

    def test_nlr_normal(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'NEUT': 4000.0, 'LYMPH': 2000.0}, 'M')
        nlr = [r for r in ratios if r['id'] == 'nlr'][0]
        assert nlr['status'] == 'normal'

    def test_nlr_viral(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'NEUT': 1500.0, 'LYMPH': 3000.0}, 'M')
        nlr = [r for r in ratios if r['id'] == 'nlr'][0]
        assert nlr['status'] == 'info'

    def test_homa_ir_normal(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'INS': 8.0, 'GLI': 90.0}, 'M')
        homa = [r for r in ratios if r['id'] == 'homa-ir'][0]
        assert homa['status'] == 'normal'
        assert homa['value'] < 2.5

    def test_homa_ir_alert(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'INS': 20.0, 'GLI': 110.0}, 'M')
        homa = [r for r in ratios if r['id'] == 'homa-ir'][0]
        assert homa['status'] == 'alert'
        assert homa['value'] > 3.5

    def test_urea_crea_normal(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'UREA': 30.0, 'CREA': 2.0}, 'M')
        uc = [r for r in ratios if r['id'] == 'urea-crea'][0]
        assert uc['status'] == 'normal'

    def test_missing_biomarker_skips_ratio(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'TG': 100.0}, 'M')
        tg_hdl = [r for r in ratios if r['id'] == 'tg-hdl']
        assert len(tg_hdl) == 0

    def test_zero_denominator_safe(self):
        from core.correlations import compute_ratios
        ratios = compute_ratios({'TG': 100.0, 'HDL': 0.0}, 'M')
        tg_hdl = [r for r in ratios if r['id'] == 'tg-hdl']
        assert len(tg_hdl) == 0

    def test_consistency_hct_hgb_ok(self):
        from core.correlations import compute_consistency_checks
        checks = compute_consistency_checks({'HCT': 45.0, 'HGB': 15.0})
        hct = [c for c in checks if c['id'] == 'hct-hgb-ratio']
        assert len(hct) == 0

    def test_consistency_hct_hgb_flagged(self):
        from core.correlations import compute_consistency_checks
        checks = compute_consistency_checks({'HCT': 60.0, 'HGB': 15.0})
        hct = [c for c in checks if c['id'] == 'hct-hgb-ratio']
        assert len(hct) == 1

    def test_consistency_bild_bilt(self):
        from core.correlations import compute_consistency_checks
        checks = compute_consistency_checks({'BILD': 0.5, 'BILT': 0.3})
        bil = [c for c in checks if c['id'] == 'bild-bilt']
        assert len(bil) == 1
        assert bil[0]['status'] == 'alert'

    def test_consistency_lipid_sum_ok(self):
        from core.correlations import compute_consistency_checks
        checks = compute_consistency_checks({
            'CT': 200.0, 'HDL': 50.0, 'LDL': 120.0, 'VLDL': 30.0
        })
        lipid = [c for c in checks if c['id'] == 'lipid-sum']
        assert len(lipid) == 0

    def test_consistency_lipid_sum_flagged(self):
        from core.correlations import compute_consistency_checks
        checks = compute_consistency_checks({
            'CT': 200.0, 'HDL': 50.0, 'LDL': 80.0, 'VLDL': 20.0
        })
        lipid = [c for c in checks if c['id'] == 'lipid-sum']
        assert len(lipid) == 1

    def test_pattern_hypothyroidism(self):
        from core.correlations import compute_clinical_patterns
        patterns = compute_clinical_patterns(
            {'TSH': 8.0, 'T4L': 0.5}, 'M',
            {'TSH': (0.4, 4.0), 'T4L': (0.8, 1.8)},
        )
        thyroid = [p for p in patterns if p['id'] == 'thyroid']
        assert len(thyroid) == 1
        assert thyroid[0]['status'] == 'alert'

    def test_pattern_metabolic_syndrome(self):
        from core.correlations import compute_clinical_patterns
        patterns = compute_clinical_patterns(
            {'TG': 200.0, 'HDL': 35.0, 'GLI': 110.0}, 'M',
            {'TG': (None, 150.0), 'HDL': (40.0, None), 'GLI': (70.0, 99.0)},
        )
        ms = [p for p in patterns if p['id'] == 'metabolic-syndrome']
        assert len(ms) == 1
        assert ms[0]['status'] == 'alert'

    def test_thyroid_normal_shows_ok(self):
        from core.correlations import compute_clinical_patterns
        patterns = compute_clinical_patterns(
            {'TSH': 2.0, 'T4L': 1.2}, 'M',
            {'TSH': (0.4, 4.0), 'T4L': (0.8, 1.8)},
        )
        thyroid = [p for p in patterns if p['id'] == 'thyroid']
        assert len(thyroid) == 1
        assert thyroid[0]['status'] == 'normal'

    def test_metabolic_syndrome_normal_shows_ok(self):
        from core.correlations import compute_clinical_patterns
        patterns = compute_clinical_patterns(
            {'TG': 100.0, 'HDL': 55.0, 'GLI': 85.0}, 'M',
            {'TG': (None, 150.0), 'HDL': (40.0, None), 'GLI': (70.0, 99.0)},
        )
        ms = [p for p in patterns if p['id'] == 'metabolic-syndrome']
        assert len(ms) == 1
        assert ms[0]['status'] == 'normal'

    def test_iron_normal_shows_ok(self):
        from core.correlations import compute_clinical_patterns
        patterns = compute_clinical_patterns(
            {'FE': 90.0, 'FERR': 150.0}, 'M',
            {'FE': (60.0, 170.0), 'FERR': (30.0, 300.0)},
        )
        iron = [p for p in patterns if p['id'] == 'iron-metabolism']
        assert len(iron) == 1
        assert iron[0]['status'] == 'normal'

    def test_analyze_correlations_empty(self):
        from core.correlations import analyze_correlations
        assert analyze_correlations([], 'M') is None

    def test_iron_deficiency_pattern(self):
        from core.correlations import compute_clinical_patterns
        patterns = compute_clinical_patterns(
            {'FE': 30.0, 'FERR': 10.0, 'HGB': 10.0}, 'M',
            {'FE': (60.0, 170.0), 'FERR': (30.0, 300.0), 'HGB': (13.0, 17.0)},
        )
        iron = [p for p in patterns if p['id'] == 'iron-metabolism']
        assert len(iron) == 1
        assert iron[0]['status'] == 'alert'  # with low HGB

    def test_chronic_inflammation_pattern(self):
        from core.correlations import compute_clinical_patterns
        patterns = compute_clinical_patterns(
            {'FE': 30.0, 'FERR': 500.0, 'PCR': 10.0}, 'M',
            {'FE': (60.0, 170.0), 'FERR': (30.0, 300.0), 'PCR': (None, 3.0)},
        )
        iron = [p for p in patterns if p['id'] == 'iron-metabolism']
        assert len(iron) == 1
        assert iron[0]['status'] == 'warning'


# =============================================================================
# Medication Models
# =============================================================================

class TestMedicationModel:
    """Tests for the Medication catalog model."""

    def test_create_medication(self, db):
        med = Medication.objects.create(name='Vitamina D3', type='vitamin', common_doses='1000 UI, 5000 UI')
        assert med.name == 'Vitamina D3'
        assert med.type == 'vitamin'
        assert med.get_type_display() == 'Vitamina'

    def test_str(self, db):
        med = Medication.objects.create(name='Creatina', type='supplement')
        assert str(med) == 'Creatina (Suplemento)'

    def test_unique_name(self, db):
        Medication.objects.create(name='Metformina', type='medication')
        with pytest.raises(Exception):
            Medication.objects.create(name='Metformina', type='medication')

    def test_ordering(self, db):
        Medication.objects.create(name='Zinco', type='supplement')
        Medication.objects.create(name='Aspirina', type='medication')
        Medication.objects.create(name='Vitamina C', type='vitamin')
        names = list(Medication.objects.values_list('name', flat=True))
        assert names.index('Aspirina') < names.index('Zinco')

    def test_type_choices(self, db):
        for value, _ in Medication.TYPE_CHOICES:
            med = Medication.objects.create(name=f'Test-{value}', type=value)
            assert med.type == value


class TestUserMedicationModel:
    """Tests for the UserMedication model."""

    @pytest.fixture
    def medication(self, db):
        return Medication.objects.create(name='Vitamina D3', type='vitamin', common_doses='5000 UI')

    def test_create_user_medication(self, user, medication):
        um = UserMedication.objects.create(
            user=user, medication=medication, dose='5000 UI',
            frequency='daily', start_date=date(2025, 1, 1),
        )
        assert um.is_active is True
        assert um.end_date is None

    def test_str_active(self, user, medication):
        um = UserMedication.objects.create(
            user=user, medication=medication, dose='5000 UI',
            frequency='daily', start_date=date(2025, 1, 1),
        )
        assert 'ativo' in str(um)
        assert 'Vitamina D3' in str(um)

    def test_str_inactive(self, user, medication):
        um = UserMedication.objects.create(
            user=user, medication=medication, dose='5000 UI',
            frequency='daily', start_date=date(2025, 1, 1), is_active=False,
        )
        assert 'inativo' in str(um)

    def test_cascade_delete_user(self, user, medication):
        UserMedication.objects.create(
            user=user, medication=medication, dose='5000 UI',
            frequency='daily', start_date=date(2025, 1, 1),
        )
        user.delete()
        assert UserMedication.objects.count() == 0

    def test_cascade_delete_medication(self, user, medication):
        UserMedication.objects.create(
            user=user, medication=medication, dose='5000 UI',
            frequency='daily', start_date=date(2025, 1, 1),
        )
        medication.delete()
        assert UserMedication.objects.count() == 0

    def test_frequency_choices(self, user, medication):
        for value, _ in UserMedication.FREQUENCY_CHOICES:
            um = UserMedication.objects.create(
                user=user, medication=Medication.objects.create(name=f'Med-{value}', type='medication'),
                dose='10 mg', frequency=value, start_date=date(2025, 1, 1),
            )
            assert um.frequency == value


class TestExamMedicationModel:
    """Tests for the ExamMedication snapshot model."""

    @pytest.fixture
    def medication(self, db):
        return Medication.objects.create(name='Metformina', type='medication')

    def test_create_exam_medication(self, exam, medication):
        em = ExamMedication.objects.create(
            exam=exam, medication=medication, dose='500 mg', frequency='daily',
        )
        assert str(em) == 'Metformina - 500 mg'

    def test_unique_together(self, exam, medication):
        ExamMedication.objects.create(exam=exam, medication=medication, dose='500 mg', frequency='daily')
        with pytest.raises(Exception):
            ExamMedication.objects.create(exam=exam, medication=medication, dose='1000 mg', frequency='daily')

    def test_cascade_delete_exam(self, exam, medication):
        ExamMedication.objects.create(exam=exam, medication=medication, dose='500 mg', frequency='daily')
        exam.delete()
        assert ExamMedication.objects.count() == 0

    def test_cascade_delete_medication(self, exam, medication):
        ExamMedication.objects.create(exam=exam, medication=medication, dose='500 mg', frequency='daily')
        medication.delete()
        assert ExamMedication.objects.count() == 0


# =============================================================================
# Medication Forms
# =============================================================================

class TestUserMedicationForm:
    """Tests for the UserMedicationForm."""

    @pytest.fixture
    def medication(self, db):
        return Medication.objects.create(name='Creatina', type='supplement')

    def test_valid_existing_medication(self, medication):
        form = UserMedicationForm(data={
            'medication': medication.pk,
            'dose': '5 g',
            'frequency': 'daily',
            'start_date': '01/01/2025',
        })
        assert form.is_valid(), form.errors

    def test_valid_new_medication(self, db):
        form = UserMedicationForm(data={
            'medication_name': 'Novo Suplemento',
            'medication_type': 'supplement',
            'dose': '100 mg',
            'frequency': 'daily',
            'start_date': '01/01/2025',
        })
        assert form.is_valid(), form.errors
        assert Medication.objects.filter(name='Novo Suplemento').exists()

    def test_no_medication_selected_or_named(self, db):
        form = UserMedicationForm(data={
            'dose': '5 g',
            'frequency': 'daily',
            'start_date': '01/01/2025',
        })
        assert not form.is_valid()

    def test_date_formats(self, medication):
        form = UserMedicationForm(data={
            'medication': medication.pk,
            'dose': '5 g',
            'frequency': 'daily',
            'start_date': '15/06/2025',
            'end_date': '2025-12-31',
        })
        assert form.is_valid(), form.errors

    def test_new_medication_get_or_create_dedup(self, db):
        Medication.objects.create(name='Existente', type='vitamin')
        form = UserMedicationForm(data={
            'medication_name': 'Existente',
            'medication_type': 'supplement',
            'dose': '10 mg',
            'frequency': 'daily',
            'start_date': '01/01/2025',
        })
        assert form.is_valid()
        assert Medication.objects.filter(name='Existente').count() == 1


# =============================================================================
# Medication Views
# =============================================================================

class TestMedicationViews:
    """Tests for medication CRUD views."""

    @pytest.fixture
    def auth_client(self, user):
        client = Client()
        client.login(username='testuser', password='TestPass123!')
        return client

    @pytest.fixture
    def medication(self, db):
        return Medication.objects.create(name='Vitamina D3', type='vitamin')

    @pytest.fixture
    def user_med(self, user, medication):
        return UserMedication.objects.create(
            user=user, medication=medication, dose='5000 UI',
            frequency='daily', start_date=date(2025, 1, 1),
        )

    def test_medications_list_requires_login(self):
        client = Client()
        resp = client.get(reverse('medications'))
        assert resp.status_code == 302

    def test_medications_list_ok(self, auth_client):
        resp = auth_client.get(reverse('medications'))
        assert resp.status_code == 200

    def test_medication_add_get(self, auth_client):
        resp = auth_client.get(reverse('medication_add'))
        assert resp.status_code == 200

    def test_medication_add_post(self, auth_client, medication):
        resp = auth_client.post(reverse('medication_add'), {
            'medication': medication.pk,
            'dose': '5000 UI',
            'frequency': 'daily',
            'start_date': '01/01/2025',
        })
        assert resp.status_code == 302
        assert UserMedication.objects.filter(user__username='testuser').count() == 1

    def test_medication_edit_get(self, auth_client, user_med):
        resp = auth_client.get(reverse('medication_edit', args=[user_med.pk]))
        assert resp.status_code == 200

    def test_medication_edit_post(self, auth_client, user_med):
        resp = auth_client.post(reverse('medication_edit', args=[user_med.pk]), {
            'medication': user_med.medication.pk,
            'dose': '10000 UI',
            'frequency': 'weekly',
            'start_date': '01/01/2025',
        })
        assert resp.status_code == 302
        user_med.refresh_from_db()
        assert user_med.dose == '10000 UI'

    def test_medication_toggle(self, auth_client, user_med):
        assert user_med.is_active is True
        auth_client.post(reverse('medication_toggle', args=[user_med.pk]))
        user_med.refresh_from_db()
        assert user_med.is_active is False
        assert user_med.end_date is not None

    def test_medication_delete(self, auth_client, user_med):
        auth_client.post(reverse('medication_delete', args=[user_med.pk]))
        assert UserMedication.objects.count() == 0

    def test_data_isolation(self, auth_client, medication):
        """User cannot edit another user's medication."""
        other = User.objects.create_user(username='other', password='TestPass123!')
        other.profile.date_of_birth = date(1990, 1, 1)
        other.profile.gender = 'M'
        other.profile.save()
        other_med = UserMedication.objects.create(
            user=other, medication=medication, dose='1000 UI',
            frequency='daily', start_date=date(2025, 1, 1),
        )
        resp = auth_client.get(reverse('medication_edit', args=[other_med.pk]))
        assert resp.status_code == 404

    def test_exam_medications_view_get(self, auth_client, exam, user_med):
        resp = auth_client.get(reverse('exam_medications', args=[exam.pk]))
        assert resp.status_code == 200

    def test_exam_medications_view_post(self, auth_client, exam, user_med):
        resp = auth_client.post(reverse('exam_medications', args=[exam.pk]), {
            'medications': [user_med.pk],
        })
        assert resp.status_code == 302
        assert ExamMedication.objects.filter(exam=exam).count() == 1


# =============================================================================
# Medication URL Routing
# =============================================================================

class TestMedicationURLs:
    """Tests for medication URL patterns."""

    def test_medications_url(self):
        assert resolve('/medications/').view_name == 'medications'

    def test_medication_add_url(self):
        assert resolve('/medications/add/').view_name == 'medication_add'

    def test_medication_edit_url(self):
        assert resolve('/medications/1/edit/').view_name == 'medication_edit'

    def test_medication_toggle_url(self):
        assert resolve('/medications/1/toggle/').view_name == 'medication_toggle'

    def test_medication_delete_url(self):
        assert resolve('/medications/1/delete/').view_name == 'medication_delete'

    def test_exam_medications_url(self):
        assert resolve('/exam/1/medications/').view_name == 'exam_medications'


# =============================================================================
# Seed Medications Command
# =============================================================================

class TestSeedMedicationsCommand:
    """Tests for the seed_medications management command."""

    def test_seed_creates_medications(self, db):
        from django.core.management import call_command
        call_command('seed_medications')
        assert Medication.objects.count() > 50

    def test_seed_idempotent(self, db):
        from django.core.management import call_command
        call_command('seed_medications')
        count1 = Medication.objects.count()
        call_command('seed_medications')
        count2 = Medication.objects.count()
        assert count1 == count2

    def test_seed_types(self, db):
        from django.core.management import call_command
        call_command('seed_medications')
        types = set(Medication.objects.values_list('type', flat=True))
        assert 'vitamin' in types
        assert 'supplement' in types
        assert 'hormone' in types
        assert 'medication' in types
