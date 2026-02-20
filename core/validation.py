"""
Post-extraction validation engine for blood exam results.

Runs after all ExamResults are saved. Detects data quality issues
and applies auto-corrections where confidence is high.

Layers:
  A. Physiological range checks (impossible values)
  B. Cross-biomarker formula validation (lipid panel, WBC sum)
  C. WBC differential percentage detection + auto-conversion
  D. Duplicate exam detection
  E. Historical consistency checks
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional

logger = logging.getLogger('core')


class FlagSeverity(Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    AUTO_CORRECTED = 'auto_corrected'


class FlagCategory(Enum):
    PHYSIOLOGICAL = 'physiological'
    CROSS_BIOMARKER = 'cross_biomarker'
    WBC_PERCENTAGE = 'wbc_percentage'
    DUPLICATE_EXAM = 'duplicate_exam'
    HISTORICAL = 'historical'
    LOW_CONFIDENCE = 'low_confidence'
    UNMATCHED = 'unmatched'


@dataclass
class ValidationFlag:
    exam_result_id: Optional[int]
    biomarker_code: str
    severity: FlagSeverity
    category: FlagCategory
    message: str
    original_value: Optional[Decimal] = None
    corrected_value: Optional[Decimal] = None
    details: dict = field(default_factory=dict)


# =============================================================================
# Physiological limits: absolute min/max that are physically impossible to exceed.
# Values outside these ranges almost certainly indicate a mapping error.
# =============================================================================
PHYSIOLOGICAL_LIMITS = {
    # Hemograma
    'HCT':   (15, 70),
    'HGB':   (3, 25),
    'RBC':   (1.5, 8.0),
    'WBC':   (500, 100000),
    'PLT':   (5000, 1500000),
    'VCM':   (50, 130),
    'HCM':   (15, 45),
    'CHCM':  (25, 40),
    'RDW':   (8, 25),
    'NEUT':  (100, 50000),
    'LYMPH': (100, 30000),
    'MONO':  (10, 5000),
    'EOS':   (0, 10000),
    'BASO':  (0, 3000),
    # Lipidograma
    'CT':    (50, 500),
    'HDL':   (5, 150),
    'LDL':   (10, 400),
    'VLDL':  (1, 100),
    'TG':    (10, 2000),
    # Glicemia
    'GLI':   (20, 600),
    'EAG':   (20, 600),
    'HBA1C': (3.0, 20.0),
    'INS':   (0.1, 500),
    # Funcao Hepatica
    'TGO':   (1, 2000),
    'TGP':   (1, 2000),
    'GGT':   (1, 5000),
    'FA':    (10, 3000),
    'BILT':  (0.05, 30),
    'BILD':  (0.01, 15),
    'ALB':   (1.0, 7.0),
    # Funcao Renal
    'CREA':  (0.1, 15.0),
    'UREA':  (3, 200),
    'AU':    (0.5, 20),
    'TFG':   (5, 200),
    # Tireoide
    'TSH':   (0.01, 100),
    'T4L':   (0.1, 10.0),
    'T3L':   (0.5, 15.0),
    'T3T':   (0.2, 5.0),
    # Vitaminas e Minerais
    'VITD':  (1, 200),
    'B12':   (50, 5000),
    'FOLATO': (0.5, 50),
    'FE':    (5, 500),
    'FERR':  (1, 5000),
    'ZN':    (20, 300),
    'MG':    (0.5, 5.0),
    'CA':    (4.0, 16.0),
    'CAI':   (0.5, 2.0),
    'NA':    (100, 180),
    'K':     (1.5, 9.0),
    'P':     (0.5, 10.0),
    # Hormonal
    'TESTO': (1, 3000),
    'TESTOL': (0.1, 200),
    'E2':    (1, 1000),
    'DHEAS': (5, 1000),
    'CORT':  (0.5, 50),
    'IGF1':  (10, 1000),
    'PSA':   (0.01, 100),
    'PRL':   (0.5, 200),
    'LH':    (0.1, 100),
    'FSH':   (0.1, 100),
    'DHT':   (10, 3000),
    'SHBG':  (1, 300),
    'HGH':   (0.01, 50),
    'PTH':   (1, 500),
    # Inflamacao
    'PCR':   (0.01, 500),
    'VHS':   (0, 150),
    'HOMO':  (1, 100),
    # Proteinas
    'PT':    (2, 12),
    'GLOB':  (0.5, 7),
    # Outros
    'PEPC':  (0.1, 20),
    'VITC':  (0.1, 15),
    'IGFBP3': (0.5, 15),
}

# Biomarkers where large swings between exams are expected
VOLATILE_CODES = {'INS', 'CORT', 'PRL', 'HGH', 'VHS', 'PCR', 'BASO', 'EOS'}


def validate_exam(exam):
    """
    Run all validation rules on a completed exam.

    Args:
        exam: Exam model instance with results already saved.

    Returns:
        list of ValidationFlag
    """
    from .models import ExamResult

    results = ExamResult.objects.filter(exam=exam).select_related('biomarker')
    results_by_code = {r.biomarker.code: r for r in results}

    flags = []
    flags.extend(_check_physiological_ranges(results_by_code))
    flags.extend(_check_lipid_formula(results_by_code))
    flags.extend(_check_wbc_sum(results_by_code))
    flags.extend(_check_wbc_percentages(results_by_code))
    flags.extend(_check_duplicate_exam(exam, results_by_code))
    flags.extend(_check_historical_consistency(exam, results_by_code))

    return flags


# ---- Rule A: Physiological Range Checks ----

def _check_physiological_ranges(results_by_code):
    flags = []
    for code, result in results_by_code.items():
        if code not in PHYSIOLOGICAL_LIMITS:
            continue
        abs_min, abs_max = PHYSIOLOGICAL_LIMITS[code]
        val = float(result.value)
        if val < abs_min or val > abs_max:
            flags.append(ValidationFlag(
                exam_result_id=result.id,
                biomarker_code=code,
                severity=FlagSeverity.ERROR,
                category=FlagCategory.PHYSIOLOGICAL,
                message=(
                    f"{result.biomarker.name}: valor {val} fora dos limites "
                    f"fisiol\u00f3gicos ({abs_min}-{abs_max} {result.biomarker.unit})"
                ),
                original_value=result.value,
                details={'abs_min': abs_min, 'abs_max': abs_max},
            ))
    return flags


# ---- Rule B: Cross-Biomarker Formula Checks ----

def _check_lipid_formula(results_by_code):
    """CT should approximate HDL + LDL + VLDL (within 15%)."""
    flags = []
    ct = results_by_code.get('CT')
    hdl = results_by_code.get('HDL')
    ldl = results_by_code.get('LDL')
    vldl = results_by_code.get('VLDL')

    if not (ct and hdl and ldl and vldl):
        return flags

    expected = float(hdl.value) + float(ldl.value) + float(vldl.value)
    actual = float(ct.value)

    if expected <= 0:
        return flags

    deviation_pct = abs(actual - expected) / expected * 100
    if deviation_pct > 15:
        flags.append(ValidationFlag(
            exam_result_id=ct.id,
            biomarker_code='CT',
            severity=FlagSeverity.WARNING,
            category=FlagCategory.CROSS_BIOMARKER,
            message=(
                f"CT={actual:.0f} difere {deviation_pct:.0f}% da f\u00f3rmula "
                f"HDL({float(hdl.value):.0f})+LDL({float(ldl.value):.0f})"
                f"+VLDL({float(vldl.value):.0f})={expected:.0f}"
            ),
            details={
                'formula': 'CT = HDL + LDL + VLDL',
                'expected': expected,
                'actual': actual,
                'deviation_pct': round(deviation_pct, 1),
            },
        ))
    return flags


def _check_wbc_sum(results_by_code):
    """WBC should approximate sum of differential components (within 10%)."""
    flags = []
    wbc = results_by_code.get('WBC')
    components = ['NEUT', 'LYMPH', 'MONO', 'EOS', 'BASO']
    available = {c: results_by_code[c] for c in components if c in results_by_code}

    if not wbc or len(available) < 3:
        return flags

    component_sum = sum(float(r.value) for r in available.values())
    wbc_val = float(wbc.value)

    if wbc_val <= 0:
        return flags

    deviation_pct = abs(wbc_val - component_sum) / wbc_val * 100
    if deviation_pct > 10:
        flags.append(ValidationFlag(
            exam_result_id=wbc.id,
            biomarker_code='WBC',
            severity=FlagSeverity.WARNING,
            category=FlagCategory.CROSS_BIOMARKER,
            message=(
                f"WBC={wbc_val:.0f} difere {deviation_pct:.0f}% da soma "
                f"dos componentes ({component_sum:.0f})"
            ),
            details={
                'formula': 'WBC = NEUT + LYMPH + MONO + EOS + BASO',
                'wbc': wbc_val,
                'component_sum': component_sum,
                'components': {c: float(r.value) for c, r in available.items()},
            },
        ))
    return flags


# ---- Rule C: WBC Differential Percentage Detection ----

def _check_wbc_percentages(results_by_code):
    """Detect if WBC differential was stored as percentages instead of absolute."""
    flags = []
    wbc = results_by_code.get('WBC')
    if not wbc or float(wbc.value) < 1000:
        return flags

    wbc_val = float(wbc.value)
    diff_codes = ['NEUT', 'LYMPH', 'MONO', 'EOS']
    diff_results = {c: results_by_code[c] for c in diff_codes if c in results_by_code}

    if len(diff_results) < 2:
        return flags

    # All differential values < 100 while WBC > 1000
    all_small = all(float(r.value) < 100 for r in diff_results.values())
    # Their sum should be roughly 100 (they are percentages)
    total = sum(float(r.value) for r in diff_results.values())
    looks_like_pct = 50 < total < 110

    if all_small and looks_like_pct:
        for code, result in diff_results.items():
            pct_val = float(result.value)
            absolute_val = round(pct_val * wbc_val / 100)
            flags.append(ValidationFlag(
                exam_result_id=result.id,
                biomarker_code=code,
                severity=FlagSeverity.AUTO_CORRECTED,
                category=FlagCategory.WBC_PERCENTAGE,
                message=(
                    f"{code}: valor {pct_val} parece ser percentual. "
                    f"Convertido para absoluto: {absolute_val}/mm\u00b3 "
                    f"({pct_val}% \u00d7 WBC {wbc_val:.0f})"
                ),
                original_value=result.value,
                corrected_value=Decimal(str(absolute_val)),
                details={
                    'percentage': pct_val,
                    'wbc': wbc_val,
                    'absolute': absolute_val,
                },
            ))
    return flags


# ---- Rule D: Duplicate Exam Detection ----

def _check_duplicate_exam(exam, results_by_code):
    """Check if >80% of values match any previous exam exactly."""
    flags = []
    from .models import Exam, ExamResult

    previous_exams = (
        Exam.objects
        .filter(user=exam.user, status='completed')
        .exclude(id=exam.id)
        .order_by('-exam_date')[:10]
    )

    for prev_exam in previous_exams:
        prev_results = {
            r.biomarker.code: r
            for r in ExamResult.objects.filter(exam=prev_exam).select_related('biomarker')
        }

        common_codes = set(results_by_code.keys()) & set(prev_results.keys())
        if len(common_codes) < 5:
            continue

        exact_matches = sum(
            1 for code in common_codes
            if results_by_code[code].value == prev_results[code].value
        )

        match_pct = exact_matches / len(common_codes) * 100
        if match_pct > 80:
            flags.append(ValidationFlag(
                exam_result_id=None,
                biomarker_code='EXAM',
                severity=FlagSeverity.WARNING,
                category=FlagCategory.DUPLICATE_EXAM,
                message=(
                    f"Poss\u00edvel duplicata: {match_pct:.0f}% dos valores "
                    f"id\u00eanticos ao exame de "
                    f"{prev_exam.exam_date.strftime('%d/%m/%Y')} "
                    f"({exact_matches}/{len(common_codes)} biomarcadores)"
                ),
                details={
                    'duplicate_exam_id': prev_exam.id,
                    'duplicate_exam_date': prev_exam.exam_date.isoformat(),
                    'match_pct': round(match_pct, 1),
                    'exact_matches': exact_matches,
                    'total_compared': len(common_codes),
                },
            ))
    return flags


# ---- Rule E: Historical Consistency ----

def _check_historical_consistency(exam, results_by_code):
    """Flag values that changed >200% from the previous exam."""
    flags = []
    from .models import Exam, ExamResult

    previous_exam = (
        Exam.objects
        .filter(user=exam.user, status='completed', exam_date__lt=exam.exam_date)
        .first()
    )
    if not previous_exam:
        return flags

    prev_results = {
        r.biomarker.code: r
        for r in ExamResult.objects.filter(exam=previous_exam).select_related('biomarker')
    }

    for code, result in results_by_code.items():
        if code in VOLATILE_CODES or code not in prev_results:
            continue

        prev_val = float(prev_results[code].value)
        curr_val = float(result.value)

        if prev_val == 0:
            continue

        change_pct = abs(curr_val - prev_val) / prev_val * 100
        if change_pct > 200:
            flags.append(ValidationFlag(
                exam_result_id=result.id,
                biomarker_code=code,
                severity=FlagSeverity.WARNING,
                category=FlagCategory.HISTORICAL,
                message=(
                    f"{result.biomarker.name}: mudan\u00e7a de {change_pct:.0f}% "
                    f"({prev_val} \u2192 {curr_val}) desde "
                    f"{previous_exam.exam_date.strftime('%d/%m/%Y')}"
                ),
                details={
                    'previous_value': prev_val,
                    'current_value': curr_val,
                    'change_pct': round(change_pct, 1),
                    'previous_exam_date': previous_exam.exam_date.isoformat(),
                },
            ))
    return flags


# ---- Auto-corrections ----

def apply_auto_corrections(exam, flags):
    """Apply auto-corrections for high-confidence fixes (WBC %, BASO estimation)."""
    from .models import ExamResult

    # Apply WBC percentage conversions
    for flag in flags:
        if (flag.severity == FlagSeverity.AUTO_CORRECTED
                and flag.corrected_value is not None
                and flag.exam_result_id):
            result = ExamResult.objects.get(id=flag.exam_result_id)
            result.value = flag.corrected_value
            result.save()
            logger.info(
                f"Auto-corrected {flag.biomarker_code}: "
                f"{flag.original_value} -> {flag.corrected_value}"
            )

    # Estimate BASO if missing
    _estimate_baso_if_missing(exam, flags)


def _estimate_baso_if_missing(exam, flags):
    """If BASO is missing but WBC and other components are present, estimate it."""
    from .models import Biomarker, ExamResult

    results_by_code = {
        r.biomarker.code: r
        for r in ExamResult.objects.filter(exam=exam).select_related('biomarker')
    }

    if 'BASO' in results_by_code:
        return

    wbc = results_by_code.get('WBC')
    needed = ['NEUT', 'LYMPH', 'MONO', 'EOS']
    available = {c: results_by_code[c] for c in needed if c in results_by_code}

    if not wbc or len(available) < 4:
        return

    component_sum = sum(float(r.value) for r in available.values())
    baso_estimated = max(0, float(wbc.value) - component_sum)

    baso_bm = Biomarker.objects.filter(code='BASO').first()
    if not baso_bm:
        return

    result = ExamResult.objects.create(
        exam=exam,
        biomarker=baso_bm,
        value=Decimal(str(round(baso_estimated))),
    )
    flags.append(ValidationFlag(
        exam_result_id=result.id,
        biomarker_code='BASO',
        severity=FlagSeverity.INFO,
        category=FlagCategory.CROSS_BIOMARKER,
        message=(
            f"BASO estimado: WBC({float(wbc.value):.0f}) - "
            f"componentes({component_sum:.0f}) = {baso_estimated:.0f}/mm\u00b3"
        ),
        corrected_value=Decimal(str(round(baso_estimated))),
    ))
    logger.info(f"Estimated BASO={baso_estimated:.0f} for exam {exam.id}")


def save_validation_flags(exam, flags):
    """Persist validation flags to the database."""
    from .models import ExamValidation

    # Clear previous flags for this exam
    ExamValidation.objects.filter(exam=exam).delete()

    objects = []
    for flag in flags:
        objects.append(ExamValidation(
            exam=exam,
            exam_result_id=flag.exam_result_id,
            biomarker_code=flag.biomarker_code,
            severity=flag.severity.value,
            category=flag.category.value,
            message=flag.message,
            original_value=flag.original_value,
            corrected_value=flag.corrected_value,
            details=flag.details,
        ))

    if objects:
        ExamValidation.objects.bulk_create(objects)
        logger.info(
            f"Exam {exam.id}: saved {len(objects)} validation flags "
            f"({sum(1 for f in flags if f.severity == FlagSeverity.ERROR)} errors, "
            f"{sum(1 for f in flags if f.severity == FlagSeverity.WARNING)} warnings, "
            f"{sum(1 for f in flags if f.severity == FlagSeverity.AUTO_CORRECTED)} auto-corrected)"
        )
